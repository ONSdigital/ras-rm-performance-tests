import unittest

import pytest

from sdc.clients.sftpclient import SFTPClient


@pytest.mark.usefixtures('sftpserver')
class TestSFTPClient(unittest.TestCase):
    def test_ls_lists_files_matching_a_glob_pattern(self):
        files = {
            'readme.txt': 'Text file in the root',
            'folder': {
                'readme.txt': 'Text file in a folder',
                'data1.csv': 'Data file 1',
                'data2.csv': 'Data file 2'}}

        with self.sftpserver.serve_content(files):
            self.client = SFTPClient(host=self.sftpserver.host,
                                     username='user',
                                     password='pw',
                                     port=self.sftpserver.port)

            self.assertEqual(['data1.csv', 'data2.csv'],
                             self.client.ls('folder', '*.csv'))

    def test_get_returns_the_file_contents(self):
        files = {'folder': {'readme.txt': 'Text file in a folder'}}

        with self.sftpserver.serve_content(files):
            self.client = SFTPClient(host=self.sftpserver.host,
                                     username='user',
                                     password='pw',
                                     port=self.sftpserver.port)

            self.assertEqual(b'Text file in a folder',
                             self.client.get('folder/readme.txt'))

    def test_delete_removes_the_file(self):
        files = {'files': {'readme.txt': 'Text file in a folder'}}

        with self.sftpserver.serve_content(files):
            self.client = SFTPClient(host=self.sftpserver.host,
                                     username='user',
                                     password='pw',
                                     port=self.sftpserver.port)

            self.client.delete('files/readme.txt')
            self.assertEqual([], self.client.ls('files', '*'))
