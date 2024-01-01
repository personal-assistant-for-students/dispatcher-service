import unittest
from unittest.mock import patch, MagicMock
from telegram_task_manager import TelegramTaskManager

class TestTelegramTaskManager(unittest.TestCase):
    @patch('telebot.TeleBot')
    @patch('redis_manager.RedisManager')
    def setUp(self, mock_redis, mock_telebot):
        self.manager = TelegramTaskManager()
        self.manager.bot = mock_telebot

    @patch('requests.post')
    def test_create_task(self, mock_post):
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {'id': '123'}

        self.manager.create_task({
            'title': 'Test Task',
            'content': 'Test Content',
            'deadline': '2023-12-31'
        }, 123456)

        mock_post.assert_called_once()

if __name__ == '__main__':
    unittest.main()