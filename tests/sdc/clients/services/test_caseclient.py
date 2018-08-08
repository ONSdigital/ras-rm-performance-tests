import unittest
from unittest.mock import Mock

from requests import Response

from sdc.clients.services import CaseServiceClient


class TestCaseServiceClient(unittest.TestCase):
    def setUp(self):
        self.http_client = Mock()
        self.client = CaseServiceClient(self.http_client)

    def test_find_by_enrolment_code_makes_get_request_to_the_case_service(self):
        enrolment_code = '4d7bjg7s8gq6'

        self.client.find_by_enrolment_code(enrolment_code)

        self.http_client.get.assert_called_with(
            path='/cases/iac/4d7bjg7s8gq6',
            expected_status=200
        )

    def test_find_by_enrolment_code_returns_the_case_dict(self):
        content = b'{"x": 1}'
        response = Response()
        response._content = content
        response.encoding = 'utf-8'
        self.http_client.get.return_value = response

        case = self.client.find_by_enrolment_code('4d7bjg7s8gq6')

        self.assertEqual({'x': 1}, case)