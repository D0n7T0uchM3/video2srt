from pyrogram import Client, filters
from pyrogram.types import *
import os
import logging
from dotenv import load_dotenv
import validators

import run_whisper
import audio2video
import openai_api

load_dotenv()

if not os.path.exists("temp"):
    os.mkdir("temp")

# Схема логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

bot = Client(
    "whisper",
    api_id=os.getenv("API_ID"),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("TOKEN")
)

reply_keyboard = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(
            text='/help'
        )
    ]
], resize_keyboard=True, one_time_keyboard=True, placeholder='Введите текст')

def get_srt(text):
    url_list = text.split("\n")

    if check_link(url_list):
        result = run_whisper.convert_to_srt(url_list)

    else:
        result = "Одна или несколько ваших ссылок недействительны! Пожалуйста перепроверьте данные!"

    return result

def check_link(link_list):
    for link in link_list:
        if not validators.url(link):
            return False

    return True

def remove_trailing_empty_lines(text):
    lines = text.splitlines()

    while lines and not lines[-1].strip():
        lines.pop()

    return '\n'.join(lines)

def check_srt(srt_file_name):
    if srt_file_name[-3:] == "srt":
        return True

    return False

def remove_temp_files(file_path):
    try:
        os.remove(file_path)
        logging.info(f"{file_path} deleted!")
    except OSError as e:
        logging.exception("Error: %s", e)

@bot.on_message(filters.command(["start"], prefixes=["/", "!"]))
async def start(client, message):
    PhotoStart = "data/img/start.png"

    await message.reply_photo(
        photo=PhotoStart,
        caption=
        f'Привет, друг!\n\n'
        f'Для транскрибации видео отправь мне ссылку на видео из видеохостинга YouTube, '
        f'если таких ссылок у тебя несколько - отправь их списком разделяя через перенос строки!\n\n'
        f'Если нужно составить тест по получившимуся .srt файлу, то просто отправь мне один файл с расширением и структурой ".srt"!\n\n'
        f'Ecли же необходимо изменить аудиодорожку в видео и добавить субтитры, то отправь мне ссылку на видео из '
        f'видеохостинга YouTube, а также в этом же сообщении прикрепи файл с расширением и '
        f'структурой ".srt"!',
        reply_markup=reply_keyboard)

@bot.on_message(filters.command(["help"], prefixes=["/", "!"]))
async def help(client, message):
    help_text = (f'Для транскрибации видео отправь мне ссылку на видео из видеохостинга YouTube, '
                f'если таких ссылок у тебя несколько - отправь их списком разделяя через перенос строки!\n\n'
                f'Если нужно составить тест по получившимуся .srt файлу, то просто отправь мне один файл с расширением и структурой ".srt"!\n\n'
                f'Ecли же необходимо изменить аудиодорожку в видео и добавить субтитры, то отправь мне ссылку на видео из '
                f'видеохостинга YouTube, а также в этом же сообщении прикрепи файл с расширением и '
                f'структурой ".srt"!')

    await message.reply_text(help_text, quote=True)

@bot.on_message(filters.text)
def message_from_user(client, message):
    msgs = message.text

    if not os.path.exists("temp/srt"):
        os.mkdir("temp/srt")

    K = message.reply_text("Взял в работу, идёт транскрибация текста, готовый результат будет через пару минут!")

    try:
        list_srt = get_srt(msgs)

        if type(list_srt) == str:
            # checked_srt = openai_api.text_generator(list_srt).check_srt()
            message.reply_text(list_srt, quote=True)

        else:
            for srt in list_srt:
                # checked_srt = openai_api.text_generator(list_srt).check_srt()
                message.reply_document(srt, reply_markup=reply_keyboard)

        for srt in list_srt:
            remove_temp_files(srt)

    except Exception as e:
        logging.exception("Error: %s", e)

        notworking = "data/img/error.png"
        message.reply_photo(
            photo=notworking,
            caption=f"Сейчас не могу ответить, возникла ошибка, попробуйте чуть позже или "
                        f"обратитесь в нашу тех. поддержку. Также просьба проверить ваш .srt файл, в "
                        f"нем возможно содержится ошибка, которая и повлияла на работу программы.\n\n"
                        f"Ошибка:\n{e}", reply_markup=reply_keyboard)

    K.delete()

@bot.on_message(filters.document)
def on_document(client, message):
    file_id = message.document.file_id
    file_name = message.document.file_name
    msgs = message.caption

    if not os.path.exists("temp/video"):
        os.mkdir("temp/video")

    if not os.path.exists("temp/video"):
        os.mkdir("temp/wav")

    message.download(file_name=f"temp/srt/{file_name}")

    if msgs != None:
        url_list = msgs.split("\n")

        if check_link(url_list):
            if check_srt(file_name):
                K = message.reply_text("Взял в работу, ваше видео будет готово через пару минут!")

                progress_reply_message = message.reply_text("Начало работы...")

                try:
                    with open(f"temp/srt/{file_name}") as f:
                        file_data = f.read()

                    data_with_checked_lines = remove_trailing_empty_lines(file_data)

                    video_path = audio2video.srt2video(url_list[0], data_with_checked_lines, file_id)

                    for value in video_path:
                        if isinstance(value, float):
                            progress_text = f"Прогресс выполнения: {value:.2f}%"
                            progress_reply_message.edit_text(progress_text)

                        else:
                            progress_reply_message.edit_text(
                                "Видео готово. Идет процесс рендеринга. Может занять пару минут.")

                            message.reply_document(value, reply_markup=reply_keyboard)

                except Exception as e:
                    logging.exception("Error: %s", e)

                    notworking = "data/img/error.png"
                    message.reply_photo(
                        photo=notworking,
                        caption=f"Сейчас не могу ответить, возникла ошибка, попробуйте чуть позже или "
                        f"обратитесь в нашу тех. поддержку. Также просьба проверить ваш .srt файл, в "
                        f"нем возможно содержится ошибка, которая и повлияла на работу программы.\n\n"
                        f"Ошибка:\n{e}", reply_markup=reply_keyboard)

                K.delete()
                progress_reply_message.delete()

            else:
                message.reply_text("Неверный формат файла, проверьте данные! "
                                   "Необходимый формат - "".srt!""", quote=True, reply_markup=reply_keyboard)

        else:
            message.reply_text("Неверная ссылка, проверьте данные!", quote=True)

    else:
        K = message.reply_text("Взял в работу, тест будет готов через минуту!")
        
        try:                        
            with open(f'temp/srt/{file_name}', 'r') as input_file:
                filtered_text = ''
            
                for line in input_file:
                    if not line.startswith("00:") and not line.strip().isdigit() and line.strip():
                        filtered_text += line + '\n'
                
            filtered_text = filtered_text.replace("+","")
            
            test = openai_api.text_generator(filtered_text).test()
            
            with open(f"temp/srt/{file_id}_test.txt", "w") as f:
                f.write(test)
    
            message.reply_document(f"temp/srt/{file_id}_test.txt")
        
        except Exception as e:
            logging.exception("Error: %s", e)

            notworking = "data/img/error.png"
            message.reply_photo(
                photo=notworking,
                caption=f"Сейчас не могу ответить, возникла ошибка, попробуйте чуть позже или "
                        f"обратитесь в нашу тех. поддержку. Также просьба проверить ваш .srt файл, в "
                        f"нем возможно содержится ошибка, которая и повлияла на работу программы.\n\n"
                        f"Ошибка:\n{e}", reply_markup=reply_keyboard)

        K.delete()
        
bot.run()