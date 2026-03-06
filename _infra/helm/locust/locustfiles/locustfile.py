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
from bs4 import BeautifulSoup

from werkzeug import exceptions
from google.cloud import storage
from locust import HttpUser, TaskSet, task, events
from locust.runners import MasterRunner, LocalRunner

from gevent import spawn, sleep



logging.basicConfig(level=logging.DEBUG, format="%(message)s")
logger = logging.getLogger()

FORM_TYPE = "0001"
EQ_ID = "2"
PERIOD = "1806"
RESPONDENTS = int(os.getenv("test_respondents"))
REQUEST_FILE = '/mnt/locust/' + os.getenv('requests_file')
r = random.Random()

logger.info("Retrieving JSON requests from: %s", REQUEST_FILE)
with open(REQUEST_FILE, encoding="utf-8") as REQUEST_FILE:
    REQUEST_LIST = json.load(REQUEST_FILE)["requests"]

# Ignore these during collection exercise event processing as they are the key
# for the collection exercise and don't represent event data
IGNORE_COLUMNS = ["surveyRef", "exerciseRef"]
CSRF_REGEX = re.compile(r'<input id="csrf_token" name="csrf_token" type="hidden" value="(.+?)"\/?>')
# USER_WAIT_TIME_WAIT_TIME is between GET and POST requests
USER_WAIT_TIME_MIN_SECONDS = int(os.getenv("user_wait_time_min_seconds", 1))
USER_WAIT_TIME_MAX_SECONDS = int(os.getenv("user_wait_time_max_seconds", 1))
AUTH = (os.getenv("security_user_name"), os.getenv("security_user_password"))
CE_URL = f"{os.getenv('collection_exercise')}/collectionexercises"

SURVEY_DETAILS = [
    {
        "survey_name": "QBS",
        "ce_config": "/mnt/locust/qbs_collection-exercise-config.json",
        "ce_events": "/mnt/locust/qbs_collection-exercise-event-config.json",
        "type": "EQ",
        "survey_ref": "139"
    },
    {
        "survey_name": "ASHE",
        "ce_config": "/mnt/locust/ashe_collection-exercise-config.json",
        "ce_events": "/mnt/locust/ashe_collection-exercise-event-config.json",
        "type": "SEFT",
        "survey_ref": "141",
        "ci_file_location": "/mnt/locust/065_201803_0001.xlsx"
    },
]


# Load data for tests
def load_data():
    logger.info(f"Container host: {socket.gethostname()}")

    for survey in SURVEY_DETAILS:
        survey_id = get_survey_id(survey["survey_name"])
        load_collection_exercises(survey["ce_config"])
        load_collection_exercise_events(survey["ce_events"])
        load_and_link_collection_instrument(survey_id, survey["type"], survey["survey_ref"],
                                            survey.get("ci_file_location"))
        load_and_link_sample(survey["survey_ref"])
        execute_collection_exercise(survey["survey_ref"])
    register_users()


def get_survey_id(survey_name):
    survey_details = requests.get(f"{os.getenv('survey')}/surveys/shortname/{survey_name}", auth=AUTH)
    try:
        survey_details.raise_for_status()
        survey_data = survey_details.json()
        logger.info("Survey successfully found at id %s", survey_data["id"])
        return survey_data["id"]

    except requests.exceptions.HTTPError:
        logger.error(
            f"Couldn't find survey: {survey_name}, "
            f"status code: {survey_details.status_code}, "
            f"message {survey_details.text}"
        )


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
        date = "0" + date

    try:
        raw = datetime.strptime(date, "%d%m%y")
        raw = raw.replace(tzinfo=timezone.utc)
    except ValueError:
        print("Failed to parse {}".format(date))
        raise

    time_str = raw.isoformat(timespec="milliseconds")
    return time_str


# Collection exercise loading
def load_collection_exercises(ce_config: str):
    config = json.load(open(ce_config))
    input_files = config["inputFiles"]
    column_mappings = config["columnMappings"]
    row_handler = partial(post_collection_exercise)
    logger.info("Posting collection exercises")
    process_files(input_files, row_handler, column_mappings)


def post_collection_exercise(data):
    response = requests.post(CE_URL, json=data, auth=AUTH, verify=False)
    status_code = response.status_code
    detail_text = response.text if status_code != 201 else ""
    logger.info("%s <= %s (%s)", status_code, data, detail_text)


# Collection exercise event loading
def load_collection_exercise_events(collection_exercise_event_config):
    config = json.load(open(collection_exercise_event_config))
    input_files = config["inputFiles"]
    column_mappings = config["columnMappings"]
    row_handler = partial(process_event_row)
    process_files(input_files, row_handler, column_mappings)


def process_event_row(data):
    collection_exercise = get_collection_exercise(survey_ref=data["surveyRef"], exercise_ref=data["exerciseRef"])
    if collection_exercise:
        collection_exercise_id = collection_exercise["id"]
        for event_tag, date in data.items():
            if event_tag not in IGNORE_COLUMNS:
                post_event(collection_exercise_id, event_tag, date)


def get_collection_exercise(survey_ref, exercise_ref):
    response = requests.get(f"{CE_URL}/{exercise_ref}/survey/{survey_ref}", verify=False)
    try:
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            logger.error(
                "Error getting collection exercise ID for survey %s, exercise %s, error %s",
                survey_ref,
                exercise_ref,
                data["error"],
            )
        else:
            return data
    except requests.exceptions.HTTPError:
        logger.exception("Error getting collection exercise data")


def post_event(collection_exercise_id, event_tag, date):
    data = {"tag": event_tag, "timestamp": reformat_date(date)}
    response = requests.post(f"{CE_URL}/{collection_exercise_id}/events", json=data, auth=AUTH, verify=False)
    status_code = response.status_code
    detail_text = response.text if status_code != 201 else ""

    logger.info("%s <= %s (%s)", status_code, data, detail_text)


# Collection instrument loading
def load_and_link_collection_instrument(survey_id, survey_type, survey_ref, ci_file_location):
    logger.info("Uploading collection instrument", extra={"survey_id": survey_id, "form_type": FORM_TYPE})
    collection_exercise = get_collection_exercise(survey_ref, PERIOD)
    if not collection_exercise:
        raise Exception("No collection exercise")

    collection_exercise_id = collection_exercise["id"]
    post_classifiers = {"form_type": FORM_TYPE}

    if survey_type == "SEFT":
        params = {"classifiers": json.dumps(post_classifiers), "survey_id": survey_id}
        post_url = (
            f"{os.getenv('collection_instrument')}/collection-instrument-api/1.0.2/upload/{collection_exercise_id}"
        )
        ci_file_stream = open(ci_file_location, "r", encoding="utf-8")
        ci_file= {"file": ("065_201803_0001.xlsx", ci_file_stream, "application/json")}
        requests.post(url=post_url, files=ci_file, params=params, auth=AUTH)

    else:
        post_classifiers["eq_id"] = EQ_ID
        params = {"classifiers": json.dumps(post_classifiers), "survey_id": survey_id}
        post_url = f"{os.getenv('collection_instrument')}/collection-instrument-api/1.0.2/upload"
        requests.post(url=post_url, auth=AUTH, params=params)

    get_url = f"{os.getenv('collection_instrument')}/collection-instrument-api/1.0.2/collectioninstrument"
    get_classifiers = {"form_type": FORM_TYPE, "SURVEY_ID": survey_id}
    get_response = requests.get(url=get_url, auth=AUTH, params={"searchString": json.dumps(get_classifiers)})
    get_response.raise_for_status()

    for ci in json.loads(get_response.text):
        logger.info("Linking collection instrument %s to exercise %s", ci["id"], PERIOD)
        link_url = f"{os.getenv('collection_instrument')}/collection-instrument-api/1.0.2/link-exercise/{ci['id']}/{collection_exercise_id}"
        link_response = requests.post(url=link_url, auth=AUTH)
        link_response.raise_for_status()

    logger.info("Successfully linked collection instruments to exercise %s", PERIOD)


# Sample generation/loading/linking
def load_and_link_sample(survey_ref):
    logger.info("Generating and loading sample for survey %s, period %s", survey_ref, PERIOD)
    sample = generate_sample_string(size=RESPONDENTS)
    sample_url = f"{os.getenv('sample_file_uploader')}/samples/fileupload"
    files = {"file": ("test_sample_file.xlxs", sample.encode("utf-8"), "text/csv")}
    sample_response = requests.post(url=sample_url, auth=AUTH, files=files)

    if sample_response.status_code != 202:
        logger.error(
            "%s << Error uploading sample file for survey %s, period %s",
            sample_response.status_code,
            survey_ref,
            PERIOD,
        )
        raise Exception("Failed to upload sample")

    sample_summary_id = sample_response.json()["id"]
    logger.info("Successfully uploaded sample file for survey %s, period %s", survey_ref, PERIOD)
    poll_url = f"{os.getenv('sample')}/samples/samplesummary/{sample_summary_id}"
    check_and_transition_sample_summary_status_url = (
        f"{os.getenv('sample')}/samples/samplesummary/{sample_summary_id}/check-and-transition-sample-summary-status"
    )

    attempt = 1
    ready = False
    while attempt <= 5 and not ready:
        check_and_transition_sample_summary_status = requests.get(
            url=check_and_transition_sample_summary_status_url, auth=AUTH
        )
        logger.info("check_and_transition_sample_summary_status: %s", check_and_transition_sample_summary_status)
        logger.info("Polling to see if sample summary %s is ready to link (attempt %s)", sample_summary_id, attempt)
        sample_summary = json.loads(requests.get(poll_url, auth=AUTH).text)
        ready = sample_summary["state"] == "ACTIVE"
        if not ready:
            logger.info("Not ready, current state is %s, waiting 3s", sample_summary["state"])
            attempt += 1
            time.sleep(3)

    if not ready:
        logger.error("Collection exercise %s on survey %s never went READY_FOR_REVIEW", PERIOD, survey_ref)
        raise Exception("Failed to execute collection exercise")

    data = {"sampleSummaryIds": [str(sample_summary_id)]}

    collection_exercise = get_collection_exercise(survey_ref, PERIOD)
    if collection_exercise:
        collection_exercise_id = collection_exercise["id"]
        collection_exercise_response = requests.put(f"{CE_URL}/link/{collection_exercise_id}", auth=AUTH, json=data)
        collection_exercise_response.raise_for_status()
        logger.info("Successfully linked sample summary with collection exercise %s", PERIOD)
    else:
        logger.error("failed to link sample summary with collection exercise")


def generate_sample_string(size):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=":")
    for i in range(size):
        sample_unit_ref = "499" + format(str(i), "0>8s")
        runame3 = str(i)
        tradas3 = str(i)
        region_code = "WW"
        row = (
            sample_unit_ref, "H", "75110", "75110", "84110", "84110", "3603", "97281", "9905249178", "5", "E",
            region_code, "07/08/2003", "OFFICE FOR", "NATIONAL STATISTICS", runame3, "OFFICE FOR","NATIONAL STATISTICS",
            tradas3, "", "", "", "C", "", "1", FORM_TYPE, "S",
        )
        writer.writerow(row)
    return output.getvalue()


# Collection exercise execution
def execute_collection_exercise(survey_ref):
    attempt = 1
    ready = False
    while attempt <= 20 and not ready:
        get_collection_exercise_state(survey_ref)
        logger.info("Polling to see if collection exercise %s is ready to execute (attempt %s)", PERIOD, attempt)
        data = get_collection_exercise(survey_ref, PERIOD)
        if data:
            ready = data["state"] == "READY_FOR_REVIEW"
        if not ready:
            if data:
                logger.info("Collection exercise not yet READY_FOR_REVIEW, current state is %s", data["state"])
            else:
                logger.info("Collection exercise not yet available")
            attempt += 1
            time.sleep(1)

    if not ready:
        logger.error("Collection exercise %s on survey %s never went READY_FOR_REVIEW", PERIOD, survey_ref)
        raise Exception("Failed to execute collection exercise")

    while get_collection_exercise_state(survey_ref) == "READY_FOR_REVIEW":
        logger.info("Executing collection exercise %s on survey %s ", PERIOD, survey_ref)
        execute_url = f"{os.getenv('collection_exercise')}/collectionexerciseexecution/{data['id']}"
        response = requests.post(execute_url, auth=AUTH)
        response.raise_for_status()
        logger.info("Collection exercise %s on survey %s executed", PERIOD, survey_ref)
        logger.info("Waiting for READY_FOR_LIVE...")
        time.sleep(1)

    while get_collection_exercise_state(survey_ref) != "LIVE":
        logger.info("Executing process-scheduled-events...")
        process_scheduled_events_url = f"{os.getenv('collection_exercise')}/cron/process-scheduled-events"
        response = requests.get(process_scheduled_events_url, auth=AUTH)
        response.raise_for_status()
        logger.info("Waiting for LIVE...")
        time.sleep(1)


def get_collection_exercise_state(survey_ref):
    data = get_collection_exercise(survey_ref, PERIOD)
    logger.info("Collection Exercise State: %s", data["state"])
    return data["state"]


# Register respondent accounts
def register_users():
    for i in range(RESPONDENTS):
        sample_unit_ref = "499" + format(str(i), "0>8s")
        email_address = sample_unit_ref + "@test.com"
        logger.info("Attempting to register user %s", email_address)

        party_ru_url = f"{os.getenv('party')}/party-api/v1/businesses/ref/{sample_unit_ref}"
        party_response = requests.get(party_ru_url, auth=AUTH)
        party_response.raise_for_status()
        ru_party_id = json.loads(party_response.text)["id"]
        case_data = None
        attempt = 1
        while attempt <= 60:
            logger.info(
                "Polling to see if case for %s is ready to register against (attempt %s)", sample_unit_ref, attempt
            )
            case_url = f"{os.getenv('case')}/cases/partyid/{ru_party_id}"
            case_response = requests.get(case_url, auth=AUTH, params={"iac": "true"})
            case_response.raise_for_status()
            if case_response.status_code == 200:
                case_data = json.loads(case_response.text)
                if case_data:
                    break
                else:
                    logger.info("IAC not found, waiting 5s")
                    attempt += 1
                    time.sleep(5)
            else:
                logger.info("Not found, waiting 5s")
                attempt += 1
                time.sleep(5)

        if not case_data:
            logger.error("Case never found for %s", sample_unit_ref)
            raise Exception("Case not found")

        for index, case in enumerate(case_data):
            iac = case["iac"]

            if index == 0:
                register_url = f"{os.getenv('party')}/party-api/v1/respondents"
                data = {
                    "emailAddress": email_address,
                    "firstName": "first_name",
                    "lastName": "last_name",
                    "password": os.getenv("test_respondent_password"),
                    "telephone": "09876543210",
                    "enrolmentCode": iac,
                }
                register_response = requests.post(register_url, json=data, auth=AUTH)

                if register_response.status_code != 200:
                    logger.error(
                        "Couldn't register user %s because %s > %s",
                        email_address,
                        register_response.status_code,
                        register_response.text,
                    )
                    raise Exception("Failed to register user")

                # TODO: Introduce a frontstage email verification link step rather than direct activation
                respondent_id = json.loads(register_response.text)["id"]
                activate_payload = {"status_change": "ACTIVE"}
                activate_url = f"{os.getenv('party')}/party-api/v1/respondents/edit-account-status/{respondent_id}"
                activate_response = requests.put(activate_url, json=activate_payload, auth=AUTH)
                activate_response.raise_for_status()

                logger.info("Successfully registered and activated user %s", email_address)
            else:

                url = f"{os.getenv('party')}/party-api/v1/respondents/add_survey"
                request_json = {"party_id": respondent_id, "enrolment_code": iac}
                requests.post(url, auth=AUTH, json=request_json)


def data_loaded():
    url = f"{os.getenv('party')}/party-api/v1/respondents?emailAddress={'499' + format(str(0), '0>8s') + '@test.com'}"
    response = requests.get(url, auth=AUTH)
    if response.status_code != 200:
        logger.info("Loading data because Party check returned %s", response.status_code)
        return False
    data = json.loads(response.text)
    if data["total"] == 0:
        logger.info("Loading data because Party polled and %s records found", data["total"])
        return False
    if data["data"][0]["status"] != "ACTIVE":
        logger.info(
            "Loading data because %s is set to %s (will probably fail)",
            "499" + format(str(0), "0>8s") + "@test.com",
            data["data"][0]["status"],
        )
        return False
    return True


# This will only be run on Master
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("on_test_start Locust runner: %s", environment.runner)
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        environment.runner.upload_greenlet = spawn(lambda: None)
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
    response = None

    def get(
        self,
        url: str,
        grouping: str = None,
        expected_response_text: str = None,
        expected_response_status: int = 200,
        expected_attachment: str = None,
    ):
        with self.client.get(url=url, name=grouping, allow_redirects=False, catch_response=True) as response:
            self.verify_response(expected_response_status, expected_response_text, expected_attachment, response, url)
            time.sleep(r.randint(USER_WAIT_TIME_MIN_SECONDS, USER_WAIT_TIME_MAX_SECONDS))
            return response

    def post(
        self,
        url: str,
        data: dict = {},
        grouping: str = None,
        expected_response_text: str = None,
        expected_response_status: int = 200,
        expected_attachment: str = None,
        allow_redirects: bool = True,
        files=None,
    ):
        data["csrf_token"] = self.csrf_token

        with self.client.post(
            url=url, name=grouping, data=data, allow_redirects=allow_redirects, catch_response=True, files=files
        ) as response:
            self.verify_response(expected_response_status, expected_response_text, expected_attachment, response, url)
            time.sleep(r.randint(USER_WAIT_TIME_MIN_SECONDS, USER_WAIT_TIME_MAX_SECONDS))
            return response

    def verify_response(self, expected_response_status, expected_response_text, expected_attachment, response, url):
        if response.status_code != expected_response_status:
            error = f"Expected a {expected_response_status} but got a {response.status_code} for url {url}"
            response.failure(error)
            self.interrupt()

        if expected_response_text and expected_response_text not in response.text:
            error = f"response text ({expected_response_text}) isn't in returned html"
            response.failure(error)
            self.interrupt()

        if expected_attachment and expected_attachment not in response.text:
            error = f"response text ({expected_attachment}) isn't in returned html"
            response.failure(error)
            self.interrupt()


class FrontstageTasks(TaskSet, Mixins):

    def on_start(self):
        self.sign_in()
        self.stash = {}  # stash holds the response and url of a previous request so it can be re-used

    def sign_in(self):
        self.response = self.get(url="/sign-in", expected_response_text="Sign in")
        self.csrf_token = _capture_csrf_token(self.response.content.decode("utf8"))
        self.response = self.post(
            url="/sign-in", data=_generate_random_respondent(), allow_redirects=False, expected_response_status=302
        )
        self.auth_cookie = self.response.cookies["authorization"]

    @task
    def perform_requests(self):
        for request in REQUEST_LIST:
            grouping = request.get("grouping")
            expected_response_text = request.get("expected_response_text")
            expected_response_status = request.get("response_status", 200)
            harvest_dict = {}

            if "apply_stash" in request.keys():
                self.response = self.stash["response"]

            if "stash" in request.keys() and self.stash.get("url"):
                request_url = self.stash["url"]
            elif self.response and "harvest" in request:
                soup = BeautifulSoup(self.response.text, "html.parser")
                harvest_details = request["harvest"]

                if harvest_details["type"] == "url":
                    for link in soup.find_all(id=request["harvest"]["id"]):
                        if request["harvest"]["link_text"] in link.get_text():
                            request_url = link.get("href")
                            break

                if harvest_details["type"] == "name":
                    for name in harvest_details["names"]:
                        input_name = soup.find("input", attrs={"name": name})
                        input_value = input_name.attrs.get("value")
                        harvest_dict[name] = input_value
                if harvest_details["type"] == "form":
                    request_url = soup.find("form", id=harvest_details["id"]).get("action")
            else:
                request_url = request["url"]

            if request["method"] == "GET":
                self.response = self.get(request_url, grouping, expected_response_text, expected_response_status)
            elif request["method"] == "POST":
                request_url = self.response.url if request_url == "self" else request_url
                response_data = request["data"]
                file = None
                if harvest_dict:
                    response_data.update(harvest_dict)
                if "file" in response_data:
                    file_stream = open(f"/mnt/locust/{response_data['file']}", "r", encoding="utf-8")
                    file = {"file": (response_data["file"], file_stream, "application/json")}

                self.response = self.post(
                    url=request_url,
                    data=response_data,
                    grouping=grouping,
                    expected_response_text=expected_response_text,
                    expected_response_status=expected_response_status,
                    files=file,
                )
            else:
                raise exceptions.MethodNotAllowed(
                    valid_methods={"GET", "POST"},
                    description=f"Invalid request method {request['method']} for request to: {request_url}",
                )

            if "stash" in request:
                self.stash = {"url": request_url, "response": self.response}


class FrontstageLocust(HttpUser):
    tasks = {FrontstageTasks}


class GoogleCloudStorage:

    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.client = storage.Client(project=self.project_id)
        self.bucket = self.client.bucket(self.bucket_name)

    def upload(self, file_name, file):
        path = datetime.utcnow().strftime("%y-%m-%d-%H-%M") + "/" + file_name
        blob = self.bucket.blob(path)
        blob.upload_from_string(data=file, content_type="application/csv")


def _capture_csrf_token(html):
    match = CSRF_REGEX.search(html)
    if match:
        return match.group(1)


def _generate_random_respondent():
    respondent_email = f"499{random.randint(0, RESPONDENTS-1):08}@test.com"
    return {"username": respondent_email, "password": os.getenv("test_respondent_password")}
