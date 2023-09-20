import os
import whisper
import yt_dlp
from datetime import timedelta
import numpy as np
import csv
import logging
import configparser
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

config = configparser.ConfigParser()
config.read("config.ini")

language = config.get("Whisper", "language")
verbose = config.get("Whisper", "verbose")
output_format = config.get("Whisper", "output_format")
task = config.get("Whisper", "task")
temperature_conf = float(config.get("Whisper", "temperature"))
temperature_increment_on_fallback_conf = float(config.get("Whisper", "temperature_increment_on_fallback"))
best_of = int(config.get("Whisper", "best_of"))
beam_size = int(config.get("Whisper", "beam_size"))
patience = float(config.get("Whisper", "patience"))
length_penalty = float(config.get("Whisper", "length_penalty"))
suppress_tokens = config.get("Whisper", "suppress_tokens")
initial_prompt = config.get("Whisper", "initial_prompt")
condition_on_previous_text = bool(config.get("Whisper", "condition_on_previous_text"))
fp16 = bool(config.get("Whisper", "fp16"))
compression_ratio_threshold = float(config.get("Whisper", "compression_ratio_threshold"))
logprob_threshold = float(config.get("Whisper", "logprob_threshold"))
no_speech_threshold = float(config.get("Whisper", "no_speech_threshold"))
drive_whisper_path = config.get("Whisper", "drive_whisper_path")
Model = config.get("Whisper", "model")
download_path = config.get("Whisper", "download_path")

csv_file = "videos.csv"
output_directory = "output"

def read_from_csv():
    with open(csv_file, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        headers = next(reader)

        id_column_index = headers.index("ID")

        video_url_list = []

        for row in reader:
            video_id = row[id_column_index]

            url = f"https://youtu.be/{video_id}"

            video_url_list.append(url)

    return video_url_list

def download_wav_file(video_url_list):
    video_path_local_list = []

    for url in video_url_list:
        video_path = os.path.join(download_path, f"{url.split('/')[-1].replace('.', '')}.wav")
        if not os.path.exists(video_path):

            ydl_opts = {
                'format': 'm4a/bestaudio/best',
                'outtmpl': download_path + '%(id)s.%(ext)s',
                'postprocessors': [{  # Extract audio using ffmpeg
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                list_video_info = [ydl.extract_info(url, download=False)]

            for video_info in list_video_info:
                video_path_local_list.append(Path(f"{video_info['id']}.wav"))

        else:
            logging.info(f"This '{video_path}' already exists.")

    return video_path_local_list

def run_whisper(video_path_local):
    verbose_lut = {
        'Live transcription': True,
        'Progress bar': True,
        'None': None
    }

    args = dict(
        language=(None if language == "Auto detection" else language),
        verbose=verbose_lut[verbose],
        task=task,
        temperature=temperature_conf,
        temperature_increment_on_fallback=temperature_increment_on_fallback_conf,
        best_of=best_of,
        beam_size=beam_size,
        patience=patience,
        length_penalty=(length_penalty if length_penalty >= 0.0 else None),
        suppress_tokens=suppress_tokens,
        initial_prompt=(None if not initial_prompt else initial_prompt),
        condition_on_previous_text=condition_on_previous_text,
        fp16=fp16,
        compression_ratio_threshold=compression_ratio_threshold,
        logprob_threshold=logprob_threshold,
        no_speech_threshold=no_speech_threshold
    )

    temperature = args.pop("temperature")
    temperature_increment_on_fallback = args.pop("temperature_increment_on_fallback")

    if temperature_increment_on_fallback is not None:
        temperature = tuple(np.arange(temperature, 1.0 + 1e-6, temperature_increment_on_fallback))

    else:
        temperature = [temperature]

    whisper_model = whisper.load_model(Model)

    video_transcription = whisper.transcribe(
        whisper_model,
        str(os.path.join(download_path, f"{video_path_local.split('/')[-1]}.wav")),
        temperature=temperature,
        **args,
    )
    
    return video_transcription

def convert_to_srt():
    video_url_list = read_from_csv()
    video_path_local_list = download_wav_file(video_url_list)
    
    for video_path_local in video_path_local_list:
        logging.info(f"### {video_path_local}")

        video_transcription = run_whisper(video_path_local)

        segments = video_transcription['segments']
    
        for segment in segments:
            startTime = str(0) + str(timedelta(seconds=int(segment['start']))) + ',000'
            endTime = str(0) + str(timedelta(seconds=int(segment['end']))) + ',000'
            text = segment['text']
            segmentId = segment['id'] + 1
            segment = f"{segmentId}\n{startTime} --> {endTime} client\n{text[1:] if text[0] is ' ' else text}\n\n"
            srtFilename = os.path.join(output_directory, f"{video_path_local}.srt")
            with open(srtFilename, 'a', encoding='utf-8') as srtFile:
                srtFile.write(segment)
    
        logging.info(f"**Done for {video_path_local}**")

def main():
    convert_to_srt()

if __name__ == "__main__":
    main()

# # Save output
# whisper.utils.get_writer(
#     output_format=output_format,
#     output_dir=video_path_local.parent
# )(
#     video_transcription,
#     str(video_path_local.stem),
#     options=dict(
#         highlight_words=False,
#         max_line_count=None,
#         max_line_width=None,
#     )
# )