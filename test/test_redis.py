import unittest
from unittest.mock import patch
from redis_manager import RedisManager


class TestRedisManager(unittest.TestCase):
    @patch('redis.StrictRedis')
    def test_connect(self, mock_redis):
        redis_instance = mock_redis.return_value
        redis_instance.ping.return_value = True

        manager = RedisManager()
        manager.connect()
        redis_instance.ping.assert_called_once()

    @patch('redis.StrictRedis')
    def test_set_value(self, mock_redis):
        redis_instance = mock_redis.return_value
        manager = RedisManager()
        manager.connect()

        manager.set_value('key', 'value')
        redis_instance.set.assert_called_once_with('key', 'value')

    @patch('redis.StrictRedis')
    def test_get_value(self, mock_redis):
        redis_instance = mock_redis.return_value
        redis_instance.get.return_value = 'value'
        manager = RedisManager()
        manager.connect()

        result = manager.get_value('key')
        redis_instance.get.assert_called_once_with('key')
        self.assertEqual(result, 'value')


if __name__ == '__main__':
    unittest.main()
