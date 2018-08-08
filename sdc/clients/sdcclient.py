import logging
import os

from schema import Schema, Regex, And

from sdc.clients import http
from sdc.clients.enrolmentcodes import EnrolmentCodes
from sdc.clients.http import factory
from sdc.clients.notifymockclient import NotifyMockClient
from sdc.clients.services import CaseServiceClient, \
    CollectionExerciseServiceClient, CollectionInstrumentServiceClient, \
    PartyServiceClient, SampleServiceClient, SurveyServiceClient
from sdc.clients.sftpclient import SFTPClient
from sdc.clients.users import Users

URL_SCHEMA = Regex(r'^https?://')
NON_EMPTY_STRING_SCHEMA = And(str, len)

CONFIG_SCHEMA = Schema({
    'service_username': NON_EMPTY_STRING_SCHEMA,
    'service_password': NON_EMPTY_STRING_SCHEMA,
    'case_url': URL_SCHEMA,
    'iac_url': URL_SCHEMA,
    'notify_mock_url': URL_SCHEMA,
    'party_url': URL_SCHEMA,
    'party_create_respondent_endpoint': NON_EMPTY_STRING_SCHEMA,
    'collection_exercise_url': URL_SCHEMA,
    'collection_instrument_url': URL_SCHEMA,
    'sample_url': URL_SCHEMA,
    'survey_url': URL_SCHEMA,
    'sftp_host': NON_EMPTY_STRING_SCHEMA,
    'sftp_port': int,
    'sftp_base_dir': NON_EMPTY_STRING_SCHEMA,
    'actionexporter_sftp_username': NON_EMPTY_STRING_SCHEMA,
    'actionexporter_sftp_password': NON_EMPTY_STRING_SCHEMA,
})


class SDCClient:
    def __init__(self, config):
        self.config = CONFIG_SCHEMA.validate(config)
        self.action_exporter_sftp_client = None

    @property
    def collection_exercises(self):
        http_client = self._create_http_client(self.config['collection_exercise_url'])

        return CollectionExerciseServiceClient(http_client)

    @property
    def enrolment_codes(self):
        if not self.action_exporter_sftp_client:
            self.action_exporter_sftp_client = SFTPClient(
                host=self.config['sftp_host'],
                username=self.config['actionexporter_sftp_username'],
                password=self.config['actionexporter_sftp_password'],
                port=self.config['sftp_port'])

        return EnrolmentCodes(sftp_client=self.action_exporter_sftp_client,
                              base_dir=self.config['sftp_base_dir'])

    @property
    def samples(self):
        http_client = self._create_http_client(self.config['sample_url'])

        return SampleServiceClient(http_client=http_client)

    @property
    def collection_instruments(self):
        http_client = self._create_http_client(self.config['collection_instrument_url'])
        return CollectionInstrumentServiceClient(http_client=http_client)

    @property
    def cases(self):
        http_client = http.factory.create(
            base_url=self.config['case_url'],
            username=self.config['service_username'],
            password=self.config['service_password'])

        return CaseServiceClient(http_client=http_client)

    @property
    def surveys(self):
        return SurveyServiceClient(self._create_http_client(self.config['survey_url']))

    @property
    def users(self):
        http_client = self._create_http_client(self.config['party_url'])
        user_client = PartyServiceClient(http_client=http_client)
        notify_client = self.messages

        return Users(user_client=user_client, notify_client=notify_client)

    @property
    def messages(self):
        http_client = self._create_http_client(self.config['notify_mock_url'])
        return NotifyMockClient(http_client=http_client)

    def _create_http_client(self, url):
        return http.factory.create(
            base_url=url,
            username=self.config['service_username'],
            password=self.config['service_password'])


def config_from_env():
    config = CONFIG_SCHEMA.validate({
        'service_username': os.getenv('COLLECTION_INSTRUMENT_USERNAME',
                                      'admin'),
        'service_password': os.getenv('COLLECTION_INSTRUMENT_PASSWORD',
                                      'secret'),
        'iac_url': os.getenv('IAC_URL', 'http://localhost:8121'),
        'case_url': os.getenv('CASE_URL', 'http://localhost:8171'),
        'party_url': os.getenv('PARTY_URL', 'http://localhost:8081'),
        'party_create_respondent_endpoint': os.getenv(
            'PARTY_CREATE_RESPONDENT_ENDPOINT', '/party-api/v1/respondents'),
        'notify_mock_url': os.getenv('NOTIFY_MOCK_URL'),
        'collection_exercise_url': os.getenv('COLLECTION_EXERCISE_URL',
                                             'http://localhost:8145'),
        'collection_instrument_url':
            os.getenv('COLLECTION_INSTRUMENT_URL', 'http://localhost:8002'),
        'sample_url': os.getenv('SAMPLE_URL', 'http://localhost:8125'),
        'survey_url': os.getenv('SURVEY_URL', 'http://localhost:8080'),
        'sftp_host': os.getenv('SFTP_HOST'),
        'sftp_port': int(os.getenv('SFTP_PORT', '22')),
        'sftp_base_dir': os.getenv('SFTP_BASE_DIR', 'BSD/'),
        'actionexporter_sftp_username':
            os.getenv('ACTION_EXPORTER_SFTP_USERNAME'),
        'actionexporter_sftp_password':
            os.getenv('ACTION_EXPORTER_SFTP_PASSWORD'),
    })

    logging.debug(f'Using config: {repr(config)}')

    return config
