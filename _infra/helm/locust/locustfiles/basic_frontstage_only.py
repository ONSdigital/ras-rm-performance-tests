import datetime
import json
import logging
import os
import re
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup

from werkzeug import exceptions
from google.cloud import storage
from locust import HttpUser, TaskSet, task, events, between
from locust.runners import MasterRunner, LocalRunner

r = random.Random()

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()

requests_file = './/' + os.getenv('requests_file')
logger.info("Retrieving JSON requests from: %s", requests_file)
with open(requests_file, encoding='utf-8') as requests_file:
    requests_json = json.load(requests_file)
    request_list = requests_json["requests"]

# Ignore these during collection exercise event processing as they are the key
# for the collection exercise and don't represent event data
CSRF_REGEX = re.compile(r'<input id="csrf_token" name="csrf_token" type="hidden" value="(.+?)"\/?>')
USER_WAIT_TIME_MIN_SECONDS = 5
USER_WAIT_TIME_MAX_SECONDS = 15


# This will only be run on Master
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("on_test_start Locust runner: %s", environment.runner)
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        logger.error(f"Running on MasterRunner/LocalRunner, no actions to take")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("on_test_stop Locust runner: %s", environment.runner)
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        logger.error(f"Running on MasterRunner/LocalRunner, no actions to take")


class Mixins:
    csrf_token = None
    auth_cookie = None
    response = None

    def get(
        self,
        url: str,
        grouping: str=None,
        expected_response_text: str=None,
        expected_response_status: int=200,
    ):
        with self.client.get(url=url,
                             name=grouping,
                             allow_redirects=False,
                             catch_response=True,
                             headers={"Referer":"https://surveys-preprod.onsdigital.uk"}
                             ) as response:
            self.verify_response(expected_response_status, expected_response_text, response, url)
            return response

    def post(
        self,
        url: str,
        data: dict = {},
        grouping: str=None,
        expected_response_text: str=None,
        expected_response_status: int=200,
        allow_redirects: bool=True,
    ):
        data["csrf_token"] = self.csrf_token

        with self.client.post(
            url=url,
            name=grouping,
            data=data,
            allow_redirects=allow_redirects,
            catch_response=True,
            headers={"Referer":"https://surveys-preprod.onsdigital.uk"}
        ) as response:
            self.verify_response(expected_response_status, expected_response_text, response, url)
            return response

    def verify_response(self, expected_response_status, expected_response_text, response, url):

        if response.status_code != expected_response_status:
            error = f"Expected a {expected_response_status} but got a {response.status_code} for url {url}"
            response.failure(error)
            self.interrupt()

        if expected_response_text and expected_response_text not in response.text:
            error = f"response text ({expected_response_text}) isn't in returned html"
            response.failure(error)
            self.interrupt()


class FrontstageTasks(TaskSet, Mixins):

    def on_start(self):
        self.sign_in()

    def sign_in(self):
        self.response = self.get(url="/sign-in", expected_response_text="Sign in")
        self.csrf_token = _capture_csrf_token(self.response.content.decode('utf8'))
        self.response = self.post(url="/sign-in",
                                  data=_respondent(),
                                  allow_redirects=False,
                                  expected_response_status=302)
        self.auth_cookie = self.response.cookies['authorization']

    @task
    def perform_requests(self):
        for request in request_list:
            grouping = request.get("grouping")
            expected_response_text = request.get("expected_response_text")
            expected_response_status = request.get("response_status", 200)

            if self.response and "harvest_url" in request:
                soup = BeautifulSoup(self.response.text, "html.parser")

                for link in soup.find_all(id=request["harvest_url"]["id"]):
                    if request["harvest_url"]["link_text"] in link.get_text():
                        request_url = link.get("href")
                        break
                    logger.error(f"Unable to harvest url {request['harvest_url']}")
                    self.interrupt()
            else:
                request_url = request["url"]

            if request["method"] == "GET":
                self.response =self.get(request_url, grouping, expected_response_text, expected_response_status)
            elif request["method"] == "POST":
                request_url = self.response.url if request_url == "self" else request_url
                response_data = request['data']
                self.response = self.post(url=request_url,
                                          data=response_data,
                                          grouping=grouping,
                                          expected_response_text=expected_response_text,
                                          expected_response_status=expected_response_status)
            else:
                raise exceptions.MethodNotAllowed(
                    valid_methods={"GET", "POST"},
                    description=f"Invalid request method {request['method']} for request to: {request_url}"
                )
            time.sleep(r.randint(USER_WAIT_TIME_MIN_SECONDS, USER_WAIT_TIME_MAX_SECONDS))

class FrontstageLocust(HttpUser):
    tasks = {FrontstageTasks}
    wait_time = between(USER_WAIT_TIME_MIN_SECONDS, USER_WAIT_TIME_MAX_SECONDS)



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


def _respondent():
    return {"username": os.getenv("frontstage_respondent_username"), "password": os.getenv("frontstage_respondent_password")}
