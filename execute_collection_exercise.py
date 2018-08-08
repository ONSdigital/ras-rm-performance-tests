import datetime
import json
import logging
import os

from dateutil.relativedelta import relativedelta

from sdc import csvfile
from sdc.clients import SDCClient, sdcclient
from sdc.utils import wait_for, logger

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

SURVEY_ID = os.getenv('SURVEY_ID', '75b19ea0-69a4-4c58-8d7f-4458c8f43f5c')
SURVEY_CLASSIFIERS = os.getenv('SURVEY_CLASSIFIERS',
                               '{"form_type":"0102","eq_id":"1"}')

PERIOD_OVERRIDE = os.getenv('COLLECTION_EXERCISE_PERIOD', None)

logger.initialise_from_env()

config = sdcclient.config_from_env()
sdc = SDCClient(config)


def get_previous_period():
    return (datetime.datetime.now() - relativedelta(months=1)).strftime('%Y%m')


def collection_exercise_period():
    return PERIOD_OVERRIDE or get_previous_period()


def upload_and_link_collection_instrument(survey_id,
                                          survey_classifiers,
                                          collection_instruments,
                                          exercise_id):
    instrument_id = sdc.collection_instruments.get_id_from_classifier(survey_classifiers)

    if instrument_id is None:
        sdc.collection_instruments.upload(survey_id, survey_classifiers)
        instrument_id = sdc.collection_instruments.get_id_from_classifier(survey_classifiers)
        logging.info(f'Created collection instrument, ID = {instrument_id}')
    else:
        logging.info(f'Collection instrument exists, ID = {instrument_id}')

    collection_instruments.link_to_collection_exercise(
        instrument_id,
        exercise_id)


def upload_sample(sdc, csv):
    sample_size = csvfile.num_lines(filename=csv, delimiter=':')

    with open(csv, 'rb') as fh:
        sample_id = sdc.samples.upload_file(fh)

    logging.debug(f'Uploaded sample {sample_id} with {sample_size} sample units.')

    return {'sample_id': sample_id, 'sample_size': sample_size}


def upload_collection_instrument(survey_classifiers, survey_id):
    instrument_id = sdc.collection_instruments.get_id_from_classifier(survey_classifiers)

    if instrument_id is None:
        sdc.collection_instruments.upload(survey_id, survey_classifiers)
        instrument_id = sdc.collection_instruments.get_id_from_classifier(survey_classifiers)
        logging.info(f'Created collection instrument, ID = {instrument_id}')
    else:
        logging.info(f'Collection instrument exists, ID = {instrument_id}')

    return instrument_id


def link_collection_instrument_and_sample_to_collection_exercise(exercise_id, instrument_id, sample_id):
    sdc.collection_exercises \
        .link_sample_to_collection_exercise(sample_id, exercise_id)

    sdc.collection_instruments.link_to_collection_exercise(
        instrument_id,
        exercise_id)


def collection_exercise_is_ready_for_live(exercise_id):
    ready_for_live_states = ['LIVE', 'READY_FOR_LIVE']

    return sdc.collection_exercises.get_state(exercise_id) in ready_for_live_states


def main():
    survey_id = SURVEY_ID
    exercise_period = collection_exercise_period()
    sample_file = f'{SCRIPT_DIR}/sample.csv'

    exercise = sdc.collection_exercises.get_by_survey_and_period(
        survey_id,
        exercise_period)

    exercise_id = exercise['id']

    if collection_exercise_is_ready_for_live(exercise_id):
        logging.info(
            'Quitting: The collection exercise has already been executed.')
        return

    sample = upload_sample(sdc=sdc, csv=sample_file)
    sample_id = sample['sample_id']

    instrument_id = upload_collection_instrument(
        survey_classifiers=SURVEY_CLASSIFIERS,
        survey_id=survey_id
    )

    link_collection_instrument_and_sample_to_collection_exercise(
        exercise_id=exercise_id,
        instrument_id=instrument_id,
        sample_id=sample_id)

    wait_for(lambda: sdc.samples.get_state(sample_id) == 'ACTIVE')

    wait_for(lambda: sdc.collection_exercises.get_state(exercise_id) in [
        'READY_FOR_REVIEW'])

    sdc.collection_exercises.execute(exercise_id)

    wait_for(lambda: collection_exercise_is_ready_for_live(exercise_id))

    today = datetime.date.today().strftime('%d%m%Y')

    print(json.dumps(
        {
            'survey_id': survey_id,
            'collection_exercise_id': exercise_id,
            'collection_exercise_period': exercise_period,
            'sample_size': sample['sample_size'],
            'execution_date': today,
        }
    ))


main()
