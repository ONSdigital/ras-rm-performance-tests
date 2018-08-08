import unittest
from unittest.mock import patch, Mock, MagicMock

from requests import Response

from sdc.clients.http.authenticatedhttpclient import AuthenticatedHTTPClient


class TestAuthenticatedHTTPClient(unittest.TestCase):
    USER = 'example-service-username'
    PASSWORD = 'very-secret-service-password'

    def setUp(self):
        self.decorated_client = Mock()
        self.decorated_client.get = MagicMock()

        self.client = AuthenticatedHTTPClient(self.decorated_client,
                                              self.USER,
                                              self.PASSWORD)

    def test_get_delegates_request_to_requests_library(self):
        requests_response = Response()
        self.decorated_client.get.return_value = requests_response

        response = self.client.get(url='http://example.com',
                                   json={'ok': 'true'})

        self.decorated_client.get.assert_called_with(
            url='http://example.com',
            json={'ok': 'true'},
            auth=(self.USER, self.PASSWORD))
        self.assertEqual(requests_response, response)

    def test_post_delegates_request_to_requests_library(self):
        requests_response = Response()
        self.decorated_client.post.return_value = requests_response

        response = self.client.post(url='http://example.com',
                                    json={'ok': 'true'})

        self.decorated_client.post.assert_called_with(
            url='http://example.com',
            json={'ok': 'true'},
            auth=(self.USER, self.PASSWORD))
        self.assertEqual(requests_response, response)

    def test_put_delegates_request_to_requests_library(self):
        requests_response = Response()
        self.decorated_client.put.return_value = requests_response

        response = self.client.put(url='http://example.com',
                                   json={'ok': 'true'})

        self.decorated_client.put.assert_called_with(
            url='http://example.com',
            json={'ok': 'true'},
            auth=(self.USER, self.PASSWORD))
        self.assertEqual(requests_response, response)
