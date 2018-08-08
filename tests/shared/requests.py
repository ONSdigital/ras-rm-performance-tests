import json

from requests import Response


class Requests:
    @staticmethod
    def http_response(status_code, body=''):
        if isinstance(body, list) or isinstance(body, dict):
            body = json.dumps(body)

        if isinstance(body, str):
            body = bytes(body, 'utf-8')

        response = Response()
        response.status_code = status_code
        response.encoding = 'utf-8'
        response._content = body
        return response
