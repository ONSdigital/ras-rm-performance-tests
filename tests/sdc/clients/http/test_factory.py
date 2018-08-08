import unittest
from unittest.mock import patch

from sdc.clients.http import factory
from sdc.clients.http.httpcodeexception import HTTPCodeException
from tests.shared.requests import Requests


class TestHTTPClientFactory(unittest.TestCase, Requests):
    BASE_URL = 'http://example.com'
    PASSWORD = 'example-pass'
    USERNAME = 'example-user'

    def setUp(self):
        self.client = factory.create(self.BASE_URL,
                                     self.USERNAME,
                                     self.PASSWORD)

    @patch('requests.get')
    def test_it_delegates_to_the_requests_library(self, get):
        self.client.get(url='http://something.com')

        get.assert_called()

    @patch('requests.get')
    def test_it_is_an_authenticated_client(self, get):
        self.client.get(url='http://something.com')

        get.assert_called_with(url='http://something.com',
                               auth=(self.USERNAME, self.PASSWORD))

    @patch('requests.get')
    def test_it_is_a_base_url_client(self, get):
        self.client.get(path='/api-endpoint')

        get.assert_called_with(url=f'{self.BASE_URL}/api-endpoint',
                               auth=(self.USERNAME, self.PASSWORD))

    @patch('requests.get')
    def test_it_is_a_status_code_checking_http_client(self, get):
        response = self.http_response(status_code=404)
        get.return_value = response

        with self.assertRaises(HTTPCodeException):
            self.client.get(url='http://something.com', expected_status=200)

    @patch('requests.get')
    def test_it_handles_errors_when_path_parameter_is_provided(self, get):
        response = self.http_response(status_code=404)
        get.return_value = response

        with self.assertRaises(HTTPCodeException):
            self.client.get(path='/endpoint', expected_status=200)
