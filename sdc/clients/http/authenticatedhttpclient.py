class AuthenticatedHTTPClient:
    def __init__(self, client, username: str, password: str):
        self.client = client
        self.auth = (username, password)

    def get(self, **kwargs):
        return self.client.get(**kwargs, auth=self.auth)

    def post(self, **kwargs):
        return self.client.post(**kwargs, auth=self.auth)

    def put(self, **kwargs):
        return self.client.put(**kwargs, auth=self.auth)
