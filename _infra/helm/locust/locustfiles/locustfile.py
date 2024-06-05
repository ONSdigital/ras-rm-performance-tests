import csv
import datetime
import io
import json
import logging
import os
import random
import re
import requests
import socket
import time
from datetime import timezone, datetime
from functools import partial

from werkzeug import exceptions
from google.cloud import storage
from locust import HttpUser, TaskSet, task, events, between
from locust.runners import MasterRunner, LocalRunner


survey_short_name = 'QBS'
survey_long_name = 'Quarterly Business Survey'
survey_ref = '139'
form_type = '0001'
eq_id = '2'
period = '1806'
respondents = int(os.getenv('test_respondents'))
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()

requests_file = '/mnt/locust/' + os.getenv('requests_file')
logger.info("Retrieving JSON requests from: %s", requests_file)
with open(requests_file, encoding='utf-8') as requests_file:
    requests_json = json.load(requests_file)
    request_list = requests_json["requests"]

# Ignore these during collection exercise event processing as they are the key
# for the collection exercise and don't represent event data
ignore_columns = ['surveyRef', 'exerciseRef']
CSRF_REGEX = re.compile(r'<input id="csrf_token" name="csrf_token" type="hidden" value="(.+?)"\/?>')

# Load data for tests
def load_data():
    auth = (os.getenv('security_user_name'), os.getenv('security_user_password'))

    logger.info("Container host: %s", socket.gethostname())

    survey_id = load_survey(auth)
    load_collection_exercises(auth)
    load_collection_exercise_events(auth)
    load_and_link_collection_instrument(auth, survey_id)
    load_and_link_sample(auth)
    execute_collection_exercise(auth, survey_id)
    register_users(auth)


# Survey loading
def load_survey(auth):
    logger.info('Trying to find survey %s', survey_short_name)
    get_url = f"{os.getenv('survey')}/surveys/shortname/{survey_short_name}"
    get_response = requests.get(get_url, auth=auth)

    try:
        get_response.raise_for_status()
        get_data = get_response.json()
        logger.info("Survey successfully found at id %s", get_data['id'])
        return get_data['id']
    except requests.exceptions.HTTPError:
        logger.error("Couldn't find survey %s, status code %s, message %s", survey_short_name, get_response.status_code,
                     get_response.text)

    create_url = f"{os.getenv('survey')}/surveys"
    survey_details = {"surveyRef": survey_ref, "longName": survey_long_name, "shortName": survey_short_name,
                      "legalBasisRef": 'STA1947', "surveyType": 'Business',
                      "classifiers": [{"name": "COLLECTION_INSTRUMENT", "classifierTypes": ["FORM_TYPE"]},
                                      {"name": "COMMUNICATION_TEMPLATE", "classifierTypes": ["LEGAL_BASIS", "REGION"]}]}

    create_response = requests.post(create_url, json=survey_details, auth=auth)
    try:
        create_response.raise_for_status()
        create_data = json.loads(create_response.text)
        logger.info("Successfully created survey at id %s", create_data['id'])
        return create_data['id']
    except requests.exceptions.HTTPError:
        if create_response.status_code == 409:
            # it exists try to retrieve it again
            return load_survey(auth)
        logger.exception("failed to obtain survey id")


# Helper methods for Collection exercise/event mapping
def map_columns(column_mappings, row):
    new_row = dict()
    for key, value in row.items():
        try:
            if key and value:
                new_row[column_mappings[key] if column_mappings[key] else key] = value
        except KeyError:
            new_row[key] = value
    return new_row


def process_files(file_list, row_handler, column_mappings):
    for filename in file_list:
        with open(filename) as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                new_row = map_columns(column_mappings, row)

                if new_row:
                    row_handler(data=new_row)


def reformat_date(date):
    if len(date) == 5:
        # Looks like the dates are zero padded unless the day number is < 10 in which case the 0 is missing
        # so if we have a 5 digit date we can assume it's a date in the first 9 days of a month and prefixing
        # a zero will give us the correct value
        date = '0' + date

    try:
        raw = datetime.strptime(date, '%d%m%y')
        raw = raw.replace(tzinfo=timezone.utc)
    except ValueError:
        print("Failed to parse {}".format(date))
        raise

    time_str = raw.isoformat(timespec='milliseconds')
    return time_str


# Collection exercise loading
def load_collection_exercises(auth):
    config = json.load(open(".//collection-exercise-config.json"))
    input_files = config['inputFiles']
    column_mappings = config['columnMappings']
    url = f"{os.getenv('collection_exercise')}/collectionexercises"

    row_handler = partial(post_collection_exercise, url=url, auth=auth)

    logger.info('Posting collection exercises')
    process_files(input_files, row_handler, column_mappings)


def post_collection_exercise(data, url, auth):
    response = requests.post(url, json=data, auth=auth, verify=False)

    status_code = response.status_code
    detail_text = response.text if status_code != 201 else ''

    logger.info("%s <= %s (%s)", status_code, data, detail_text)


# Collection exercise event loading
def load_collection_exercise_events(auth):
    config = json.load(open(".//collection-exercise-event-config.json"))
    input_files = config['inputFiles']
    column_mappings = config['columnMappings']
    url = f"{os.getenv('collection_exercise')}/collectionexercises"

    row_handler = partial(process_event_row, auth=auth, url=url)

    process_files(input_files, row_handler, column_mappings)


def process_event_row(data, auth, url):
    collection_exercise = get_collection_exercise(survey_ref=data['surveyRef'], exercise_ref=data['exerciseRef'],
                                                  url=url, auth=auth)
    if collection_exercise:
        collection_exercise_id = collection_exercise['id']
        for event_tag, date in data.items():
            if event_tag not in ignore_columns:
                post_event(collection_exercise_id, event_tag, date, auth, url)


def get_collection_exercise(survey_ref, exercise_ref, url, auth):
    response = requests.get(f'{url}/{exercise_ref}/survey/{survey_ref}', auth=auth, verify=False)

    try:
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            logger.error("Error getting collection exercise ID for survey %s, exercise %s, error %s", survey_ref,
                         exercise_ref, data['error'])
        else:
            return data
    except requests.exceptions.HTTPError:
        logger.exception("Error getting collection exercise data")


def post_event(collection_exercise_id, event_tag, date, auth, url):
    data = {"tag": event_tag, "timestamp": reformat_date(date)}

    response = requests.post(f'{url}/{collection_exercise_id}/events', json=data, auth=auth, verify=False)

    status_code = response.status_code
    detail_text = response.text if status_code != 201 else ''

    logger.info("%s <= %s (%s)", status_code, data, detail_text)


# Collection instrument loading
def load_and_link_collection_instrument(auth, survey_id):
    logger.info('Uploading eQ collection instrument', extra={'survey_id': survey_id, 'form_type': form_type})
    post_url = f"{os.getenv('collection_instrument')}/collection-instrument-api/1.0.2/upload"

    post_classifiers = {"form_type": form_type, "eq_id": eq_id}

    params = {"classifiers": json.dumps(post_classifiers), "survey_id": survey_id}

    post_response = requests.post(url=post_url, auth=auth, params=params)

    get_url = f"{os.getenv('collection_instrument')}/collection-instrument-api/1.0.2/collectioninstrument"
    get_classifiers = {"form_type": form_type, "SURVEY_ID": survey_id}

    get_response = requests.get(url=get_url, auth=auth, params={'searchString': json.dumps(get_classifiers)})
    get_response.raise_for_status()

    collection_exercise_url = f"{os.getenv('collection_exercise')}/collectionexercises"
    collection_exercise = get_collection_exercise(survey_ref, period, collection_exercise_url, auth)
    if collection_exercise:
        collection_exercise_id = collection_exercise['id']

        for ci in json.loads(get_response.text):
            logger.info('Linking collection instrument %s to exercise %s', ci['id'], period)
            link_url = f"{os.getenv('collection_instrument')}/collection-instrument-api/1.0.2/link-exercise/{ci['id']}/{collection_exercise_id}"
            link_response = requests.post(url=link_url, auth=auth)
            link_response.raise_for_status()

        logger.info('Successfully linked collection instruments to exercise %s', period)
    else:
        logger.error("Error retrieving collection exercise")


# Sample generation/loading/linking
def load_and_link_sample(auth):
    logger.info('Generating and loading sample for survey %s, period %s', survey_ref, period)
    sample = generate_sample_string(size=respondents)

    sample_url = f"{os.getenv('sample_file_uploader')}/samples/fileupload"
    files = {'file': ('test_sample_file.xlxs', sample.encode('utf-8'), 'text/csv')}

    sample_response = requests.post(url=sample_url, auth=auth, files=files)

    if sample_response.status_code != 202:
        logger.error('%s << Error uploading sample file for survey %s, period %s', sample_response.status_code,
                     survey_ref, period)
        raise Exception('Failed to upload sample')

    sample_summary_id = sample_response.json()['id']
    logger.info('Successfully uploaded sample file for survey %s, period %s', survey_ref, period)

    poll_url = f"{os.getenv('sample')}/samples/samplesummary/{sample_summary_id}"
    check_and_transition_sample_summary_status_url = f"{os.getenv('sample')}/samples/samplesummary/{sample_summary_id}/check-and-transition-sample-summary-status"

    attempt = 1
    ready = False
    while attempt <= 5 and not ready:

        check_and_transition_sample_summary_status = requests.get(url=check_and_transition_sample_summary_status_url,
                                                                  auth=auth)
        logger.info("check_and_transition_sample_summary_status: %s", check_and_transition_sample_summary_status)

        logger.info('Polling to see if sample summary %s is ready to link (attempt %s)', sample_summary_id, attempt)
        sample_summary = json.loads(requests.get(poll_url, auth=auth).text)
        ready = sample_summary['state'] == 'ACTIVE'
        if not ready:
            logger.info('Not ready, current state is %s, waiting 3s', sample_summary['state'])
            attempt += 1
            time.sleep(3)

    if not ready:
        logger.error('Collection exercise %s on survey %s never went READY_FOR_REVIEW', period, survey_ref)
        raise Exception('Failed to execute collection exercise')

    data = {'sampleSummaryIds': [str(sample_summary_id)]}
    collection_exercise_url = f"{os.getenv('collection_exercise')}/collectionexercises"
    collection_exercise = get_collection_exercise(survey_ref, period, collection_exercise_url, auth)
    if collection_exercise:
        collection_exercise_id = collection_exercise['id']
        collection_exercise_response = requests.put(f'{collection_exercise_url}/link/{collection_exercise_id}',
                                                    auth=auth, json=data)
        collection_exercise_response.raise_for_status()
        logger.info('Successfully linked sample summary with collection exercise %s', period)
    else:
        logger.error("failed to link sample summary with collection exercise")


def generate_sample_string(size):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=":")
    for i in range(size):
        sample_unit_ref = '499' + format(str(i), "0>8s")
        runame3 = str(i)
        tradas3 = str(i)
        region_code = 'WW'
        row = (sample_unit_ref, 'H', '75110', '75110', '84110', '84110', '3603', '97281', '9905249178', '5', 'E',
               region_code, '07/08/2003', 'OFFICE FOR', 'NATIONAL STATISTICS', runame3, 'OFFICE FOR',
               'NATIONAL STATISTICS', tradas3, '', '', '', 'C', '', '1', form_type, 'S')
        writer.writerow(row)

    return output.getvalue()


# Collection exercise execution
def execute_collection_exercise(auth, survey_id):
    poll_url = f"{os.getenv('collection_exercise')}/collectionexercises"
    attempt = 1
    ready = False
    while attempt <= 20 and not ready:
        get_collection_exercise_state(auth)
        logger.info('Polling to see if collection exercise %s is ready to execute (attempt %s)', period, attempt)
        data = get_collection_exercise(survey_ref, period, poll_url, auth)
        if data:
            ready = data['state'] == 'READY_FOR_REVIEW'
        if not ready:
            if data:
                logger.info('Collection exercise not yet READY_FOR_REVIEW, current state is %s', data['state'])
            else:
                logger.info('Collection exercise not yet available')
            attempt += 1
            time.sleep(1)

    if not ready:
        logger.error('Collection exercise %s on survey %s never went READY_FOR_REVIEW', period, survey_ref)
        raise Exception('Failed to execute collection exercise')

    while get_collection_exercise_state(auth) == 'READY_FOR_REVIEW':
        logger.info('Executing collection exercise %s on survey %s ', period, survey_ref)
        execute_url = f"{os.getenv('collection_exercise')}/collectionexerciseexecution/{data['id']}"
        response = requests.post(execute_url, auth=auth)
        response.raise_for_status()
        logger.info('Collection exercise %s on survey %s executed', period, survey_ref)
        logger.info('Waiting for READY_FOR_LIVE...')
        time.sleep(1)

    while get_collection_exercise_state(auth) != 'LIVE':
        logger.info('Executing process-scheduled-events...')
        process_scheduled_events_url = f"{os.getenv('collection_exercise')}/cron/process-scheduled-events"
        response = requests.get(process_scheduled_events_url, auth=auth)
        response.raise_for_status()
        logger.info('Waiting for LIVE...')
        time.sleep(1)


def get_collection_exercise_state(auth):
    collection_exercise_url = f"{os.getenv('collection_exercise')}/collectionexercises"
    data = get_collection_exercise(survey_ref, period, collection_exercise_url, auth)
    logger.info('Collection Exercise State: %s', data['state'])
    return data['state']


# Register respondent accounts
def register_users(auth):
    for i in range(respondents):
        sample_unit_ref = '499' + format(str(i), "0>8s")
        email_address = sample_unit_ref + "@test.com"
        logger.info("Attempting to register user %s", email_address)

        party_ru_url = f"{os.getenv('party')}/party-api/v1/businesses/ref/{sample_unit_ref}"
        party_response = requests.get(party_ru_url, auth=auth)
        party_response.raise_for_status()
        ru_party_id = json.loads(party_response.text)['id']

        attempt = 1
        case_found = False
        while attempt <= 60 and not case_found:
            logger.info('Polling to see if case for %s is ready to register against (attempt %s)', sample_unit_ref,
                        attempt)
            case_url = f"{os.getenv('case')}/cases/partyid/{ru_party_id}"
            case_response = requests.get(case_url, auth=auth, params={"iac": "true"})
            case_response.raise_for_status()
            if case_response.status_code == 200:
                case_data = json.loads(case_response.text)[0]
                if case_data['iac'] is not None:
                    iac = case_data['iac']
                    case_found = True
                else:
                    logger.info('IAC not found, waiting 5s')
                    attempt += 1
                    time.sleep(5)
            else:
                logger.info('Not found, waiting 5s')
                attempt += 1
                time.sleep(5)

        if not case_found:
            logger.error("Case never found for %s", sample_unit_ref)
            raise Exception("Case not found")

        register_url = f"{os.getenv('party')}/party-api/v1/respondents"
        data = {'emailAddress': email_address, 'firstName': 'first_name', 'lastName': 'last_name',
                'password': os.getenv('test_respondent_password'), 'telephone': '09876543210', 'enrolmentCode': iac}
        register_response = requests.post(register_url, json=data, auth=auth)
        if register_response.status_code != 200:
            logger.error("Couldn't register user %s because %s > %s", email_address, register_response.status_code,
                         register_response.text)
            raise Exception("Failed to register user")

        # TODO: Introduce a frontstage email verification link step rather than direct activation

        respondent_id = json.loads(register_response.text)['id']
        activate_payload = {"status_change": "ACTIVE"}
        activate_url = f"{os.getenv('party')}/party-api/v1/respondents/edit-account-status/{respondent_id}"
        activate_response = requests.put(activate_url, json=activate_payload, auth=auth)
        activate_response.raise_for_status()

        logger.info("Successfully registered and activated user %s", email_address)


def data_loaded():
    auth = (os.getenv('security_user_name'), os.getenv('security_user_password'))
    url = f"{os.getenv('party')}/party-api/v1/respondents?emailAddress={'499' + format(str(0), '0>8s') + '@test.com'}"
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        logger.info("Loading data because Party check returned %s", response.status_code)
        return False
    data = json.loads(response.text)
    if data['total'] == 0:
        logger.info("Loading data because Party polled and %s records found", data['total'])
        return False
    if data['data'][0]['status'] != 'ACTIVE':
        logger.info("Loading data because %s is set to %s (will probably fail)",
                    '499' + format(str(0), '0>8s') + '@test.com', data['data'][0]['status'])
        return False
    return True


# This will only be run on Master
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("on_test_start Locust runner: %s", environment.runner)
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        load_data()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("on_test_stop Locust runner: %s", environment.runner)
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        gcs = GoogleCloudStorage()
        failures = "rasrm_failures.csv"
        stats = "rasrm_stats.csv"
        history = "rasrm_stats_history.csv"

        with open(failures) as f:
            gcs.upload(file_name=failures, file=f.read())
        with open(stats) as s:
            gcs.upload(file_name=stats, file=s.read())
        with open(history) as h:
            gcs.upload(file_name=history, file=h.read())


class Mixins:
    csrf_token = None
    auth_cookie = None

    def get(self, url: str, expected_response_text=None):
        with self.client.get(url=url, allow_redirects=False, catch_response=True) as response:
            if response.status_code != 200:
                error = f"Expected a 200 but got a {response.status_code} for url {url}"
                response.failure(error)
                self.interrupt()

            if expected_response_text and expected_response_text not in response.text:
                error = f"response text ({expected_response_text}) isn't in returned html"
                response.failure(error)
                self.interrupt()

            return response

    def post(self, url: str, data: dict = {}):
        data['csrf_token'] = self.csrf_token
        with self.client.post(url=url, data=data, allow_redirects=False, catch_response=True) as response:

            if response.status_code != 302:
                error = f"Expected a 302 but got a ({response.status_code}) for url {url} and data {data}"
                response.failure(error)
                self.interrupt()

            return response


class FrontstageTasks(TaskSet, Mixins):

    def on_start(self):
        self.sign_in()

    def sign_in(self):
        response = self.get(url="/sign-in", expected_response_text="Sign in")
        self.csrf_token = _capture_csrf_token(response.content.decode('utf8'))

        response = self.post("/sign-in", data=_generate_random_respondent())
        self.auth_cookie = response.cookies['authorization']

    @task
    def perform_requests(self):
        for request in request_list:
            request_url = request['url']

            if request["method"] == "GET":
                expected_response_text = request['expected_response_text']
                self.get(request_url, expected_response_text)

            elif request["method"] == "POST":
                response_data = request['data']
                self.post(request_url, response_data)

            else:
                raise exceptions.MethodNotAllowed(
                    valid_methods={"GET", "POST"},
                    description=f"Invalid request method {request['method']} for request to: {request_url}"
                )

class FrontstageLocust(HttpUser):
    tasks = {FrontstageTasks}
    wait_time = between(5, 15)


class GoogleCloudStorage:

    def __init__(self):
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.client = storage.Client(project=self.project_id)
        self.bucket = self.client.bucket(self.bucket_name)

    def upload(self, file_name, file):
        path = datetime.utcnow().strftime("%y-%m-%d-%H-%M") + "/" + file_name
        blob = self.bucket.blob(path)
        blob.upload_from_string(data=file, content_type='application/csv')


def _capture_csrf_token(html):
    match = CSRF_REGEX.search(html)
    if match:
        return match.group(1)


def _generate_random_respondent():
    respondent_email = f"499{random.randint(0, respondents-1):08}@test.com"
    return {"username": respondent_email, "password": os.getenv("test_respondent_password")}
