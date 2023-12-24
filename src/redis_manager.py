import redis


class RedisManager:
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.connection = None

    def connect(self):
        """Establish a connection to the Redis server."""
        try:
            self.connection = redis.StrictRedis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            self.connection.ping()
            print("Connected to Redis")
        except Exception as e:
            print(f"Error connecting to Redis: {e}")

    def set_value(self, key, value):
        """Set a value in Redis."""
        try:
            self.connection.set(key, value)
        except Exception as e:
            print(f"Error setting value in Redis: {e}")

    def set_values(self, key, mapping):
        """Set a value in Redis."""
        try:
            self.connection.hmset(key, mapping)
        except Exception as e:
            print(f"Error setting value in Redis: {e}")

    def get_value(self, key):
        """Get a value from Redis."""
        try:
            return self.connection.get(key)
        except Exception as e:
            print(f"Error getting value from Redis: {e}")
            return None
