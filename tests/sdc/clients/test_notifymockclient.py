import json
import unittest
from unittest.mock import Mock

from sdc.clients.notifymockclient import NotifyMockClient
from tests.shared.requests import Requests


class TestNotifyMockClient(unittest.TestCase, Requests):
    def setUp(self):
        self.http_client = Mock()
        self.client = NotifyMockClient(self.http_client)

    def test_get_emails_for_makes_a_request_to_the_mock(self):
        self.client.get_emails_for('tom@example.com')

        self.http_client.get.assert_called_with(
            path='/inbox/emails/tom%40example.com'
        )

    def test_it_returns_a_list_found_emails(self):
        messages = [
            {'message': 'one'},
            {'message': 'two'},
        ]

        response = self.http_response(200, json.dumps(messages))
        self.http_client.get.return_value = response

        result = self.client.get_emails_for('tom@example.com')

        self.assertEqual(messages, result)