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
import timeit

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

    def load_model(self, checkpoint_dir="model/", repo_id="capleaf/viXTTS", use_deepspeed=False):
        self.clear_gpu_cache()
        os.makedirs(checkpoint_dir, exist_ok=True)

        required_files = ["model.pth", "config.json", "vocab.json", "speakers_xtts.pth"]
        files_in_dir = os.listdir(checkpoint_dir)
        if not all(file in files_in_dir for file in required_files):
            yield f"Missing model files! Downloading from {repo_id}..."
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
            yield f"Model download finished..."

        xtts_config = os.path.join(checkpoint_dir, "config.json")
        config = XttsConfig()
        config.load_json(xtts_config)
        self.model = Xtts.init_from_config(config)
        yield "Loading model..."
        self.model.load_checkpoint(
            config, checkpoint_dir=checkpoint_dir, use_deepspeed=use_deepspeed
        )
        if torch.cuda.is_available():
            self.model.cuda()

        print("Model Loaded!")
        yield "Model Loaded!"

        # Preprocess conditioning latents and filter cache
        yield "Preprocessing conditioning latents and filter cache..."
        audio_path = os.path.join(self.MODEL_DIR, "vi_sample.wav")
        
        # Apply DeepFilter
        if audio_path not in self.filter_cache:
            filtered_audio_path = audio_path.replace(".wav", self.FILTER_SUFFIX)
            subprocess.run(["deepFilter", audio_path, "-o", os.path.dirname(audio_path)])
            self.filter_cache[audio_path] = filtered_audio_path

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

        if normalize_text and lang == "vi":
            tts_text = self.normalize_vietnamese_text(tts_text)

        if lang in ["ja", "zh-cn"]:
            sentences = tts_text.split("。")
        else:
            sentences = tts_text.split(". ")

        wav_chunks = []
        for sentence in sentences:
            if sentence.strip() == "":
                continue
            wav_chunk = self.model.inference(
                text=sentence,
                language=lang,
                gpt_cond_latent=gpt_cond_latent,
                speaker_embedding=speaker_embedding,
                temperature=0.5,
                length_penalty=1.0,
                repetition_penalty=10.0,
                top_k=50,
                top_p=0.8,
                enable_text_splitting=True,
            )

            keep_len = self.calculate_keep_len(sentence, lang)
            wav_chunk["wav"] = wav_chunk["wav"][:keep_len]

            wav_chunks.append(torch.tensor(wav_chunk["wav"]))
        
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
        audioId = self.run_tts("en", text, audioPath, False, False)
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
        text = (
            VNTTS.TTSnorm(text, unknown=False, lower=False, rule=True)
            .replace("..", ".")
            .replace("!.", "!")
            .replace("?.", "?")
            .replace(" .", ".")
            .replace(" ,", ",")
            .replace('"', "")
            .replace("'", "")
            .replace("AI", "Ây Ai")
            .replace("A.I", "Ây Ai")
        )
        return text

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

    @staticmethod
    def TTSnorm(text, punc=False, unknown=True, lower=True, rule=False):
        module_name = 'vinorm'
        spec = importlib.util.find_spec(module_name)
        
        if spec is None:
            raise ImportError(f"Module {module_name} not found")
        
        module_path = spec.origin
        module_dir = os.path.dirname(module_path)

        input_path = os.path.join(module_dir, "input.txt")
        output_path = os.path.join(module_dir, "output.txt")
        main_executable = os.path.join(module_dir, "main")

        with open(input_path, "w", encoding="utf-8") as fw:
            fw.write(text)

        myenv = os.environ.copy()
        myenv['LD_LIBRARY_PATH'] = os.path.join(module_dir, 'lib')

        command = ['python', main_executable]
        if punc:
            command.append("-punc")
        if unknown:
            command.append("-unknown")
        if lower:
            command.append("-lower")
        if rule:
            command.append("-rule")

        try:
            subprocess.check_call(command, env=myenv, cwd=module_dir)
        except subprocess.CalledProcessError as e:
            print(f"Command failed with error: {e}")

        with open(output_path, "r", encoding="utf-8") as fr:
            text = fr.read()

        processed_text = ""
        segments = text.split("#line#")
        for segment in segments:
            if segment.strip() == "":
                continue
            processed_text += segment + ". "

        return processed_text

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
    
#     # Load the model
#     for message in vntts.load_model():
#         print(message)
    
#     # Generate speech
#     startTime = timeit.default_timer()
#     print("timer started")
#     text = "Xin chào, bây giờ tôi là gói Python"
#     output_path = vntts.text_to_speech(text)
#     print(f"Speech generated at: {output_path}")
#     print("Time taken: ", timeit.default_timer() - startTime)
    
