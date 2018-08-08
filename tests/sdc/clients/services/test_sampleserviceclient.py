import json
import unittest
from unittest.mock import Mock

from sdc.clients.services import SampleServiceClient
from tests.shared.requests import Requests


class TestSampleServiceClient(unittest.TestCase, Requests):
    def setUp(self):
        self.http_client = Mock()

        self.client = SampleServiceClient(http_client=self.http_client)

    def test_upload_file(self):
        file_handle = 'file-handle'
        sample_id = 'e8123bce-23a9-4ceb-8829-a858ed542ae0'
        response = self.http_response(status_code=201, body=bytes(json.dumps({"id": sample_id}), 'utf-8'))
        self.http_client.post.return_value = response

        result = self.client.upload_file(file_handle)

        self.http_client.post.assert_called_with(
            path='/samples/B/fileupload',
            expected_status=201,
            files={'file': file_handle}
        )
        self.assertEqual(sample_id, result)

    def test_get_state(self):
        sample_id = 'e8123bce-23a9-4ceb-8829-a858ed542ae0'

        response = self.http_response(status_code=200, body=b'{"state": "INIT"}')
        self.http_client.get.return_value = response

        result = self.client.get_state(sample_id)

        self.http_client.get.assert_called_with(
            path=f'/samples/samplesummary/{sample_id}',
            expected_status=200
        )
        self.assertEqual('INIT', result)
