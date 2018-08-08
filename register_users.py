import json
import logging
import os
import sys

from num2words import num2words

from sdc.clients import SDCClient, sdcclient
from sdc.clients.enrolmentcodes import RemoteFileNotFoundException
from sdc.utils import wait_for, logger

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

logger.initialise_from_env()


def download_enrolment_codes(sdc_client,
                             period,
                             expected_codes,
                             today,
                             survey_ref):
    try:
        return sdc_client.enrolment_codes.download(
            survey_ref=survey_ref,
            period=period,
            generated_date=today,
            expected_codes=expected_codes)

    except RemoteFileNotFoundException:
        return None


def main():
    if len(sys.argv) is not 2:
        print(f'Usage: {sys.argv[0]} config_file')
        exit(1)

    with open(sys.argv[1], 'r') as file:
        exercise_config = json.load(file)

    logging.debug(f'Exercise config loaded: {exercise_config}')

    sdc = SDCClient(sdcclient.config_from_env())

    survey = sdc.surveys.get_by_id(exercise_config['survey_id'])

    enrolment_codes = wait_for(lambda: download_enrolment_codes(
        sdc_client=sdc,
        survey_ref=survey['surveyRef'],
        period=exercise_config['collection_exercise_period'],
        expected_codes=exercise_config['sample_size'],
        today=exercise_config['execution_date']))

    logging.debug(f'Found enrolment codes {enrolment_codes}')

    count = 0
    users = []
    for code in enrolment_codes:
        logging.debug(f'Registering user with code {code}')
        count += 1
        email_address = f'user-{exercise_config["collection_exercise_period"]}-{count}@example.com'
        users.append(email_address)
        sdc.users.register(
            email_address=email_address,
            first_name='User',
            last_name=num2words(count),
            password='Top5ecret',
            telephone='0123456789',
            enrolment_code=code
        )

    # Activate user
    logging.info('Verifying user accounts')
    for email_address in users:
        sdc.users.verify(email_address)


main()
