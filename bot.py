# импортируем необходимые библиотеки, токены и ссылки
import requests
from transformers import AutoTokenizer
from pprint import pprint
# from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from config import token, url
import json
import telebot
import logging

# копируем из Практикума
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w",)


# настраиваем поведение GPT и всякие формальности
bot = telebot.TeleBot(token)
system_content = ''
assistant_content = 'Решим задачу по шагам:'
user_content = ""
result = ''
answer = ''

max_tokens_in_task = 2048
# kb = types.InlineKeyboardMarkup()
kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
status = 1

# функция для сохранения данных


def load_data():
    try:
        with open('users.json', "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    return data


def save_data(data):
    with open('users.json', "w") as f:
        json.dump(data, f)

# модуль с прикладными командами -------
# /start


@bot.message_handler(commands=['start'])
def hello(message):
    # button1 = types.InlineKeyboardButton(text='запрос к GPT', callback_data='/solve_task')
    # button2 = types.InlineKeyboardButton(text='инфо', callback_data='/help')
    # kb.add(button1)
    # kb.add(button2)
    user_id = message.chat.id
    help = KeyboardButton(text="/help")
    solve = KeyboardButton(text="/solve_task")
    kb.add(help, row_width=3)
    kb.add(solve, row_width=3)
    bot.send_message(user_id, text='Привет, это бот-GPT, который может помочь '
                                   'решить задачи по алгебре', reply_markup=kb)
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {}
    data[str(user_id)] = {'status': 0, 'admin': ''}
    save_data(data)


# /help
@bot.message_handler(commands=['help'])
def info(message):
    user_id = message.chat.id
    bot.send_message(user_id, text='Инструкция по использованию:\n'
                                   '1. используйте команду /solve_task\n'
                                   '2. введите свой запрос и подождите\n'
                                   '3. введите "продолжи", для продолжения ответа\n'
                                   '4. или введите новый запрос\n'
                                   '5. для завершения работы напишите "конец"')

# ---------------------------------------------------------------------------------------
# GPT


@bot.message_handler(commands=['solve_task'])
def solve_task(message):
    user_id = message.from_user.id
    bot.send_message(user_id, text="Напиши запрос")
    # регистрируем следующий "шаг"
    bot.register_next_step_handler(message, get_response)


def get_response(message):
    global answer, result
    user_id = message.from_user.id
    user_prompt = message.text
    data = load_data()
    data[str(user_id)] = {'status': 1, 'admin': 'F'}
    if str(user_id) == "1439318759":
        data[str(user_id)] = {'status': 1, 'admin': 'T'}
    save_data(data)
    # убеждаемся, что получили текстовое сообщение, а не что-то другое
    if message.content_type != "text":
        bot.send_message(user_id, text="Отправь промт текстовым сообщением")
        bot.register_next_step_handler(message, get_response)
        return

    # Получение запроса от пользователя
    if len(user_prompt.lower()) > max_tokens_in_task:
        bot.send_message(user_id, text="запрос слишком длинный")
        bot.register_next_step_handler(message, get_response)

    elif user_prompt.lower() == 'конец':
        bot.send_message(user_id, text='вы завершили работу команды')
        exit(0)
    else:
        bot.send_message(user_id, text="Промт принят! Ожидайте.")
    # блок для проверки и обработки сообщений

    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt},
                {"role": "system", "content": assistant_content + answer},
            ],
            "temperature": 1,
            "max_tokens": 40
        }
    )
    if resp.status_code == 200 and 'choices' in resp.json():
        result = resp.json()['choices'][0]['message']['content']
        if result == '':
            bot.send_message(message.chat.id, result)
        else:
            answer += result
            bot.send_message(message.chat.id, f'Ответ: {result}')
    else:
        logging.error(f'Не удалось получить ответ от нейросети.\nЗапрос:\n{user_content}')
        bot.send_message(user_id, text='Не удалось получить ответ от нейросети')
        bot.send_message(user_id, text=f'Текст ошибки: {resp.json()}')
    solve_task(message)
    return answer


@bot.message_handler(commands=['continue'])
def con_reply(message):
    global assistant_content
    user_id = message.chat.id
    data = load_data()
    assistant_content += answer
    if data[str(user_id)]['status'] == 1 or data[str(user_id)]['status'] == 2:
        get_response(message)
    else:
        logging.warning("Пользователь еще не отправил первый запрос")
        bot.send_message(user_id, 'Вы еще не отправляли первый запрос. Воспользуйтесь /solve_task')

# ------------------------debug--------------------------


@bot.message_handler(commands=['debug'])
def debug(message):
    user_id = message.chat.id
    data = load_data()
    if data[str(user_id)]['admin'] == 'T':
        try:
            with open("log_file.txt", "rb") as f:
                bot.send_document(message.chat.id, f)

        except FileNotFoundError:
            bot.send_message(user_id, 'У вас нет ошибок')
    else:
        bot.send_message(user_id, 'Вы не можете использовать эту команду.')


bot.polling()
