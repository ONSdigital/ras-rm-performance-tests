import unittest
from unittest.mock import Mock, MagicMock

from requests import Response

from sdc.clients.http.baseurlhttpclient import BaseURLHTTPClient


class TestBaseURLHTTPClient(unittest.TestCase):
    BASE_URL = 'http://example.com/api'
    GET_RESPONSE = Response()
    POST_RESPONSE = Response()
    PUT_RESPONSE = Response()

    def setUp(self):
        self.decorated_client = Mock()
        self.decorated_client.get = MagicMock(return_value=self.GET_RESPONSE)
        self.decorated_client.post = MagicMock(return_value=self.POST_RESPONSE)
        self.decorated_client.put = MagicMock(return_value=self.PUT_RESPONSE)

        self.client = BaseURLHTTPClient(self.decorated_client, self.BASE_URL)

    def test_get_delegates_with_full_url(self):
        self.client.get(path='/endpoint')

        self.decorated_client.get.assert_called_with(
            url=f'{self.BASE_URL}/endpoint')

    def test_get_returns_the_response(self):
        self.assertEqual(self.GET_RESPONSE, self.client.get(path='/endpoint'))

    def test_get_delegates_all_arguments(self):
        self.client.get(path='/endpoint', extra=True)

        self.decorated_client.get.assert_called_with(
            url=f'{self.BASE_URL}/endpoint', extra=True)

    def test_get_with_url_argument(self):
        self.client.get(url='http://example.com/v2/endpoint')

        self.decorated_client.get.assert_called_with(
            url='http://example.com/v2/endpoint')

    def test_get_raises_if_url_and_path_are_provided(self):
        with self.assertRaises(Exception):
            self.client.get(url='http://example.com', path='/v2/endpoint')

    def test_post_delegates_with_full_url(self):
        self.client.post(path='/endpoint')

        self.decorated_client.post.assert_called_with(
            url=f'{self.BASE_URL}/endpoint')

    def test_post_returns_the_response(self):
        self.assertEqual(self.POST_RESPONSE, self.client.post(path='/endpoint'))

    def test_post_delegates_all_arguments(self):
        self.client.post(path='/endpoint', extra=True)

        self.decorated_client.post.assert_called_with(
            url=f'{self.BASE_URL}/endpoint', extra=True)

    def test_post_with_url_argument(self):
        self.client.post(url='http://example.com/v2/endpoint')

        self.decorated_client.post.assert_called_with(
            url='http://example.com/v2/endpoint')

    def test_post_raises_if_url_and_path_are_provided(self):
        with self.assertRaises(Exception):
            self.client.post(url='http://example.com', path='/v2/endpoint')

    def test_put_delegates_with_full_url(self):
        self.client.put(path='/endpoint')

        self.decorated_client.put.assert_called_with(
            url=f'{self.BASE_URL}/endpoint')

    def test_put_returns_the_response(self):
        self.assertEqual(self.PUT_RESPONSE, self.client.put(path='/endpoint'))

    def test_put_delegates_all_arguments(self):
        self.client.put(path='/endpoint', extra=True)

        self.decorated_client.put.assert_called_with(
            url=f'{self.BASE_URL}/endpoint', extra=True)

    def test_put_with_url_argument(self):
        self.client.put(url='http://example.com/v2/endpoint')

        self.decorated_client.put.assert_called_with(
            url='http://example.com/v2/endpoint')

    def test_put_raises_if_url_and_path_are_provided(self):
        with self.assertRaises(Exception):
            self.client.put(url='http://example.com', path='/v2/endpoint')
