import telebot
from telebot import types
import requests
from datetime import datetime
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

TOKEN = "YOUR_TOKEN"
bot = telebot.TeleBot(TOKEN)

HOST = "http://127.0.0.1:5000"

TASK_SERVICE_URL = HOST + "/tasks"
TASK_UPDATE_URL = TASK_SERVICE_URL + "/{task_id}"

# calendar and CallbackData for managing choosing date
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_callback = CallbackData("calendar", "action", "year", "month", "day")

# dictionary for temp storing new task
task_creation_data = {}


def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("/joka", "/new", "/tasks")
    return keyboard


@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "Привет! Я ваш персональный ассистент, что будем делать сегодня?",
                 reply_markup=create_main_keyboard())


@bot.message_handler(commands=['joka'])
def handle_start(message):
    bot.reply_to(message, "Здесь будет сгенерирован лучший анекдот")


@bot.message_handler(commands=['new'])
def start_task_creation(message):
    msg = bot.send_message(message.chat.id, "Введите название задачи:")
    bot.register_next_step_handler(msg, set_task_title)


@bot.message_handler(commands=['tasks'])
def handle_tasks(message):
    try:
        response = requests.get(TASK_SERVICE_URL)
        if response.status_code == 200:
            tasks = response.json()
            if len(tasks) == 0:
                bot.reply_to(message, "Делать было нечего дело было вечером, список задач пуст короче")
            else:
                # sorting by deadline
                tasks.sort(key=lambda x: datetime.strptime(x['deadline'], '%Y-%m-%d'))
                markup = types.InlineKeyboardMarkup()
                for task in tasks:
                    status_emoji = get_status_emoji(task['additional_status'])
                    task_info = f"{status_emoji} {task['title']} - {task['status']}"
                    task_button = types.InlineKeyboardButton(task_info, callback_data=f"task_{task['id']}")
                    markup.add(task_button)
                bot.reply_to(message, "Вот отсортированный по ближайшему дедлайну список ваших задач:",
                             reply_markup=markup)
        else:
            bot.reply_to(message, "Не удалось получить задачи.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")


def set_task_title(message):
    task_creation_data['title'] = message.text
    now = datetime.now()
    bot.send_message(message.chat.id, "Выберите дату дедлайна:", reply_markup=calendar.create_calendar(
        name=calendar_callback.prefix,
        year=now.year,
        month=now.month
    ))


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_callback.prefix))
def handle_calendar(call):
    name, action, year, month, day = call.data.split(calendar_callback.sep)
    date = calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month, day=day
    )
    if action == "DAY":
        task_creation_data['deadline'] = date.strftime("%Y-%m-%d")
        msg = bot.send_message(call.message.chat.id, "Что является результатом выполнения задачи, кратко опишите:")
        bot.register_next_step_handler(msg, set_task_description)
    elif action == "CANCEL":
        bot.send_message(call.message.chat.id, "Создание задачи отменено.")


def set_task_description(message):
    task_creation_data['description'] = message.text

    # prepare new task
    task_data = {
        'title': task_creation_data['title'],
        'content': task_creation_data['description'],
        'deadline': task_creation_data['deadline']
    }

    # send new task to task manager
    try:
        response = requests.post(TASK_SERVICE_URL, json=task_data)
        if response.status_code == 201:
            bot.send_message(message.chat.id,
                             f"Задача создана:\nНазвание: {task_creation_data['title']}\nДедлайн: {task_creation_data['deadline']}\nОписание: {task_creation_data['description']}")
        else:
            bot.send_message(message.chat.id, "Произошла ошибка при создании задачи.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {str(e)}")

    # temp task can be clear
    task_creation_data.clear()


def get_status_emoji(additional_status):
    if additional_status == "Сгорел":
        return "💀"
    elif additional_status == "Адище":
        return "🔥"
    if additional_status == "Горит":
        return "🤬"
    elif additional_status == "Теплый":
        return "🥵"
    else:
        return "🥶"


@bot.callback_query_handler(func=lambda call: call.data.startswith("task_"))
def task_callback(call):
    task_id = call.data.split("_")[1]
    try:
        response = requests.get(f"{TASK_SERVICE_URL}/{task_id}")
        if response.status_code == 200:
            task = response.json()

            # creation layout for buttons
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Выполнено", callback_data=f"status_{task_id}_Выполнено"))
            markup.add(types.InlineKeyboardButton("Делаю", callback_data=f"status_{task_id}_Делаю"))
            markup.add(types.InlineKeyboardButton("Сделать", callback_data=f"status_{task_id}_Сделать"))

            bot.send_message(
                call.message.chat.id,
                f"Информация о задаче:\nНазвание: {task['title']}\nДедлайн: {task['deadline']}\nЧто: {task['content']}\nСтатус: {task['status']}\nДоп. статус: {task['additional_status']}",
                reply_markup=markup
            )
        else:
            bot.answer_callback_query(call.id, "Ошибка при получении задачи.")
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("status_"))
def handle_status_change(call):
    _, task_id, new_status = call.data.split("_")

    update_url = TASK_UPDATE_URL.format(task_id=task_id)
    updated_data = {"status": new_status}

    try:
        response = requests.put(update_url, json=updated_data)

        if response.status_code == 200:
            task_response = requests.get(f"{TASK_SERVICE_URL}/{task_id}")

            if task_response.status_code == 200:
                task = task_response.json()
                updated_task_info = f"Задача обновлена:\nНазвание: {task['title']}\nДедлайн: {task['deadline']}\nНовый статус: {task['status']}"
                bot.send_message(call.message.chat.id, updated_task_info)
            else:
                bot.send_message(call.message.chat.id, "Ошибка при получении обновленной задачи.")
        else:
            bot.send_message(call.message.chat.id, "Ошибка при обновлении статуса задачи.")

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка: {str(e)}")


@bot.message_handler(func=lambda message: message.text.startswith("/update"))
def update_task(message):
    data = message.text.split()
    task_id = data[1]
    updated_data = {
        "title": data[2],
        "deadline": data[3],
        "status": data[4],
        "additional_status": data[5]
    }
    try:
        response = requests.put(TASK_UPDATE_URL.format(task_id=task_id), json=updated_data)
        if response.status_code == 200:
            bot.reply_to(message, "Задача успешно обновлена.")
            handle_tasks(message)  # get new list of tasks
        else:
            bot.reply_to(message, "Ошибка при обновлении задачи.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")


def main():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()