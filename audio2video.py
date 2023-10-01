import yt_dlp
import moviepy.editor as mp
import pysrt
import logging

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

def add_subtitle(srt_file):
    subs = pysrt.open(srt_file)

    subtitles_clips = []

    for sub in subs:
        text_clip = mp.TextClip(sub.text.replace("+", ""), fontsize=24, color='white', bg_color='black', font='Arial-Bold')
        start_time = sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds + sub.start.milliseconds / 1000
        end_time = sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds + sub.end.milliseconds / 1000
        duration = end_time - start_time
        text_clip = text_clip.set_start(start_time).set_duration(duration)
        text_clip = text_clip.set_position(('center', 'bottom'))
        subtitles_clips.append(text_clip)

    try:
        for sub in subs:
            text_clip = mp.TextClip(sub.text, fontsize=24, color='white', bg_color='black', font='Arial-Bold')
            start_time = sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds + sub.start.milliseconds / 1000
            end_time = sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds + sub.end.milliseconds / 1000
            duration = end_time - start_time
            text_clip = text_clip.set_start(start_time).set_duration(duration)
            text_clip = text_clip.set_position(('center', 'bottom'))
            subtitles_clips.append(text_clip)

    except Exception as e:
        logging.info("Error: ", e)

    return subtitles_clips

def srt2video(video_url: str, srt_file: str, audio_file: str, client_id: str):
    input_video_path = f"{download_video(video_url, client_id)}.mp4"


    video = mp.VideoFileClip(input_video_path)

    video_with_subtitles = mp.CompositeVideoClip([video] + add_subtitle(srt_file))

    final_video = video_with_subtitles.set_audio(add_audio(audio_file))

    video_file_name = f"temp/video/output_{client_id}.mp4"

    final_video.write_videofile(video_file_name)

    return video_file_name