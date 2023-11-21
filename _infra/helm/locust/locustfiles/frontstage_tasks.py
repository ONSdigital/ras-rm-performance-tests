import os
import random
import re

from locust import HttpUser, TaskSet, between, task

from _infra.helm.locust.locustfiles.mixins import Mixins

CSRF_REGEX = re.compile(r'<input id="csrf_token" name="csrf_token" type="hidden" value="(.+?)"\/?>')


class FrontstageTasks(TaskSet, Mixins):

    def on_start(self):
        self.sign_in()

    def sign_in(self):
        response = self.get(url="/sign-in", expected_response_text="Sign in")

        if os.getenv("csrf_enabled"):
            self.csrf_token = _capture_csrf_token(response.content.decode('utf8'))

        response = self.post("/sign-in", data=_generate_random_respondent())
        self.auth_cookie = response.cookies['authorization']

    @task
    def todo(self):
        self.get("/surveys/todo", expected_response_text="Click on the survey name to complete your questionnaire")


def _capture_csrf_token(html):
    match = CSRF_REGEX.search(html)
    if match:
        return match.group(1)


def _generate_random_respondent():
    respondents_count = int(os.getenv('test_respondents'))
    respondent_email = f"499{random.randint(0, respondents_count):8}@test.com"
    return {"username": respondent_email, "password": os.getenv('test_respondent_password')}
