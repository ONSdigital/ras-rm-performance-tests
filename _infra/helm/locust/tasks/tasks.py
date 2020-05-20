from locust import HttpLocust, TaskSet, task, events, between
import datetime
import sys
import os
import json
import requests
import logging
import csv
from datetime import timezone, datetime
from functools import partial

survey_short_name = 'QBS'
survey_long_name = 'Quarterly Business Survey'
survey_ref = '139'
form_type = '0001'
eq_id = '2'
period = '1806'
logger = logging.getLogger()

# Ignore these during collection exercise event processing as they are the key 
# for the collection exercise and don't represent event data
ignore_columns = ['surveyRef', 'exerciseRef']

# Load data for tests
def load_data():
    auth = (os.getenv('SECURITY_USER_NAME'), os.getenv('SECURITY_USER_PASSWORD'))

    survey_id = load_survey(auth)
    load_collection_exercises(auth)
    load_collection_exercise_events(auth)
    load_collection_instrument(auth, survey_id)

    logger.info('Executing collection exercise', extra={'survey_id':survey_id, 'period':period, 'ci_type':'eQ'})

# Survey loading
def load_survey(auth):
    logger.info('Trying to find survey %s', survey_short_name)
    get_url = f"{os.getenv('SURVEY')}/surveys/shortname/{survey_short_name}"
    get_response = requests.get(get_url, auth=auth)

    if get_response.status_code != 404:
        get_data = json.loads(get_response.text)
        logger.info("Survey successfully found at id %s", get_data['id'])
        return get_data['id']
    
    create_url = f"{os.getenv('SURVEY')}/surveys"
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
    create_response.raise_for_status()
    create_data = json.loads(create_response.text)
    logger.info("Successfully created survey at id %s", create_data['id'])
    return create_data['id']

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
    config = json.load(open("locust-tasks/collection-exercise-config.json"))
    input_files = config['inputFiles']
    column_mappings = config['columnMappings']
    url = f"{os.getenv('COLLECTION_EXERCISE')}/collectionexercises"

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
    config = json.load(open("locust-tasks/collection-exercise-event-config.json"))
    input_files = config['inputFiles']
    column_mappings = config['columnMappings']
    url = f"{os.getenv('COLLECTION_EXERCISE')}/collectionexercises"

    row_handler = partial(process_event_row, auth=auth, url=url)
    
    process_files(input_files, row_handler, column_mappings)

def process_event_row(data, auth, url):
    collection_exercise_id = get_collection_exercise_id(survey_ref=data['surveyRef'], exercise_ref=data['exerciseRef'], url=url, auth=auth)
    for event_tag, date in data.items():
        if not event_tag in ignore_columns:
            post_event(collection_exercise_id, event_tag, date, auth, url)

def get_collection_exercise_id(survey_ref, exercise_ref, url, auth):
    response = requests.get(f'{url}/{exercise_ref}/survey/{survey_ref}', auth=auth, verify=False)
    data = json.loads(response.text)

    logger.info("Processing survey %s, collection exercise %s", survey_ref, exercise_ref)

    if "error" in data:
        logger.error("Error getting collection exercise ID for posting events: survey %s, exercise %s, error %s", survey_ref, exercise_ref, data['error'])
    else:
        return data['id']

def post_event(collection_exercise_id, event_tag, date, auth, url):
    data = {"tag": event_tag, "timestamp": reformat_date(date)}

    response = requests.post(f'{url}/{collection_exercise_id}/events', json=data, auth=auth, verify=False)

    status_code = response.status_code
    detail_text = response.text if status_code != 201 else ''

    logger.info("%s <= %s (%s)", status_code, data, detail_text)

# Collection instrument loading
def load_collection_instrument(auth, survey_id):
    logger.info('Uploading eQ collection instrument', extra={'survey_id':survey_id, 'form_type':form_type})
    url = f"{os.getenv('COLLECTION_INSTRUMENT')}/collection-instrument-api/1.0.2/upload"

    classifiers = {
        "form_type": form_type,
        "eq_id": eq_id
    }

    params = {
        "classifiers": json.dumps(classifiers),
        "survey_id": survey_id
    }

    response = requests.post(url=url, auth=auth, params=params)

# This will only be run on Master and should be used for loading test data
if '--master' in sys.argv:
  load_data()

class FrontstageTasks(TaskSet):
  @task(1)
  def status(self):
    response = self.client.get("/sign-in")

class FrontstageLocust(HttpLocust):
  task_set = FrontstageTasks
  wait_time = between(5, 15)
