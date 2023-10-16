import yt_dlp
import moviepy.editor as mp
from moviepy.editor import *
import logging

import convert_text2speech

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def download_video(video_url: str, client_id: str):
    video_path = f'temp/video/{client_id}'

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': video_path
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(video_url, download=True)

    return video_path

def add_audio(audio_path):
    audio = mp.AudioFileClip(audio_path)

    return audio

def add_subtitle(start_time, duration, text):
    try:
        text_clip = mp.TextClip(text.replace("+", ""), fontsize=24, color='white', bg_color='black', font='Arial-Bold')
        text_clip = text_clip.set_start(start_time).set_duration(duration)
        text_clip = text_clip.set_position(('center', 'bottom'))

        return text_clip

    except Exception as e:
        logging.info("Error: ", e)

def count_ms(time_label):
    hh, mm, ss_ms = time_label.split(":")
    ss, ms = ss_ms.split(",")

    hh, mm, ss, ms = map(int, (hh, mm, ss, ms))

    total_ms = (hh * 3600 + mm * 60 + ss) * 1000 + ms

    return total_ms

def speed_up_video_segment(input_video, srt_text, client_id):
    text_list = srt_text.split("\n\n")
    start_time = 0
    dialogue_list = []
    time_labels = []
    time_length = []

    for text in text_list:
        lines = text.split("\n")
        time_labels.append(lines[1].split(" ")[0])
        time_length.append(count_ms(lines[1].split(" ")[2]) - count_ms(lines[1].split(" ")[0]))
        dialogue_list.append(lines[2])

    if len(dialogue_list) == len(time_labels):
        video_clip = VideoFileClip(input_video)
        video_segments = []

        for i, time_label in enumerate(time_labels):
            time = count_ms(time_label) / 1000
            audio_segment, audio = convert_text2speech.silero_tts(dialogue_list[i], client_id).combine_audio()
            tempo = len(audio_segment) / 1000
            time_length_float = time_length[i] / 1000

            edited_segment = (video_clip.subclip(time, time + time_length_float)
                              .fx(vfx.speedx, time_length_float / tempo))

            video_segment_with_subs = mp.CompositeVideoClip([edited_segment, add_subtitle(0, tempo, dialogue_list[i])])

            video_segment_with_subs_and_audio = video_segment_with_subs.set_audio(mp.AudioFileClip(audio))

            video_segments.append(video_segment_with_subs_and_audio)

            progress_num = i / len(dialogue_list) * 100
            yield progress_num

        yield 100
        edited_video = mp.concatenate_videoclips(video_segments)
        accelerated_video = edited_video.speedx(1.25)

        yield accelerated_video

    else:
        logging.info("неправильная структура srt")


def srt2video(video_url: str, srt_file: str, client_id: str):
    input_video_path = f"{download_video(video_url, client_id)}.mp4"

    video_with_audio = speed_up_video_segment(input_video_path, srt_file, client_id)

    for value in video_with_audio:
        if isinstance(value, float):
            yield value

        else:
            video_file_name = f"temp/video/output_{client_id}.mp4"

            value.write_videofile(video_file_name)

            yield video_file_name