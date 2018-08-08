import unittest
from unittest.mock import Mock, call

from requests import Response

from sdc.clients.enrolmentcodes import EnrolmentCodes, \
    RemoteFileNotFoundException, \
    MultipleRemoteFilesFoundException, IncorrectNumberOfEnrolmentCodes


class TestEnrolmentCodes(unittest.TestCase):
    BASE_DIR = 'BSD'

    def setUp(self):
        self.sftp_client = Mock()
        self.sftp_client.ls = Mock()
        self.sftp_client.ls.return_value = ['a-file.csv']
        self.sftp_client.get = Mock()
        self.sftp_client.get.return_value = b''
        self.sftp_client.delete = Mock()

        self.enrolment_codes = EnrolmentCodes(sftp_client=self.sftp_client,
                                              base_dir=self.BASE_DIR)

    def test_download_checks_if_the_ls(self):
        self.enrolment_codes.download(survey_ref='011',
                                      period='201806',
                                      generated_date='11062018',
                                      expected_codes=0)

        self.sftp_client.ls.assert_called_with(
            self.BASE_DIR, 'BSNOT_011_201806_11062018_*.csv')

    def test_download_raises_if_file_is_not_found(self):
        self.sftp_client.ls.return_value = []

        with self.assertRaises(RemoteFileNotFoundException) as context:
            self.enrolment_codes.download(survey_ref='022',
                                          period='201804',
                                          generated_date='01042018',
                                          expected_codes=1)

        self.assertEqual(
            f"No files found matching "
            f"'{self.BASE_DIR}/BSNOT_022_201804_01042018_*.csv'",
            context.exception.message
        )

    def test_download_raises_if_multiple_files_are_found(self):
        self.sftp_client.ls.return_value = ['file1.csv', 'file2.csv']

        with self.assertRaises(MultipleRemoteFilesFoundException) as context:
            self.enrolment_codes.download(survey_ref='033',
                                          period='201804',
                                          generated_date='01042018',
                                          expected_codes=2)
        self.assertEqual(
            f"Expected 1 file matching "
            f"'{self.BASE_DIR}/BSNOT_033_201804_01042018_*.csv'; "
            f"found 2 - ['file1.csv', 'file2.csv']",
            context.exception.message)

    def test_download_deletes_the_file_after_getting_it(self):
        self.sftp_client.ls.return_value = ['the-file.csv']

        self.enrolment_codes.download(survey_ref='044',
                                      period='201807',
                                      generated_date='03072018',
                                      expected_codes=0)

        self.sftp_client.assert_has_calls(
            [call.get(f'{self.BASE_DIR}/the-file.csv'),
             call.delete(f'{self.BASE_DIR}/the-file.csv')])

    def test_download_returns_the_enrolment_codes(self):
        self.sftp_client.get.return_value = bytes(
            '49900000008:lpt3932m4yxs:NOTSTARTED:null:null:null:null:null:FE\n'
            '49900000007:p2js5r9m2gbz:NOTSTARTED:null:null:null:null:null:FE\n'
            '49900000005:5sypjcp7rjyg:NOTSTARTED:null:null:null:null:null:FE\n'
            '49900000006:22yr5vmdxbx6:NOTSTARTED:null:null:null:null:null:FE\n',
            'utf-8')

        result = self.enrolment_codes.download(survey_ref='055',
                                               period='201807',
                                               generated_date='03072018',
                                               expected_codes=4)

        expected = [
            'lpt3932m4yxs',
            'p2js5r9m2gbz',
            '5sypjcp7rjyg',
            '22yr5vmdxbx6'
        ]

        self.assertEqual(expected, result)

    def test_download_does_not_delete_if_the_content_is_bad(self):
        self.sftp_client.get.return_value = \
            'bad\n' + \
            'con:tent\n'

        with self.assertRaises(Exception):
            self.enrolment_codes.download(survey_ref='066',
                                          period='201807',
                                          generated_date='03072018',
                                          expected_codes=2)

        self.sftp_client.delete.assert_not_called()

    def test_download_does_not_delete_the_file_if_not_expected_num_of_codes(
            self):
        self.sftp_client.get.return_value = bytes(
            '49900000008:lpt3932m4yxs:NOTSTARTED:null:null:null:null:null:FE\n'
            '49900000007:p2js5r9m2gbz:NOTSTARTED:null:null:null:null:null:FE\n'
            '49900000005:5sypjcp7rjyg:NOTSTARTED:null:null:null:null:null:FE\n'
            '49900000006:22yr5vmdxbx6:NOTSTARTED:null:null:null:null:null:FE\n',
            'utf-8')

        with self.assertRaises(IncorrectNumberOfEnrolmentCodes) as context:
            self.enrolment_codes.download(survey_ref='077',
                                          period='201807',
                                          generated_date='03072018',
                                          expected_codes=5)

        self.assertEqual(
            "Expected 5 enrolment codes; got 4 - ["
            "'lpt3932m4yxs', 'p2js5r9m2gbz', '5sypjcp7rjyg', '22yr5vmdxbx6'"
            "]",
            context.exception.message)

    def _mock_http_get_reponse(self, content):
        response = Response()
        response._content = content
        response.encoding = 'utf-8'
        self.http_client.get = Mock()
        self.http_client.get.return_value = response
