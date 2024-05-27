import os
import re
import logging
import torch
import configparser
import pydub
import numpy as np
import pyrubberband as pyrb
from pathlib import Path
from pydub import AudioSegment
from transliterate import translit
from num2words import num2words
from gradio_client import Client
from ruaccent import RUAccent

config = configparser.ConfigParser()
config.read("config.ini")

accentizer = RUAccent()
accentizer.load(omograph_model_size='big', use_dictionary=True)

client = Client("http://localhost:7865/")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# """
# SILERO TTS VARS
# """
# language = 'en'
# model_id = 'v3_1_ru'
# sample_rate = 48000
# speaker = 'aidar'
# device = torch.device('cuda:0')  # gpu or cpu
# put_accent = True
# put_yo = True
#
# """
# RVC VARS
# """
# pdf_path = "data/useless.pdf"
# rvc_method_name = "rmvpe"
# index_path = "logs/kuplinov/added_IVF2384_Flat_nprobe_1_kuplinov_v2.index"


class silero_tts():
    def __init__(self, text: str, client_id: str):
        self.srt_text = text
        self.client_id = client_id

    # def rvc(self, file_path):
    #     absolute_path = f"/home/video2srt/{file_path}"
    #
    #     result = client.predict(
    #         0,
    #         absolute_path,
    #         0,
    #         pdf_path,
    #         rvc_method_name,
    #         "",
    #         index_path,
    #         0,
    #         0,
    #         0,
    #         0,
    #         0,
    #         api_name="/infer_convert"
    #     )
    #
    #     return result[1]

    # def text2audio(self):
    #     torch.hub.download_url_to_file('https://raw.githubusercontent.com/snakers4/silero-models/master/models.yml',
    #                                    'latest_silero_models.yml',
    #                                    progress=False)
    #
    #     model, text = torch.hub.load(repo_or_dir='snakers4/silero-models',
    #                                  model='silero_tts',
    #                                  language=language,
    #                                  speaker=model_id)
    #
    #     model.to(device)
    #
    #     audio_file = f'temp/wav/{self.client_id}_tts.wav'
    #
    #     audio = model.save_wav(text=self.srt_text,
    #                            speaker=speaker,
    #                            sample_rate=sample_rate,
    #                            put_accent=put_accent,
    #                            put_yo=put_yo,
    #                            audio_path=audio_file)
    #
    #     audio_segment = AudioSegment.from_wav(audio)
    #
    #     return audio_segment, audio, audio_file

    def text2audio_openai(self):
        # torch.hub.download_url_to_file('https://raw.githubusercontent.com/snakers4/silero-models/master/models.yml',
        #                                'latest_silero_models.yml',
        #                                progress=False)
        #
        # model, text = torch.hub.load(repo_or_dir='snakers4/silero-models',
        #                              model='silero_tts',
        #                              language=language,
        #                              speaker=model_id)
        #
        # model.to(device)

        # audio = model.save_wav(text=self.srt_text,
        #                        speaker=speaker,
        #                        sample_rate=sample_rate,
        #                        put_accent=put_accent,
        #                        put_yo=put_yo,
        #                        audio_path=audio_file)
        #
        # return audio_segment, audio, audio_file

        speech_file_path = Path(__file__).parent / f'temp/wav/{self.client_id}_tts.wav'
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=self.srt_text
        )

        response.stream_to_file(speech_file_path)

        return speech_file_path

    def remove_temp_files(self, file_path):
        try:
            os.remove(file_path)
            logging.info(f"{file_path} deleted!")
        except OSError as e:
            logging.info(f"Error while deleting {file_path}: {e}")

    # def replace_english_with_transliteration(self, text: str):
    #     words = text.split()
    #     result = []
    #     for word in words:
    #         if word.isalpha() and word.isascii():
    #             transliterated_word = translit(word, "ru")
    #             result.append(transliterated_word)
    #         else:
    #             result.append(word)
    #     return ' '.join(result)

    # def replace_numbers_with_words(self, text: str):
    #     # Используем регулярное выражение для поиска чисел в тексте
    #     pattern = r'(\d+(?:[.,]\d+)?)'
    #     words = re.split(pattern, text)
    #
    #     result = []
    #     for word in words:
    #         if re.match(pattern, word):
    #             number = word.replace(',', '.')
    #             word_as_words = num2words(int(number), lang='ru')
    #             result.append(word_as_words)
    #         else:
    #             result.append(word)
    #
    #     return ''.join(result)

    def count_ms(self, time_label):
        hh, mm, ss_ms = time_label.split(":")
        ss, ms = ss_ms.split(",")

        hh, mm, ss, ms = map(int, (hh, mm, ss, ms))

        total_ms = (hh * 3600 + mm * 60 + ss) * 1000 + ms

        return total_ms

    def combine_audio(self):
        # translited_str = self.replace_english_with_transliteration(self.srt_text)
        # num_to_words = self.replace_numbers_with_words(translited_str)
        #
        # words_with_accent = accentizer.process_all(num_to_words)
        # audio_segment, audio, audio_file = silero_tts(words_with_accent, self.client_id).text2audio()

        audio_file = silero_tts(self.srt_text, self.client_id).text2audio_openai()

        # file_path = self.rvc(audio)

        audio_segment = AudioSegment.from_wav(audio_file)

        return audio_segment, audio_file

    def speed_up_wav(self, desired_duration_ms, audiosegment):
        tempo = len(audiosegment)

        if desired_duration_ms < tempo:
            y = np.array(audiosegment.get_array_of_samples())
            if audiosegment.channels == 2:
                y = y.reshape((-1, 2))

            sample_rate = audiosegment.frame_rate

            tempo_ratio = tempo / desired_duration_ms

            y_fast = pyrb.time_stretch(y, sample_rate, tempo_ratio)

            channels = 2 if (y_fast.ndim == 2 and y_fast.shape[1] == 2) else 1
            y = np.int16(y_fast * 2 ** 15)

            audio = pydub.AudioSegment(y.tobytes(), frame_rate=sample_rate, sample_width=2, channels=channels)
        else:
            audio = AudioSegment.silent(duration=desired_duration_ms)
            audio = audio.overlay(audiosegment, position=desired_duration_ms - tempo)

        return audio
