import json
import unittest
from datetime import datetime, timedelta
from io import StringIO

import httpretty
import pytest

from sdc.clients import SDCClient
from sdc.clients.users import NoVerificationEmailFound


@pytest.mark.usefixtures('sftpserver')
class TestSDCClientIntegration(unittest.TestCase):
    def setUp(self):
        self.client = SDCClient(self._config())

    @staticmethod
    def _config(override={}):
        config = {
            'service_username': 'example-service-username',
            'service_password': 'example-service-password',
            'case_url': 'http://case.services.com',
            'iac_url': 'http://iac.services.com',
            'collection_exercise_url': 'http://localhost:8145',
            'notify_mock_url': 'http://notify-mock.services.com',
            'collection_instrument_url': 'http://ci.services.com',
            'sample_url': 'http://sample.services.com',
            'survey_url': 'http://survey.services.com',
            'sftp_host': 'sftp.example.com',
            'sftp_port': 22,
            'sftp_base_dir': 'sftp_base',
            'actionexporter_sftp_password': 'sftp-password',
            'actionexporter_sftp_username': 'sftp-username',
            'party_url': 'http://party.services.com',
            'party_create_respondent_endpoint': '/party-api/v1/respondents',
        }

        config.update(override)

        return config

    @httpretty.activate
    def test_collection_exercises(self):
        exercise_id = '1429b8df-d657-44bb-a59a-7a298d4ed08f'

        collection_exercise = {
            'caseTypes': [
                {
                    'actionPlanId': 'BUSINESS_CASE_ACTION_PLAN_ID',
                    'sampleUnitType': 'B'
                }
            ]
        }
        httpretty.register_uri(
            httpretty.GET,
            f'http://localhost:8145/collectionexercises/{exercise_id}',
            body=json.dumps(collection_exercise),
            status=200)

        result = self.client.collection_exercises.get_by_id(exercise_id)

        self.assertEqual(collection_exercise, result)

    def test_enrolment_codes(self):
        files = {
            'sftp_base': {
                'BSNOT_11_201806_11062018_999.csv':
                    '49900000008:enrolment-code:NOTSTARTED:null:null:null:null:null:FE\n'}}

        with self.sftpserver.serve_content(files):
            client = SDCClient(self._config({
                'sftp_host': self.sftpserver.host,
                'sftp_port': self.sftpserver.port,
                'actionexporter_sftp_username': 'the-username',
                'actionexporter_sftp_password': 'the-password',
            }))

            codes = client.enrolment_codes.download(survey_ref='11',
                                                    period='201806',
                                                    generated_date='11062018',
                                                    expected_codes=1)

            self.assertEquals(['enrolment-code'], codes)

    @httpretty.activate
    def test_samples(self):
        sample_id = '1429b8df-d657-44bb-a59a-7a298d4ed08f'

        httpretty.register_uri(
            httpretty.POST,
            'http://sample.services.com/samples/B/fileupload',
            body=json.dumps({'id': sample_id}),
            status=201)

        file = StringIO('file contents')
        result = self.client.samples.upload_file(file)

        self.assertEqual(sample_id, result)

    @httpretty.activate
    def test_collection_instruments(self):
        survey_id = '6ee65e4d-ecc0-4144-936c-d87c0775b383'
        survey_classifiers = {'classifier': 'xxx'}

        httpretty.register_uri(
            httpretty.POST,
            'http://ci.services.com/collection-instrument-api/1.0.2/upload',
            body='',
            status=200)

        self.client.collection_instruments.upload(
            survey_id=survey_id,
            survey_classifiers=survey_classifiers)

    @httpretty.activate
    def test_cases_property(self):
        enrolment_code = 'p2js5r9m2gbz'

        httpretty.register_uri(
            httpretty.GET,
            f'http://case.services.com/cases/iac/{enrolment_code}',
            body=json.dumps({'id': 'case-id'}),
            status=200)

        case = self.client.cases.find_by_enrolment_code(enrolment_code)
        self.assertEqual({'id': 'case-id'}, case )

    @httpretty.activate
    def test_users_register(self):
        enrolment_code = 'p2js5r9m2gbz'

        httpretty.register_uri(
            httpretty.POST,
            'http://party.services.com/party-api/v1/respondents',
            body=json.dumps({}),
            status=200)

        self.client.users.register(
            email_address='user1@example.com',
            first_name='User',
            last_name='One',
            password='Top5ecret',
            telephone='0123456789',
            enrolment_code=enrolment_code)

    @httpretty.activate
    def test_users_activate(self):
        httpretty.register_uri(
            httpretty.GET,
            'http://notify-mock.services.com/inbox/emails/user1%40example.com',
            body=json.dumps([]),
            status=200)

        with self.assertRaises(NoVerificationEmailFound):
            self.client.users.verify('user1@example.com')

    @httpretty.activate
    def test_messages(self):
        messages = [
            {'message': 'first-message'},
            {'message': 'second-message'}]

        httpretty.register_uri(
            httpretty.GET,
            'http://notify-mock.services.com/inbox/emails/matt%40example.com',
            body=json.dumps(messages),
            status=200)

        response = self.client.messages.get_emails_for('matt@example.com')

        self.assertEqual(messages, response)

    @httpretty.activate
    def test_surveys(self):
        survey_id = '4995ecb5-cda1-4b91-b89f-3f95e2e7922e'
        survey = {'surveyRef': '001'}

        httpretty.register_uri(
            httpretty.GET,
            f'http://survey.services.com/surveys/{survey_id}',
            body=json.dumps(survey),
            status=200)

        response = self.client.surveys.get_by_id(survey_id)

        self.assertEqual(survey, response)
