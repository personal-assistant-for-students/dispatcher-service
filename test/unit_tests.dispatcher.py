import unittest
from unittest.mock import patch, Mock
import src.dispatcher_app as dp


class TestTelebot(unittest.TestCase):

    def setUp(self):
        # Создаем мок для объекта бота
        self.bot = Mock()
        dp.bot = self.bot  # Заменяем реальный бот на мок

    @patch('your_bot_module.requests.get')
    def test_handle_tasks(self, mock_get):
        # Подготавливаем мок для имитации ответа от внешнего сервиса
        mock_get.return_value = Mock(status_code=200, json=lambda: [{"id": "1", "title": "Test Task"}])

        # Вызываем функцию обработки команды /tasks
        message = Mock()
        dp.handle_tasks(message)

        # Проверяем, что бот отправил правильное сообщение
        self.bot.reply_to.assert_called_with(message, "Вот отсортированный по ближайшему дедлайну список ваших задач:")

    # Добавьте другие тесты для различных функций вашего бота


if __name__ == '__main__':
    unittest.main()
