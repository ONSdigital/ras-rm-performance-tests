class Mixins:
    csrf_token = None
    auth_cookie = None

    def get(self, url: str, expected_response_text=None):
        with self.client.get(url=url, allow_redirects=False, catch_response=True) as response:

            if response.status_code != 200:
                error = f"Expected a 200 but got a {response.status_code} for url {url}"
                response.failure(error)
                self.interrupt()

            if expected_response_text and expected_response_text not in response.text:
                error = f"response text ({expected_response_text}) isn't in returned html"
                response.failure(error)
                self.interrupt()

            return response

    def post(self, url: str, data: dict = {}):
        data['csrf_token'] = self.csrf_token
        with self.client.post(url=url, data=data, allow_redirects=False, catch_response=True) as response:

            if response.status_code != 302:
                error = f"Expected a 302 but got a ({response.status_code}) for url {url} and data {data}"
                response.failure(error)
                self.interrupt()

            return response
