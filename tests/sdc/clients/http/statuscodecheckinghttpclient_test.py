import unittest
from unittest.mock import MagicMock, Mock

from sdc.clients.http.httpcodeexception import HTTPCodeException
from sdc.clients.http.statuscodecheckinghttpclient import \
    StatusCodeCheckingHTTPClient
from tests.shared.requests import Requests


class StatusCodeCheckingHTTPClientTest(unittest.TestCase, Requests):
    def setUp(self):
        self.decorated_client = Mock()
        self.client = StatusCodeCheckingHTTPClient(self.decorated_client)

    def test_get_delegates_request_works_with_no_expected_status(self):
        requests_response = self._stub_get_response(200)

        response = self.client.get(url='http://example.com')

        self.decorated_client.get.assert_called_with(url='http://example.com')
        self.assertEqual(requests_response, response)

    def test_get_delegates_request_to_decorated_client(self):
        requests_response = self._stub_get_response(200)

        response = self.client.get(url='http://example.com',
                                   expected_status=200)

        self.decorated_client.get.assert_called_with(url='http://example.com')
        self.assertEqual(requests_response, response)

    def test_get_raises_for_unexpected_status_codes(self):
        self._stub_get_response(201, 'body')

        with self.assertRaises(HTTPCodeException) as context:
            self.client.get(url='http://example.com',
                            expected_status=200)

        self.assertEqual(HTTPCodeException(
            200, 201,
            'GET http://example.com returned an unexpected status code 201 (expected 200): body'),
            context.exception)

    def test_post_delegates_request_works_with_no_expected_status(self):
        requests_response = self._stub_post_response(200)

        response = self.client.post(url='http://example.com',
                                    json={'ok': 'true'})

        self.decorated_client.post.assert_called_with(url='http://example.com',
                                                      json={'ok': 'true'})
        self.assertEqual(requests_response, response)

    def test_post_delegates_request_to_decorated_client(self):
        requests_response = self._stub_post_response(200)

        response = self.client.post(url='http://example.com',
                                    json={'ok': 'true'},
                                    expected_status=200)

        self.decorated_client.post.assert_called_with(url='http://example.com',
                                                      json={'ok': 'true'})
        self.assertEqual(requests_response, response)

    def test_post_raises_for_unexpected_status_codes(self):
        self._stub_post_response(201, 'body')

        with self.assertRaises(HTTPCodeException) as context:
            self.client.post(url='http://example.com',
                             json={'ok': 'true'},
                             expected_status=200)

        self.assertEqual(HTTPCodeException(
            200, 201,
            'POST http://example.com returned an unexpected status code 201 (expected 200): body'),
            context.exception)

    def test_put_delegates_request_works_with_no_expected_status(self):
        requests_response = self._stub_put_response(200)

        response = self.client.put(url='http://example.com',
                                   json={'ok': 'true'})

        self.decorated_client.put.assert_called_with(url='http://example.com',
                                                     json={'ok': 'true'})
        self.assertEqual(requests_response, response)

    def test_put_delegates_request_to_decorated_client(self):
        requests_response = self._stub_put_response(200)

        response = self.client.put(url='http://example.com',
                                   json={'ok': 'true'},
                                   expected_status=200)

        self.decorated_client.put.assert_called_with(url='http://example.com',
                                                     json={'ok': 'true'})
        self.assertEqual(requests_response, response)

    def test_put_raises_for_unexpected_status_codes(self):
        self._stub_put_response(201, 'body')

        with self.assertRaises(HTTPCodeException) as context:
            self.client.put(url='http://example.com',
                            json={'ok': 'true'},
                            expected_status=200)

        self.assertEqual(HTTPCodeException(
            200, 201,
            'PUT http://example.com returned an unexpected status code 201 (expected 200): body'),
            context.exception)

    def _stub_get_response(self, status_code, body='default content'):
        response = self.http_response(status_code=status_code, body=bytes(body, 'utf-8'))
        self.decorated_client.get = MagicMock(return_value=response)

        return response

    def _stub_post_response(self, status_code, body='default content'):
        response = self.http_response(status_code=status_code, body=bytes(body, 'utf-8'))
        self.decorated_client.post = MagicMock(return_value=response)

        return response

    def _stub_put_response(self, status_code, body='default content'):
        response = self.http_response(status_code=status_code, body=bytes(body, 'utf-8'))
        self.decorated_client.put = MagicMock(return_value=response)

        return response
