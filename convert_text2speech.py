import os
import logging
import torch
import configparser
import pydub
import numpy as np
import pyrubberband as pyrb
from pydub import AudioSegment
from transliterate import translit
from num2words import num2words

config = configparser.ConfigParser()
config.read("config.ini")

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
device = torch.device('cuda:0')  # gpu or cpu
speaker = 'aidar'
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

        audio = model.save_wav(text=self.text,
                               speaker=speaker,
                               sample_rate=sample_rate,
                               put_accent=put_accent,
                               put_yo=put_yo,
                               audio_path=f'temp/wav/{self.client_id}_tts.wav')

        audio_segment = AudioSegment.from_wav(audio)

        return audio_segment, audio


class combined_audio():
    def __init__(self, srt_text: str, client_id: str):
        self.srt_text = srt_text
        self.client_id = client_id

    def remove_temp_files(self, file_path):
        try:
            os.remove(file_path)
            logging.info(f"{file_path} deleted!")
        except OSError as e:
            logging.info(f"Error while deleting {file_path}: {e}")

    def replace_english_with_transliteration(self, text: str):
        words = text.split()
        result = []
        for word in words:
            # Если слово состоит только из английских букв, то транскрибируем его
            if word.isalpha() and word.isascii():
                transliterated_word = translit(word, "ru")
                result.append(transliterated_word)
            else:
                result.append(word)
        return ' '.join(result)

    def replace_numbers_with_words(self, text: str):
        words = text.split()
        result = []
        for word in words:
            if word.isdigit():
                word_as_words = num2words(int(word), lang='ru')
                result.append(word_as_words)
            else:
                result.append(word)
        return ' '.join(result)

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
            try:
                for i, time_label in enumerate(time_labels):
                    time = self.count_ms(time_label)
                    translited_str = self.replace_english_with_transliteration(dialogue_list[i])
                    num_to_words = self.replace_numbers_with_words(translited_str)
                    audio_segment, audio = silero_tts(num_to_words, self.client_id).text2audio()
                    edited_audio = self.speed_up_wav(time_length[i], audio_segment)
                    result_audio = result_audio.overlay(edited_audio, position=time)

                    self.remove_temp_files(audio)

                    progress_num = i / len(dialogue_list) * 100
                    yield progress_num

            except Exception as e:
                error_message = f"Произошла ошибка чтения srt файла, проверьте его правильность, номер реплики с потенциальной ошибкой: {i}"
                yield error_message

            result_audio.export(f"temp/wav/{self.client_id}.wav", format="wav")

            yield f"temp/wav/{self.client_id}.wav"

        else:
            logging.info("неправильная структура srt")

    def count_ms(self, time_label):
        hh, mm, ss_ms = time_label.split(":")
        ss, ms = ss_ms.split(",")

        hh, mm, ss, ms = map(int, (hh, mm, ss, ms))

        total_ms = (hh * 3600 + mm * 60 + ss) * 1000 + ms

        return total_ms

    def speed_up_wav(self, desired_duration_ms, audiosegment):
        tempo = len(audiosegment)

        if desired_duration_ms < tempo:
            y = np.array(audiosegment.get_array_of_samples())
            if audiosegment.channels == 2:
                y = y.reshape((-1, 2))

            sample_rate = audiosegment.frame_rate

            tempo_ratio = tempo / desired_duration_ms

            print(desired_duration_ms, tempo, tempo_ratio)

            y_fast = pyrb.time_stretch(y, sample_rate, tempo_ratio)

            channels = 2 if (y_fast.ndim == 2 and y_fast.shape[1] == 2) else 1
            y = np.int16(y_fast * 2 ** 15)

            audio = pydub.AudioSegment(y.tobytes(), frame_rate=sample_rate, sample_width=2, channels=channels)
        else:
            audio = AudioSegment.silent(duration=desired_duration_ms)
            audio = audio.overlay(audiosegment, position=desired_duration_ms-tempo)

        return audio
