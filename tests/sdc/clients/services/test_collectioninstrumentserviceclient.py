import unittest
from unittest.mock import Mock

from sdc.clients.services import CollectionInstrumentServiceClient
from tests.shared.requests import Requests


class TestCollectionInstrumentServiceClient(unittest.TestCase, Requests):
    def setUp(self):
        self.http_client = Mock()
        self.client = CollectionInstrumentServiceClient(http_client=self.http_client)

    def test_upload(self):
        survey_id = 'be11e5ed-f2ce-4838-8222-57e793e97a5b'
        survey_classifiers = {'classifier': 'value'}

        self.client.upload(
            survey_id=survey_id,
            survey_classifiers=survey_classifiers)

        self.http_client.post.assert_called_with(
            path='/collection-instrument-api/1.0.2/upload',
            params={'survey_id': survey_id, 'classifiers': survey_classifiers},
            expected_status=200)

    def test_link_to_collection_exercise(self):
        instrument_id = '71a195a6-cf15-4ade-9139-41f9101a5832'
        exercise_id = '8e13e4fa-9745-44a1-a57b-58fbbc00ac08'

        self.client.link_to_collection_exercise(
            instrument_id=instrument_id,
            exercise_id=exercise_id)

        self.http_client.post.assert_called_with(
            path=f'/collection-instrument-api/1.0.2/link-exercise/{instrument_id}/{exercise_id}',
            expected_status=200
        )

    def test_get_id_from_classifier_makes_a_get_request_to_the_service(self):
        classifiers = {'classifier': 'example'}
        self.http_client.get.return_value = \
            self.http_response(status_code=200, body=b'[]')

        self.client.get_id_from_classifier(classifiers)

        self.http_client.get.assert_called_with(
            path='/collection-instrument-api/1.0.2/collectioninstrument',
            params={'searchString': classifiers},
            expected_status=200
        )

    def test_get_id_from_classifier_returns_None_if_no_results_returned(self):
        classifiers = {'classifier': 'example'}
        self.http_client.get.return_value = \
            self.http_response(status_code=200, body=b'[]')

        result = self.client.get_id_from_classifier(classifiers)

        self.assertIsNone(result)

    def test_get_id_from_classifier_returns_the_id_of_the_first_object_returned(self):
        classifiers = {'classifier': 'example'}
        self.http_client.get.return_value = \
            self.http_response(
                status_code=200,
                body=b'[{"id": "first-id"}, {"id": "second-id"}]')

        result = self.client.get_id_from_classifier(classifiers)

        self.assertEqual('first-id', result)
