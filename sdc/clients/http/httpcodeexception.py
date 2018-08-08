class HTTPCodeException(Exception):
    def __init__(self, expected, received, message):
        self.expected = expected
        self.received = received
        self.message = message

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
