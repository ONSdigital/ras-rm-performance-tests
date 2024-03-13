import json
import logging
import os
import re
import sys

from werkzeug import exceptions
from locust import HttpUser, TaskSet, task, events, between
from locust.runners import MasterRunner, LocalRunner

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()

requests_file = './' + os.getenv('requests_file')
logger.info("Retrieving JSON requests from: %s", requests_file)
with open(requests_file, encoding='utf-8') as requests_file:
    requests_json = json.load(requests_file)
    request_list = requests_json["requests"]

CSRF_REGEX = re.compile(r'<input id="csrf_token" name="csrf_token" type="hidden" value="(.+?)"\/?>')

# This will only be run on Master
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        logger.info("Starting tests on %s", environment.runner)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("on_test_stop Locust runner: %s", environment.runner)
    if isinstance(environment.runner, (MasterRunner, LocalRunner)):
        logger.info("Stopping tests on %s", environment.runner)

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

    def post(self, url: str, data: dict = {}, headers: dict = {}):
        data['csrf_token'] = self.csrf_token
        headers['Referer'] = 'https://surveys-preprod.onsdigital.uk/sign-in/'
        with self.client.post(url=url, data=data, allow_redirects=False, catch_response=True, headers=headers) as response:
            if response.status_code != 302:
                f = open("response.html", "a")
                f.write(response.text)
                f.close()
                error = f"Expected a 302 but got a ({response.status_code}) for url {url} and data {data}"
                response.failure(error)
                sys.exit()
                self.interrupt()

            return response


class FrontstageTasks(TaskSet, Mixins):

    def on_start(self):
        self.sign_in()

    def sign_in(self):
        response = self.get(url="/sign-in", expected_response_text="Sign in")
        self.csrf_token = _capture_csrf_token(response.content.decode('utf8'))

        response = self.post("/sign-in", data=get_username_and_password())
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
    wait_time = between(0, 0)

def _capture_csrf_token(html):
    match = CSRF_REGEX.search(html)
    if match:
        return match.group(1)


def get_username_and_password():
    return {"username": os.getenv("frontstage_respondent_username"),
            "password": os.getenv("frontstage_respondent_password")}
