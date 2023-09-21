import torch
from omegaconf import OmegaConf
import configparser
import logging
from pydub import AudioSegment
import io

config = configparser.ConfigParser()
config.read("config.ini")

# Схема логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

language = 'ru'
model_id = 'v3_1_ru' # v4_ru
sample_rate = 48000
speaker = 'xenia'
device = torch.device('cpu')  # gpu or cpu
put_accent = True
put_yo = True

class silero_tts():
    def __init__(self, text: str, client_id: str):
        self.text = text
        self.client_id = client_id

    def text2audio(self):
        torch.hub.download_url_to_file('https://raw.githubusercontent.com/snakers4/silero-models/master/models.yml',
                                       'latest_silero_models.yml',
                                       progress=False)

        model, text = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                     model='silero_tts',
                                     language=language,
                                     speaker=model_id)

        model.to(device)

        # Преобразуйте аудио в формат WAV
        audio = model.save_wav(text=self.text,
                               speaker=speaker,
                               sample_rate=sample_rate,
                               put_accent=put_accent,
                               put_yo=put_yo,
                               audio_path=f'temp/wav/{self.client_id}_tts.wav')

        audio_segment = AudioSegment.from_wav(audio)

        return audio_segment


class combined_audio():
    def __init__(self, srt_text: str, client_id: str):
        self.srt_text = srt_text
        self.client_id = client_id

    def combine_audio(self):
        text_list = self.srt_text.split("\n\n")
        dialogue_list = []
        time_labels = []
        time_length = []

        for text in text_list:
            lines = text.split("\n")
            time_labels.append(lines[1].split(" ")[0])
            time_length.append(self.count_ms(lines[1].split(" ")[2]) - self.count_ms(lines[1].split(" ")[0]))
            dialogue_list.append(lines[2])

        if len(dialogue_list) == len(time_labels):
            duration = self.count_ms(text_list[-1].split("\n")[1].split(" ")[-1])

            result_audio = AudioSegment.silent(duration=duration)

            for i, time_label in enumerate(time_labels):
                time = self.count_ms(time_label)
                audio_segment = silero_tts(dialogue_list[i], self.client_id).text2audio()
                edited_audio = self.speed_up_wav(time_length[i], audio_segment)
                result_audio = result_audio.overlay(edited_audio, position=time)

            result_audio.export(f"temp/wav/{self.client_id}.wav", format="wav")

            return f"temp/wav/{self.client_id}.wav"

        else:
            logging.info("неправильная структура srt")

    def count_ms(self, time_label):
        hh, mm, ss_ms = time_label.split(":")
        ss, ms = ss_ms.split(",")

        hh, mm, ss, ms = map(int, (hh, mm, ss, ms))

        total_ms = (hh * 3600 + mm * 60 + ss) * 1000 + ms

        return total_ms

    def speed_up_wav(self, desired_duration_ms, audio):
        current_duration_ms = len(audio)

        if current_duration_ms > desired_duration_ms:
            speedup_factor = current_duration_ms / desired_duration_ms
            audio = audio.speedup(playback_speed=speedup_factor)

        return audio