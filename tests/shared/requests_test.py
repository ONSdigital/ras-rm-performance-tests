from unittest import TestCase

from tests.shared.requests import Requests


class RequestsTest(TestCase):
    def test_http_response_with_no_body(self):
        response = Requests.http_response(201)

        self.assertEqual(201, response.status_code)
        self.assertEqual('', response.text)

    def test_http_response_with_body_content(self):
        response = Requests.http_response(200, 'hello world')

        self.assertEqual(200, response.status_code)
        self.assertEqual('hello world', response.text)

    def test_http_response_with_binary_body_content(self):
        response = Requests.http_response(200, b'hello world')

        self.assertEqual(200, response.status_code)
        self.assertEqual('hello world', response.text)

    def test_http_response_with_json_object_content(self):
        response = Requests.http_response(200, {'key': 'value'})

        self.assertEqual(200, response.status_code)
        self.assertEqual({'key': 'value'}, response.json())

    def test_http_response_with_json_list_content(self):
        response = Requests.http_response(200, [{'key': 'value'}])

        self.assertEqual(200, response.status_code)
        self.assertEqual([{'key': 'value'}], response.json())