import logging
import os

import requests

sample_url = os.getenv('SAMPLE_URL', 'http://localhost:8125')


class SampleServiceClient:
    def __init__(self, http_client):
        self.http_client = http_client

    def upload_file(self, file_handle):
        survey_type = 'B'

        response = self.http_client.post(
            path=f'/samples/{survey_type}/fileupload',
            expected_status=requests.codes.created,
            files={'file': file_handle}
        )

        return response.json()['id']

    def get_state(self, sample_id):
        response = self.http_client.get(
            path=f'/samples/samplesummary/{sample_id}',
            expected_status=requests.codes.ok,
        )

        state = response.json()['state']

        logging.debug(f'Current sample state for {sample_id}: {state}')

        return state

