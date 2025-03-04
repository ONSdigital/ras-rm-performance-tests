import datetime
import os
import io
import json
import requests
import time
import logging
import csv
import random
import re

from datetime import timezone, datetime, timedelta
from locust import HttpUser, SequentialTaskSet, task, events, between
from google.cloud import storage
from functools import partial

survey_short_name = 'QBS'
survey_long_name = 'Quarterly Business Survey'
survey_ref = '139'
form_type = '0001'
eq_id = '2'
period = '1806'
respondents = int(os.getenv('test_respondents'))
logger = logging.getLogger()

# Ignore these during collection exercise event processing as they are the key
# for the collection exercise and don't represent event data
ignore_columns = ['surveyRef', 'exerciseRef']


# Load data for tests
def load_data():
    auth = (os.getenv('security_user_name'), os.getenv('security_user_password'))

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

    logger.info(f"Response {get_response.text}")
    try:
        get_response.raise_for_status()
        get_data = get_response.json()
        logger.info("Survey successfully found at id %s", get_data['id'])
        return get_data['id']
    except requests.exceptions.HTTPError:
        logger.error("Couldn't find survey %s, status code %s, message %s", survey_short_name, get_response.status_code, get_response.text)

    create_url = f"{os.getenv('survey')}/surveys"
    survey_details = {
        "surveyRef": survey_ref,
        "longName": survey_long_name,
        "shortName": survey_short_name,
        "legalBasisRef": 'STA1947',
        "surveyType": 'Business',
        "classifiers": [
            {"name": "COLLECTION_INSTRUMENT", "classifierTypes": ["FORM_TYPE"]},
            {"name": "COMMUNICATION_TEMPLATE", "classifierTypes": ["LEGAL_BASIS", "REGION"]}
        ]
    }

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
    config = json.load(open("/mnt/locust/collection-exercise-config.json"))
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
    config = json.load(open("/mnt/locust/collection-exercise-event-config.json"))
    input_files = config['inputFiles']
    column_mappings = config['columnMappings']
    url = f"{os.getenv('collection_exercise')}/collectionexercises"

    row_handler = partial(process_event_row, auth=auth, url=url)

    process_files(input_files, row_handler, column_mappings)


def process_event_row(data, auth, url):
    collection_exercise = get_collection_exercise(survey_ref=data['surveyRef'], exercise_ref=data['exerciseRef'], url=url, auth=auth)
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

    post_classifiers = {
        "form_type": form_type,
        "eq_id": eq_id
    }

    params = {
        "classifiers": json.dumps(post_classifiers),
        "survey_id": survey_id
    }

    post_response = requests.post(url=post_url, auth=auth, params=params)

    get_url = f"{os.getenv('collection_instrument')}/collection-instrument-api/1.0.2/collectioninstrument"
    get_classifiers = {
        "form_type": form_type,
        "SURVEY_ID": survey_id
    }

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
        logger.error('%s << Error uploading sample file for survey %s, period %s', sample_response.status_code, survey_ref, period)
        raise Exception('Failed to upload sample')

    sample_summary_id = sample_response.json()['id']
    logger.info('Successfully uploaded sample file for survey %s, period %s', survey_ref, period)

    poll_url = f"{os.getenv('sample')}/samples/samplesummary/{sample_summary_id}"
    check_and_transition_sample_summary_status_url = f"{os.getenv('sample')}/samples/samplesummary/{sample_summary_id}/check-and-transition-sample-summary-status"

    attempt = 1
    ready = False
    while attempt <= 5 and not ready:

        check_and_transition_sample_summary_status = requests.get(url=check_and_transition_sample_summary_status_url, auth=auth)
        logger.info(check_and_transition_sample_summary_status)

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
        collection_exercise_response = requests.put(f'{collection_exercise_url}/link/{collection_exercise_id}', auth=auth, json=data)
        collection_exercise_response.raise_for_status()
        logger.info('Successfully linked sample summary with collection exercise %s', period)
    else:
        logger.error("failed to link sample summary with collection exercise")


def generate_sample_string(size):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=":")
    for i in range(size):
        sample_unit_ref='499'+format(str(i), "0>8s")
        runame3=str(i)
        tradas3=str(i)
        region_code='WW'
        row=(   sample_unit_ref,
                'H',
                '75110',
                '75110',
                '84110',
                '84110',
                '3603',
                '97281',
                '9905249178',
                '5',
                'E',
                region_code,
                '07/08/2003',
                'OFFICE FOR',
                'NATIONAL STATISTICS',
                runame3,
                'OFFICE FOR',
                'NATIONAL STATISTICS',
                tradas3,
                '',
                '',
                '',
                'C',
                '',
                '1',
                form_type,
                'S')
        writer.writerow(row)

    return output.getvalue()


# Collection exercise execution
def execute_collection_exercise(auth, survey_id):
    poll_url = f"{os.getenv('collection_exercise')}/collectionexercises"
    attempt = 1
    ready = False
    while attempt <= 20 and not ready:
        logger.info('Polling to see if collection exercise %s is ready to execute (attempt %s)', period, attempt)
        data = get_collection_exercise(survey_ref, period, poll_url, auth)
        if data:
            ready = data['state'] == 'READY_FOR_REVIEW'
        if not ready:
            if data:
                logger.info('Not ready, current state is %s, waiting 3s', data['state'])
            else:
                logger.info('Not ready waiting 3s')
            attempt += 1
            time.sleep(3)

    if not ready:
        logger.error('Collection exercise %s on survey %s never went READY_FOR_REVIEW', period, survey_ref)
        raise Exception('Failed to execute collection exercise')

    logger.info('Executing collection exercise %s on survey %s ', period, survey_ref)
    execute_url = f"{os.getenv('collection_exercise')}/collectionexerciseexecution/{data['id']}"
    response = requests.post(execute_url, auth=auth)
    response.raise_for_status()
    logger.info('Collection exerise %s on survey %s executed', period, survey_ref)
    # TODO: need a loop to check an endpoint to see if this is executed rather than a sleep
    time.sleep(10)

    process_scheduled_events_url = f"{os.getenv('collection_exercise')}/cron/process-scheduled-events"
    response = requests.get(process_scheduled_events_url, auth=auth)
    logger.info(response)
    response.raise_for_status()
    # TODO: need a loop to check an endpoint to see if this is executed rather than a sleep
    time.sleep(10)

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
            logger.info('Polling to see if case for %s is ready to register against (attempt %s)', sample_unit_ref, attempt)
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
        data = {
            'emailAddress': email_address,
            'firstName': 'first_name',
            'lastName': 'last_name',
            'password': os.getenv('test_respondent_password'),
            'telephone': '09876543210',
            'enrolmentCode': iac
        }
        register_response = requests.post(register_url, json=data, auth=auth)
        if register_response.status_code != 200:
            logger.error("Couldn't register user %s because %s > %s", email_address, register_response.status_code, register_response.text)
            raise Exception("Failed to register user")

        respondent_id = json.loads(register_response.text)['id']
        activate_payload = {"status_change": "ACTIVE"}
        activate_url = f"{os.getenv('party')}/party-api/v1/respondents/edit-account-status/{respondent_id}"
        activate_response = requests.put(activate_url, json=activate_payload, auth=auth)
        activate_response.raise_for_status()

        logger.info("Successfully registered and activated user %s", email_address)


def data_loaded():
    auth = (os.getenv('security_user_name'), os.getenv('security_user_password'))
    url = f"{os.getenv('party')}/party-api/v1/respondents?emailAddress={'499'+format(str(0), '0>8s')+'@test.com'}"
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        logger.info("Loading data because Party check returned %s", response.status_code)
        return False
    data = json.loads(response.text)
    if data['total'] == 0:
        logger.info("Loading data because Party polled and %s records found", data['total'])
        return False
    if data['data'][0]['status'] != 'ACTIVE':
        logger.info("Loading data because %s is set to %s (will probably fail)", '499'+format(str(0), '0>8s')+'@test.com', data['data'][0]['status'])
        return False
    return True


# This will only be run on Master
@events.test_start.add_listener
def on_test_start(**kwargs):
    load_data()


@events.test_stop.add_listener
def on_test_stop(**kwargs):
    gcs = GoogleCloudStorage()
    failures = "rasrm_failures.csv"
    stats = "rasrm_stats.csv"
    history = " rasrm_stats_history.csv"

    with open(failures) as f:
        gcs.upload(file_name=failures, file=f.read())
    with open(stats) as s:
        gcs.upload(file_name=stats, file=s.read())
    with open(history) as h:
        gcs.upload(file_name=history, file=h.read())


class FrontstageTasks(SequentialTaskSet):
    create_message_link = None
    view_message_thread_link = None

    def on_start(self):
        self.login()

    def login(self):
        sample_unit_ref = '499' + format(str(random.randint(0, respondents)), "0>8s")
        data = {'username': sample_unit_ref + "@test.com", 'password': os.getenv('test_respondent_password')}
        response = self.client.post("/sign-in/?next=", data=data, catch_response=True, allow_redirects=False)
        self.auth_cookie = response.cookies['authorization']

    @task(1)
    def surveys_todo(self):
        with self.client.get("/surveys/todo", cookies={"authorization": self.auth_cookie}, catch_response=True) as response:
            if 'Sign in' in response.text:
                response.failure("Not logged in")
            if 'You have no surveys to complete' in response.text:
                response.failure("No surveys in survey list")
            if 'Quarterly Business Survey' not in response.text:
                response.failure("QBS survey not found in list")
            # TODO: The secure message journey has changed significantly and is now under 'help with this survey'
            # self.create_message_link = re.search('\/secure-message\/create-message\/[^\"]*', response.text).group(0)

            # GET http://localhost:8082/surveys/surveys-help?survey_ref=139&ru_ref=49900000000
            # POST http://localhost:8082/surveys/help?short_name=QBS&amp;business_id=43e4b914-1db8-4267-ab7c-b223e7190d65&amp;survey_ref=139&amp;ru_ref=49900000000
            #         name="csrf_token" value="ImM5ZDE4MzNiNTVhMDAwZDFmYWU5MWRlOGJkNWVhNzhmMzBiZjdhZDci.ZPz3rg.MsZXp47XLJlAN1n0DCjdQq9LVcw"
            #         name="option" value="something-else"
    @task(2)
    def create_secure_message_page(self):
        with self.client.get(self.create_message_link, cookies={"authorization": self.auth_cookie}, catch_response=True) as response:
            if 'To: ONS Business Surveys team' not in response.text:
                response.failure("Couldn't find To: when sending Secure Message")
            if 'id="send-message-btn"' not in response.text:
                response.failure("Couldn't find Secure Message Send button")

    @task(3)
    def create_secure_message(self):
        data = {
            "subject": "Performance Test",
            "body": "This is a performance test",
            "send": "send"
        }

        with self.client.post(self.create_message_link, cookies={"authorization": self.auth_cookie}, data=data, catch_response=True) as response:
            d = datetime.today()
            if 'first_name last_name' not in response.text:
                response.failure("Not returned to the messages tab with a thread with our name on it")
            if not (f'{d.strftime(":%M")}' in response.text or f'{(d - timedelta(minutes=1)).strftime(":%M")}' in response.text):
                response.failure("No new messages sent in the last 60 seconds")
            self.view_message_thread_link = re.search('\/secure-message\/threads\/[^\"]*#latest-message', response.text).group(0)

    @task(4)
    def view_message_thread(self):
        with self.client.get(self.view_message_thread_link, cookies={"authorization": self.auth_cookie}, catch_response=True) as response:
            if 'This is a performance test' not in response.text:
                response.failure("Can't find message body in message thread")

    @task(5)
    def reply_to_message_thread(self):
        reply_link = self.view_message_thread_link.split('#latest-message')[0]
        data = {
            "body": "Reply to a performance test",
            "send": "send"
        }

        with self.client.post(reply_link, cookies={"authorization": self.auth_cookie}, data=data, catch_response=True) as response:
            d = datetime.today()
            if "Reply to a performance test" not in response.text:
                response.failure("Message not replied to")
            if not (f'{d.strftime(":%M")}' in response.text or f'{(d - timedelta(minutes=1)).strftime(":%M")}' in response.text):
                response.failure("No new messages sent in the last 60 seconds")

    @task(6)
    def get_survey_history(self):
        with self.client.get("/surveys/history", cookies={"authorization": self.auth_cookie}, catch_response=True) as response:
            if "Period covered" not in response.text:
                response.failure("Couldn't load survey history page")
            if "No items to show" not in response.text:
                response.failure("User has survey history somehow")


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
        blob.upload_from_string(
            data=file,
            content_type='application/csv'
        )