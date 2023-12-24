from dotenv import load_dotenv
import os

load_dotenv("../set_env.env") # load env var, temp solution FIXME use vault for store sensitive data
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
HOST = os.getenv('TASK_APP_HOST')
TASK_SERVICE_URL = HOST.format("/tasks")
TASK_UPDATE_URL = TASK_SERVICE_URL + "/{task_id}"
