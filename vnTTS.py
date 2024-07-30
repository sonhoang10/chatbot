import csv
import datetime
import os
import re
import time
import uuid
from io import StringIO
import importlib
import argparse
import hashlib
import logging
import os
import string
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
import soundfile as sf
import torch
import torchaudio
from huggingface_hub import hf_hub_download, snapshot_download
from unidecode import unidecode
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from UTSTokenizer import sent_tokenize
import timeit
import pickle
from normalize_vietnamese_text import sum_text

class VNTTS:
    def __init__(self, model_dir, output_dir):
        self.MODEL_DIR = model_dir
        self.OUTPUT_DIR = output_dir
        self.FILTER_SUFFIX = "_DeepFilterNet3.wav"
        self.speaker_audio_cache = {}
        self.filter_cache = {}
        self.conditioning_latents_cache = {}
        self.cache_queue = []
        self.model = None

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def clear_gpu_cache(self):
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def save_pickle(self, cache, filename):
        with open(filename, 'wb') as f:
            pickle.dump(cache, f)

    def load_pickle(self, filename):
        try:
            with open(filename, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return {}
    
    def setup(self, checkpoint_dir="model/", repo_id="capleaf/viXTTS"):

        snapshot_download(
            repo_id=repo_id,
            repo_type="model",
            local_dir=checkpoint_dir,
        )
        hf_hub_download(
            repo_id="coqui/XTTS-v2",
            filename="speakers_xtts.pth",
            local_dir=checkpoint_dir,
        )


    def load_model(self, checkpoint_dir="model/"):
        self.clear_gpu_cache()
        os.makedirs(checkpoint_dir, exist_ok=True)
        xtts_config = os.path.join(checkpoint_dir, "config.json")
        config = XttsConfig() 
        config.load_json(xtts_config)
        self.model = Xtts.init_from_config(config)
        yield "Loading model..."
        self.model.load_checkpoint(
            config, checkpoint_dir=checkpoint_dir, use_deepspeed=False
        )
        if torch.cuda.is_available():
            self.model.cuda()

        yield "Model Loaded!"

        filter_cache_file = os.path.normpath(os.path.join(checkpoint_dir, "filter_cache.pkl"))
        conditioning_latents_cache_file = os.path.normpath(os.path.join(checkpoint_dir, "conditioning_latents_cache.pkl"))

        # Load filter cache
        try:
            self.filter_cache = self.load_pickle(filter_cache_file)
            yield "Filter cache loaded successfully."
        except Exception as e:
            yield f"Failed to load filter cache: {str(e)}. Initializing empty cache."
            self.filter_cache = {}

        # Load conditioning latents cache
        try:
            self.conditioning_latents_cache = self.load_pickle(conditioning_latents_cache_file)
            yield "Conditioning latents cache loaded successfully."
        except Exception as e:
            yield f"Failed to load conditioning latents cache: {str(e)}. Initializing empty cache."
            self.conditioning_latents_cache = {}

        # Preprocess conditioning latents and filter cache
        yield "Preprocessing conditioning latents and filter cache..."
        audio_path = os.path.join(self.MODEL_DIR, "vi_sample.wav")
        deepfilter_path = audio_path.replace(".wav", self.FILTER_SUFFIX)
        
        # Apply DeepFilter
        if not os.path.exists(deepfilter_path):
            filtered_audio_path = audio_path.replace(".wav", self.FILTER_SUFFIX)
            subprocess.run(["deepFilter", audio_path, "-o", os.path.dirname(audio_path)], shell = True)
            self.filter_cache[audio_path] = filtered_audio_path
            try:
                self.save_pickle(self.filter_cache, filter_cache_file)
                yield "Filter cache updated and saved."
            except Exception as e:
                yield f"Failed to save filter cache: {str(e)}."

        # Compute conditioning latents
        cache_key = (
            audio_path,
            self.model.config.gpt_cond_len,
            self.model.config.max_ref_len,
            self.model.config.sound_norm_refs,
        )
        if cache_key not in self.conditioning_latents_cache:
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=self.filter_cache[audio_path],
                gpt_cond_len=self.model.config.gpt_cond_len,
                max_ref_length=self.model.config.max_ref_len,
                sound_norm_refs=self.model.config.sound_norm_refs,
            )
            self.conditioning_latents_cache[cache_key] = (gpt_cond_latent, speaker_embedding)
            try:
                self.save_pickle(self.conditioning_latents_cache, conditioning_latents_cache_file)
                yield "Conditioning latents cache updated and saved."
            except Exception as e:
                yield f"Failed to save conditioning latents cache: {str(e)}."

        yield "Preprocessing complete!"


    def invalidate_cache(self, cache_limit=50):
        if len(self.cache_queue) > cache_limit:
            key_to_remove = self.cache_queue.pop(0)
            print("Invalidating cache", key_to_remove)
            if os.path.exists(key_to_remove):
                os.remove(key_to_remove)
            if os.path.exists(key_to_remove.replace(".wav", self.FILTER_SUFFIX)):
                os.remove(key_to_remove.replace(".wav", self.FILTER_SUFFIX))
            if key_to_remove in self.filter_cache:
                del self.filter_cache[key_to_remove]
            if key_to_remove in self.conditioning_latents_cache:
                del self.conditioning_latents_cache[key_to_remove]

    def run_tts(self, lang, tts_text, speaker_audio_file, use_deepfilter, normalize_text):
        if self.model is None:
            return "You need to load the model first!", None, None

        if not speaker_audio_file:
            return "You need to provide reference audio!!!", None, None

        speaker_audio_key = speaker_audio_file
        if speaker_audio_key not in self.cache_queue:
            self.cache_queue.append(speaker_audio_key)
            self.invalidate_cache()

        if use_deepfilter and speaker_audio_key in self.filter_cache:
            print("Using filter cache...")
            speaker_audio_file = self.filter_cache[speaker_audio_key]
        elif use_deepfilter:
            print("Running filter...")
            subprocess.run(
                [
                    "deepFilter",
                    speaker_audio_file,
                    "-o",
                    os.path.dirname(speaker_audio_file),
                ]
            )
            self.filter_cache[speaker_audio_key] = speaker_audio_file.replace(
                ".wav", self.FILTER_SUFFIX
            )
            speaker_audio_file = self.filter_cache[speaker_audio_key]

        cache_key = (
            speaker_audio_key,
            self.model.config.gpt_cond_len,
            self.model.config.max_ref_len,
            self.model.config.sound_norm_refs,
        )
        if cache_key in self.conditioning_latents_cache:
            print("Using conditioning latents cache...")
            gpt_cond_latent, speaker_embedding = self.conditioning_latents_cache[cache_key]
        else:
            print("Computing conditioning latents...")
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=speaker_audio_file,
                gpt_cond_len=self.model.config.gpt_cond_len,
                max_ref_length=self.model.config.max_ref_len,
                sound_norm_refs=self.model.config.sound_norm_refs,
            )
            self.conditioning_latents_cache[cache_key] = (gpt_cond_latent, speaker_embedding)

        tts_text = re.sub("([^\x00-\x7F]|\w)(\.|\。|\?)", r"\1 \2\2", tts_text)

        if normalize_text and lang == "vi":
            tts_text = self.normalize_vietnamese_text(tts_text)

        if lang in ["ja", "zh-cn"]:
            sentences = tts_text.split("。")
        else:
            sentences = sent_tokenize(tts_text)

        startTime = timeit.default_timer()
        wav_chunks = []
        for sentence in sentences:
            if sentence.strip() == "":
                continue
            wav_chunk = self.model.inference(
                text=sentence,
                language=lang,
                gpt_cond_latent=gpt_cond_latent,
                speaker_embedding=speaker_embedding,
                enable_text_splitting=True,
                temperature=0.1,
                length_penalty=1.0,
                repetition_penalty=10.0,
                top_k=30,
                top_p=0.85,
                speed = 1.25
            )

            keep_len = self.calculate_keep_len(sentence, lang)
            wav_chunk["wav"] = wav_chunk["wav"][:keep_len]

            wav_chunks.append(torch.tensor(wav_chunk["wav"]))
        print("Inference Time: ", timeit.default_timer()- startTime)

        out_wav = torch.cat(wav_chunks, dim=0).unsqueeze(0)
        audioId = str(uuid.uuid4())
        out_path = os.path.join(self.OUTPUT_DIR, f"{audioId}.wav")
        print("Saving output to ", out_path)
        torchaudio.save(out_path, out_wav, 24000)

        return audioId

    def text_to_speech(self, text):
        if self.model is None:
            for message in self.load_model():
                print(message)
        
        audioPath = os.path.join(self.MODEL_DIR, "vi_sample.wav")
        start = timeit.default_timer()
        audioId = self.run_tts("vi", text, audioPath, False, True)
        print("Time taken: ", timeit.default_timer() - start)
        return audioId

    @staticmethod
    def generate_hash(data):
        hash_object = hashlib.md5()
        hash_object.update(data)
        return hash_object.hexdigest()

    @staticmethod
    def get_file_name(text, max_char=50):
        filename = text[:max_char]
        filename = filename.lower()
        filename = filename.replace(" ", "_")
        filename = filename.translate(
            str.maketrans("", "", string.punctuation.replace("_", ""))
        )
        filename = unidecode(filename)
        current_datetime = datetime.now().strftime("%m%d%H%M%S")
        filename = f"{current_datetime}_{filename}"
        return filename

    @staticmethod
    def normalize_vietnamese_text(text):
        # Ensure text is in utf-8 encoding
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        normalized_text = sum_text(text)
        
        return normalized_text

    @staticmethod
    def calculate_keep_len(text, lang):
        if lang in ["ja", "zh-cn"]:
            return -1

        word_count = len(text.split())
        num_punct = text.count(".") + text.count("!") + text.count("?") + text.count(",")
        
        if word_count < 5:
            return 15000 * word_count + 2000 * num_punct
        elif word_count < 10:
            return 13000 * word_count + 2000 * num_punct
        return -1

# Set up logging
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Usage example
# if __name__ == "__main__":
#     currentDir = os.getcwd()
#     modelDir = os.path.join(currentDir, "model")
#     outputDir = os.path.join(currentDir, "AudioFolder")
#     vntts = VNTTS(model_dir=modelDir , output_dir=outputDir)
#     #delete everything in the output folder
#     for file in os.listdir(outputDir):
#         os.remove(os.path.join(outputDir, file))
    
#     # # Load the model
#     startTime = timeit.default_timer()
#     for message in vntts.load_model(modelDir):
#         print(message)
#     print("Time taken to load model: ", timeit.default_timer() - startTime)
    
# #     # Generate speech
#     startTime = timeit.default_timer()
#     print("timer started")
#     output_path = vntts.text_to_speech("Dạ vâng, em sẵn lòng trợ giúp. Anh chị cần giúp đỡ với vấn đề gì ạ")
#     print(f"Speech generated at: {output_path}")
    
