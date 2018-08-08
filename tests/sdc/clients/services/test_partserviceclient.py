import unittest
from unittest.mock import Mock

from sdc.clients.services import partyserviceclient


class TestPartyServiceClient(unittest.TestCase):
    def setUp(self):
        self.http_client = Mock()
        self.client = partyserviceclient.PartyServiceClient(http_client=self.http_client)

    def test_register(self):
        enrolment_code = '4d7bjg7s8gq6'

        self.client.register(
            email_address='user1@example.com',
            first_name='User',
            last_name='One',
            password='Top5ecret',
            telephone='0123456789',
            enrolment_code=enrolment_code
        )

        self.http_client.post.assert_called_with(
            path='/party-api/v1/respondents',
            json={
                'emailAddress': 'user1@example.com',
                'firstName': 'User',
                'lastName': 'One',
                'password': 'Top5ecret',
                'telephone': '0123456789',
                'enrolmentCode': enrolment_code,
                'status': 'CREATED',
            },
            expected_status=200
        )
