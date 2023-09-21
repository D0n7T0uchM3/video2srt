import os
import whisper
import yt_dlp
from datetime import timedelta
import numpy as np
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
Model = config.get("Whisper", "model")
drive_whisper_path = config.get("Main", "drive_whisper_path")
download_path = config.get("Main", "download_path")

output_directory = config.get("Main", "output_directory")

def download_wav_file(video_url_list):
    video_path_local_list = []
    for url in video_url_list:

        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': download_path + '%(id)s.%(ext)s',
            'postprocessors': [{  # Extract audio using ffmpeg
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            list_video_info = [ydl.extract_info(url, download=True)]

        for video_info in list_video_info:
            video_path_local_list.append(Path(f"{video_info['id']}.wav"))

    return video_path_local_list

def run_whisper(video_name_local):
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

    video_transcription = whisper_model.transcribe(
        f"temp/{video_name_local}",
        temperature=temperature,
        **args,
    )
    
    return video_transcription

def convert_to_srt(url_list):
    list_of_local_files = download_wav_file(url_list)

    srt_list =[]
    
    for file_name in list_of_local_files:
        logging.info(f"### {file_name}")

        video_transcription = run_whisper(file_name)

        segments = video_transcription['segments']
        srtFilename = os.path.join(output_directory, f"{str(file_name).split('.')[0]}.srt")

        for segment in segments:
            startTime = str(0) + str(timedelta(seconds=int(segment['start']))) + ',000'
            endTime = str(0) + str(timedelta(seconds=int(segment['end']))) + ',000'
            text = segment['text']
            segmentId = segment['id'] + 1
            segment = f"{segmentId}\n{startTime} --> {endTime}\n{text[1:] if text[0] is ' ' else text}\n\n"
            with open(srtFilename, 'a', encoding='utf-8') as srtFile:
                srtFile.write(segment)

        srt_list.append(str(srtFilename))

        logging.info(f"**Done for {file_name}**")

    return srt_list