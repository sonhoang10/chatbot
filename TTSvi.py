import csv
import datetime
import os
import re
import time
import uuid
from io import StringIO

import torch
import torchaudio
from huggingface_hub import HfApi, hf_hub_download, snapshot_download
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from normalize_vietnamese_text import sum_text
import timeit

class TTSProcessor:
    def __init__(self, model_dir="model/", repo_id="capleaf/viXTTS", hf_token=None, use_deepspeed=False):
        self.model_dir = model_dir
        self.repo_id = repo_id
        self.use_deepspeed = use_deepspeed
        self.api = HfApi(token=hf_token)
        self._setup_model()
    
    def _setup_model(self):
        os.makedirs(self.model_dir, exist_ok=True)
        required_files = ["model.pth", "config.json", "vocab.json", "speakers_xtts.pth"]
        files_in_dir = os.listdir(self.model_dir)
        if not all(file in files_in_dir for file in required_files):
            snapshot_download(repo_id=self.repo_id, repo_type="model", local_dir=self.model_dir)
            hf_hub_download(repo_id="coqui/XTTS-v2", filename="speakers_xtts.pth", local_dir=self.model_dir)

        config_path = os.path.join(self.model_dir, "config.json")
        config = XttsConfig()
        config.load_json(config_path)
        self.model = Xtts.init_from_config(config)
        self.model.load_checkpoint(config, checkpoint_dir=self.model_dir, use_deepspeed=self.use_deepspeed)
        if torch.cuda.is_available():
            self.model.cuda()
        
        self.supported_languages = config.languages
        if "vi" not in self.supported_languages:
            self.supported_languages.append("vi")
        
        if "vi" not in self.model.tokenizer.char_limits:
            self.model.tokenizer.char_limits["vi"] = 5000  # Reasonable default value
    
    @staticmethod
    def normalize_vietnamese_text(text):
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
    
    def predict(self, prompt, language, audio_file_pth, speed=1.25, output_dir="output"):
        if language not in self.supported_languages:
            return None, f"Language '{language}' is not supported. Please choose a different language."

        if len(prompt) < 2:
            return None, "Please provide a longer prompt text."

        if len(prompt) > 250:
            return None, f"Your prompt is too long, please keep it under 250 characters. ({len(prompt)} characters)"

        try:
            metrics_text = ""
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=audio_file_pth,
                gpt_cond_len=30,
                gpt_cond_chunk_len=4,
                max_ref_length=60
            )

            prompt = re.sub("([^\x00-\x7F]|\w)(\.|\。|\?)", r"\1 \2\2", prompt)

            if language == "vi":
                prompt = self.normalize_vietnamese_text(prompt)

            print("Generating new audio...")
            t0 = time.time()
            out = self.model.inference(
                prompt,
                language,
                gpt_cond_latent,
                speaker_embedding,
                repetition_penalty=5.0,
                speed=speed,
                enable_text_splitting=True,
            )

            inference_time = time.time() - t0
            metrics_text += f"Time to generate audio: {round(inference_time * 1000)} milliseconds\n"
            real_time_factor = (time.time() - t0) / out["wav"].shape[-1] * 24000
            metrics_text += f"Real-time factor (RTF): {real_time_factor:.2f}\n"

            keep_len = self.calculate_keep_len(prompt, language)
            out["wav"] = out["wav"][:keep_len]
            audioId = str(uuid.uuid4())
            output_path = os.path.join(output_dir, f"{audioId}.wav")
            torchaudio.save(output_path, torch.tensor(out["wav"]).unsqueeze(0), 24000)

        except RuntimeError as e:
            if "device-side assert" in str(e):
                metrics_text = "Unhandled Exception encountered, please retry in a minute."
                error_time = datetime.datetime.now().strftime("%d-%m-%Y-%H:%M:%S")
                error_data = [error_time, prompt, language, audio_file_pth, str(e)]
                self._log_error(error_data, audio_file_pth)
                self.api.restart_space(repo_id=self.repo_id)
            else:
                metrics_text = "An error occurred: " + str(e)
            return None, metrics_text

        return audioId, output_path, metrics_text,
    
    def text_to_speech(self, text, save_file):
        language = "vi"
        speed = 1.15
        prompt=text
        audio_file_pth = r"C:\Son\TTS\demo\sound\audio8.wav"
        start = timeit.default_timer()
        audioId, output_audio, metrics_text = self.predict(prompt, language, audio_file_pth, speed, save_file)
        print("Time taken: ", timeit.default_timer() - start)
        return audioId, output_audio, metrics_text

    def _log_error(self, error_data, audio_file_pth):
        write_io = StringIO()
        csv.writer(write_io).writerows([error_data])
        csv_upload = write_io.getvalue().encode()

        filename = error_data[0] + "_" + str(uuid.uuid4()) + ".csv"
        self.api.upload_file(path_or_fileobj=csv_upload, path_in_repo=filename, repo_id="coqui/xtts-flagged-dataset", repo_type="dataset")

        speaker_filename = error_data[0] + "_reference_" + str(uuid.uuid4()) + ".wav"
        self.api.upload_file(path_or_fileobj=audio_file_pth, path_in_repo=speaker_filename, repo_id="coqui/xtts-flagged-dataset", repo_type="dataset")

# Usage example
if __name__ == "__main__":
    hf_token = os.environ.get("HF_TOKEN")
    tts_processor = TTSProcessor(hf_token=hf_token)

    prompt = "Dạ vâng, em sẵn lòng trợ giúp. Anh chị cần giúp đỡ với vấn đề gì ạ?"
    output_dir = r"C:\Son\TTS\demo\result"
    audioId, output_audio, metrics_text = tts_processor.text_to_speech(prompt,output_dir)

