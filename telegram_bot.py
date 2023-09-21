from pyrogram import Client, filters
from pyrogram.types import *
import os
import logging
from dotenv import load_dotenv
import validators

import run_whisper
import convert_text2speech

load_dotenv()

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

@bot.on_message(filters.command(["start"], prefixes=["/", "!"]))
async def start(client, message):
    PhotoStart = "data/img/start.png"

    await message.reply_photo(
        photo=PhotoStart,
        caption=
        f'Привет, друг!\n\n'
        f'Для транскрибации видео отправь мне ссылку на видео из видеохостинга YouTube, '
        f'если таких ссылок у тебя несколько - отправь их списком разделяя через перенос строки!\n\n'
        f'Если нужно перевести текст в аудио, то отправь мне один файл с расширением и структурой ".srt"!',
        reply_markup=reply_keyboard)

@bot.on_message(filters.command(["help"], prefixes=["/", "!"]))
async def help(client, message):
    help_text = (f'Для транскрибации видео отправь мне ссылку на видео из видеохостинга YouTube, '
                 f'если таких ссылок у тебя несколько - отправь их списком разделяя через перенос строки!\n\n'
                 f'Если нужно перевести текст в аудио, то отправь мне один файл с расширением и структурой ".srt"!')

    await message.reply_text(help_text, quote=True)

@bot.on_message(filters.text)
def message_from_user(client, message):
    msgs = message.text

    K = message.reply_text("Взял в работу, идёт транскрибация текста, готовый результат будет через пару минут!")

    try:
        list_srt = get_srt(msgs)

        if type(list_srt) == str:
            message.reply_text(list_srt, quote=True)

        else:
            for srt in list_srt:
                message.reply_document(srt)

    except Exception:
        notworking = "data/img/error.png"
        message.reply_photo(
            photo=notworking,
            caption=f"Сейчас не могу ответить, ведутся технические работы, попробуйте чуть позже или обратитесь в нашу тех. поддержку")

    K.delete()

@bot.on_message(filters.document)
def on_document(client, message):
    file_id = message.document.file_id
    file_name = message.document.file_name

    message.download(file_name=f"temp/srt/{file_name}")

    if check_srt(file_name):
        K = message.reply_text("Взял в работу, ваша аудиозапись будет готова через пару минут!")

        try:
            with open(f"temp/srt/{file_name}") as f:
                file_data = f.read()

            data_with_checked_lines = remove_trailing_empty_lines(file_data)

            result_wav_file = convert_text2speech.combined_audio(data_with_checked_lines, file_id).combine_audio()

            message.reply_document(result_wav_file)

        except:
            notworking = "data/img/error.png"
            message.reply_photo(
                photo=notworking,
                caption=f"Сейчас не могу ответить, ведутся технические работы, попробуйте чуть позже или обратитесь в нашу тех. поддержку")

        K.delete()

    else:
        message.reply_text("Неверный формат файла, проверьте данные! Необходимый формат - "".srt!""", quote=True)


bot.run()