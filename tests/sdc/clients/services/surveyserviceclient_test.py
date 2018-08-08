import json
import unittest
from unittest.mock import Mock

from sdc.clients.services import SurveyServiceClient
from tests.shared.requests import Requests


class SurveyServiceClientTest(unittest.TestCase, Requests):
    def setUp(self):
        self.http_client = Mock()
        self.surveys = SurveyServiceClient(self.http_client)

    def test_get_by_id(self):
        surveys = [{'surveyRef': '001'}, {'surveyRef': '002'}]
        response = self.http_response(200, surveys)
        self.http_client.get.return_value = response

        id = '5c52d45b-5f71-47cb-8c9f-7daa068638be'

        result = self.surveys.get_by_id(id)

        self.http_client.get.assert_called_with(path=f'/surveys/{id}',
                                                expected_status=200)
        self.assertEqual(surveys, result)