import logging
import os

import requests

collection_instrument_url = \
    os.getenv('COLLECTION_INSTRUMENT_URL',
              'http://localhost:8002')
collection_instrument_search_endpoint = \
    os.getenv('COLLECTION_INSTRUMENT_SEARCH_ENDPOINT',
              '/collection-instrument-api/1.0.2/collectioninstrument')
collection_instrument_upload_endpoint = \
    os.getenv('COLLECTION_INSTRUMENT_UPLOAD_ENDPOINT',
              '/collection-instrument-api/1.0.2/upload')
collection_instrument_link_endpoint = \
    os.getenv('COLLECTION_INSTRUMENT_LINK_ENDPOINT',
              '/collection-instrument-api/1.0.2/link-exercise')


class CollectionInstrumentServiceClient:
    def __init__(self, http_client):
        self.http_client = http_client

    def upload(self, survey_id, survey_classifiers):
        upload_params = {'survey_id': survey_id, 'classifiers': survey_classifiers}

        self.http_client.post(
            path=collection_instrument_upload_endpoint,
            params=upload_params,
            expected_status=requests.codes.ok)

    def link_to_collection_exercise(self, instrument_id, exercise_id):
        path = f'{collection_instrument_link_endpoint}/{instrument_id}/{exercise_id}'

        self.http_client.post(path=path, expected_status=requests.codes.ok)
        logging.info('Collection instrument linked to exercise!')

    def get_id_from_classifier(self, classifiers):
        search_params = {'searchString': classifiers}
        path = collection_instrument_search_endpoint

        response = self.http_client.get(
            path=path,
            params=search_params,
            expected_status=requests.codes.ok
        )

        results = response.json()

        return results[0]['id'] if len(results) > 0 else None
