import logging

import requests


class PartyServiceClient:
    def __init__(self, http_client):
        self.http_client = http_client

    def register(self,
                 enrolment_code,
                 email_address,
                 first_name,
                 last_name,
                 password,
                 telephone):

        logging.info(f'Registering user {email_address}')

        registration_data = {
            'emailAddress': email_address,
            'firstName': first_name,
            'lastName': last_name,
            'password': password,
            'telephone': telephone,
            'enrolmentCode': enrolment_code,
            'status': 'CREATED'
        }

        logging.debug(f'User details {registration_data}')

        self.http_client.post(
            path='/party-api/v1/respondents',
            json=registration_data,
            expected_status=requests.codes.ok
        )
