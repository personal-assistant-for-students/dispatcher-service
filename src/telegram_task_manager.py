import telebot
from telebot import types
import requests
from datetime import datetime
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE
from constant import TOKEN, TASK_SERVICE_URL, TASK_UPDATE_URL
from redis_manager import RedisManager
import config

def create_main_keyboard():
    """Creates and returns the main keyboard with commands for the bot."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("/joka", "/new", "/tasks")
    return keyboard


def get_additional_status_emoji(additional_status):
    """Returns an emoji representing the additional status of a task."""
    # Mapping additional statuses to emojis
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


def get_status_emoji(status):
    """Returns an emoji representing the status of a task."""
    # Mapping statuses to emojis
    if status == "Сделать":
        return "🔘"
    elif status == "Делаю":
        return "🟢"
    else:
        return ""


class TelegramTaskManager:
    def __init__(self):
        """Initializes the Telegram bot and sets up handlers for commands and messages."""
        self.bot = telebot.TeleBot(TOKEN)  # bot initialization
        self.redis_manager = RedisManager(config.REDIS_HOST, config.REDIS_PORT, config.REDIS_DB)  # create Redis Manager instance
        self.redis_manager.connect()
        self.calendar = Calendar(language=RUSSIAN_LANGUAGE)  # calendar initialization
        self.calendar_callback = CallbackData("calendar", "action", "year", "month", "day")

        self.user_task_data = {}  # dict for store new task of user
        self.register_handlers()  # registration of command and message handlers

    def run_bot(self):
        """Starts the bot and keeps it running."""
        self.bot.polling(none_stop=True)

    def register_handlers(self):
        """Registers handlers for different bot commands and messages."""

        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            self.handle_start(message)

        @self.bot.message_handler(commands=['joka'])
        def handle_joka(message):
            self.handle_joka(message)

        @self.bot.message_handler(commands=['new'])
        def handle_new_task(message):
            self.start_task_creation(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith(self.calendar_callback.prefix))
        def handle_calendar(call):
            user_id = call.from_user.id
            name, action, year, month, day = call.data.split(self.calendar_callback.sep)
            date = self.calendar.calendar_query_handler(bot=self.bot,
                                                        call=call,
                                                        name=name,
                                                        action=action,
                                                        year=year,
                                                        month=month,
                                                        day=day)
            if action == "DAY":
                self.user_task_data[user_id]['deadline'] = date.strftime("%Y-%m-%d")
                msg = self.bot.send_message(call.message.chat.id,
                                            "Что является результатом выполнения задачи, кратко опишите:")
                self.bot.register_next_step_handler(msg, self.set_task_description, user_id)
            elif action == "CANCEL":
                self.bot.send_message(call.message.chat.id, "Создание задачи отменено.",
                                      reply_markup=create_main_keyboard())
                self.user_task_data.pop(user_id, None)

        @self.bot.message_handler(commands=['tasks'])
        def handle_tasks(message):
            self.get_tasks(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("task_"))
        def handle_get_task_from_button_list(call):  # get task from the list
            task_id = call.data.split("_")[1]
            user_id = call.from_user.id
            try:
                response = requests.get(f"{TASK_SERVICE_URL}/{task_id}", json=user_id)
                if response.status_code == 200:
                    task = response.json()

                    # creation layout for buttons
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("Выполнено", callback_data=f"status_{task_id}_Выполнено"))
                    markup.add(types.InlineKeyboardButton("Делаю", callback_data=f"status_{task_id}_Делаю"))
                    markup.add(types.InlineKeyboardButton("Сделать", callback_data=f"status_{task_id}_Сделать"))

                    self.bot.send_message(call.message.chat.id,
                                          f"Информация о задаче:\nНазвание: {task['title']}\nДедлайн: {task['deadline']}\nЧто: {task['content']}\nСтатус: {task['status']}\nДоп. статус: {task['additional_status']}",
                                          reply_markup=markup)
                else:
                    self.bot.answer_callback_query(call.id, "Ошибка при получении задачи.")
            except Exception as e:
                self.bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("status_"))
        def handle_status_change(call):
            _, task_id, new_status = call.data.split("_")
            user_id = call.from_user.id
            update_url = TASK_UPDATE_URL.format(task_id=task_id)
            updated_data = {
                "user_id": user_id,
                "status": new_status
            }

            try:
                response = requests.put(update_url, json=updated_data)

                if response.status_code == 200:
                    task_response = requests.get(f"{TASK_SERVICE_URL}/{task_id}", json=call.from_user.id)

                    if task_response.status_code == 200:
                        task = task_response.json()
                        updated_task_info = f"Задача обновлена:\nНазвание: {task['title']}\nДедлайн: {task['deadline']}\nНовый статус: {task['status']}"
                        self.bot.send_message(call.message.chat.id, updated_task_info)
                    else:
                        self.bot.send_message(call.message.chat.id, "Ошибка при получении обновленной задачи.")
                else:
                    self.bot.send_message(call.message.chat.id, "Ошибка при обновлении статуса задачи.")

            except Exception as e:
                self.bot.send_message(call.message.chat.id, f"Ошибка: {str(e)}")

        @self.bot.message_handler(commands=['update'])
        def handle_update_task(message):
            self.update_task(message)

    def handle_start(self, message):
        """Handles the /start command."""
        user = f"user:{message.from_user.id}"
        mapping = {
            "username": message.from_user.username,
            "last_command": message.text,
            "lang_code": message.from_user.language_code
        }
        self.redis_manager.set_values(user , mapping)
        user_name = message.from_user.full_name
        self.bot.reply_to(message,
                          f"Привет {user_name}! Я ваш персональный ассистент, что будем делать сегодня?",
                          reply_markup=create_main_keyboard())

    def handle_joka(self, message):
        """Handles the /joka command by sending a joke."""
        self.bot.reply_to(message,
                          "Здесь будет сгенерирован лучший анекдот для {0}".format(message.from_user.full_name))

    def start_task_creation(self, message):
        """Starts the task creation process by asking for the task title."""
        user_id = message.from_user.id
        self.user_task_data[user_id] = {'title': '', 'deadline': '', 'description': ''}

        cancel_button = types.KeyboardButton('Отменить создание задачи')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(cancel_button)

        msg = self.bot.send_message(message.chat.id, "Введите название задачи:", reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.handle_task_creation, user_id)

    def handle_task_creation(self, message, user_id):
        """Processes the input for task title and asks for the deadline."""
        if message.text == 'Отменить создание задачи':
            self.bot.send_message(message.chat.id, "Создание задачи отменено.", reply_markup=create_main_keyboard())
            self.user_task_data.pop(user_id, None)
            return

        self.user_task_data[user_id]['title'] = message.text
        now = datetime.now()
        self.bot.send_message(message.chat.id,
                              "Выберите дату дедлайна:",
                              reply_markup=self.calendar.create_calendar(name=self.calendar_callback.prefix,
                                                                         year=now.year,
                                                                         month=now.month
                                                                         ))

    def set_task_description(self, message, user_id):
        """Processes the input for task description and creates the task."""
        if message.text == 'Отменить создание задачи':
            self.bot.send_message(message.chat.id, "Создание задачи отменено.", reply_markup=create_main_keyboard())
            self.user_task_data.pop(user_id, None)
            return

        self.user_task_data[user_id]['description'] = message.text

        # prepare new task
        task_data = {
            'user_id': user_id,
            'title': self.user_task_data[user_id]['title'],
            'content': self.user_task_data[user_id]['description'],
            'deadline': self.user_task_data[user_id]['deadline']
        }

        self.create_task(task_data, message.chat.id)

    def create_task(self, task_data, chat_id):
        """Sends a request to create a new task and informs the user."""
        try:
            response = requests.post(TASK_SERVICE_URL, json=task_data)
            if response.status_code == 201:
                self.bot.send_message(chat_id,
                                      f"Задача создана:\nНазвание: {task_data['title']}\nДедлайн: {task_data['deadline']}\nОписание: {task_data['content']}",
                                      reply_markup=create_main_keyboard())
            else:
                self.bot.send_message(chat_id, "Произошла ошибка при создании задачи.",
                                      reply_markup=create_main_keyboard())
        except Exception as e:
            self.bot.send_message(chat_id, f"Ошибка: {str(e)}", reply_markup=create_main_keyboard())

        # temp task can be clear
        self.user_task_data.pop(task_data['user_id'], None)

    def get_tasks(self, message):
        """Fetches and displays the list of tasks for the user."""
        user_id = message.from_user.id
        try:
            response = requests.get(TASK_SERVICE_URL, json=user_id)
            if response.status_code == 200:
                tasks = response.json()
                self.display_tasks(tasks, message)
            else:
                self.bot.reply_to(message, "Не удалось получить задачи.")
        except Exception as e:
            self.bot.reply_to(message, f"Ошибка: {str(e)}")

    def display_tasks(self, tasks, message):
        """Displays tasks to the user in a sorted manner with interactive buttons."""
        if len(tasks) == 0:
            self.bot.reply_to(message, "Делать было нечего дело было вечером, список задач пуст короче")
        else:
            # sorting by deadline
            tasks.sort(key=lambda x: datetime.strptime(x['deadline'], '%Y-%m-%d'))
            markup = types.InlineKeyboardMarkup()
            for task in tasks:
                additional_status_emoji = get_additional_status_emoji(task['additional_status'])
                status_emoji = get_status_emoji(task['status'])
                task_info = f"{status_emoji} {additional_status_emoji} {task['title']} - {task['status']}"
                task_button = types.InlineKeyboardButton(task_info, callback_data=f"task_{task['id']}")
                markup.add(task_button)
            self.bot.reply_to(message, "Вот отсортированный по ближайшему дедлайну список ваших задач:",
                              reply_markup=markup)

    def update_task(self, message):
        """Updating task status"""
        data = message.text.split()
        task_id = data[1]
        updated_data = {
            "user_id": message.from_user.id,
            "status": data[4]
        }
        try:
            response = requests.put(TASK_UPDATE_URL.format(task_id=task_id), json=updated_data)
            if response.status_code == 200:
                self.bot.reply_to(message, "Задача успешно обновлена.")
                self.get_tasks(message)  # get new list of tasks
            else:
                self.bot.reply_to(message, "Ошибка при обновлении задачи.")
        except Exception as e:
            self.bot.reply_to(message, f"Ошибка: {str(e)}")
