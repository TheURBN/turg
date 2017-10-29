from datetime import datetime


class RateLimiter(object):
    requests = None  # max requests per minute
    cache = None

    def __init__(self, requests):
        self.requests = requests
        self.cache = {}

    def limit_exceeded(self, user):
        key = datetime.now().minute
        if user not in self.cache:
            self.cache[user] = {}
        try:
            if self.cache[user][key] >= self.requests:
                return True
            else:
                self.cache[user][key] += 1
        except KeyError:
            self.cache[user].clear()
            self.cache[user][key] = 1

        return False
