import fnmatch
import logging

import paramiko


class SFTPClient:
    def __init__(self, host, username, password, port=22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port

    def __del__(self):
        self._disconnect_from_sftp_server()

    def ls(self, path, glob_pattern):
        self._connect_to_sftp_server()

        logging.debug(
            f'SFTP: Listing remote files matching {path}/{glob_pattern}')

        all_files = self.client.listdir(path)
        filtered_files = fnmatch.filter(all_files, glob_pattern)

        logging.debug(f'SFTP: Found {filtered_files}')

        return filtered_files

    def get(self, path):
        self._connect_to_sftp_server()

        logging.debug(f'SFTP: Getting remote file {path}')

        with self.client.open(path, "r") as sftp_file:
            return sftp_file.read()

    def delete(self, path):
        self._connect_to_sftp_server()

        logging.debug(f'SFTP: Deleting remote file {path}')
        self.client.remove(path)

    def _connect_to_sftp_server(self):
        if hasattr(self, 'ssh'):
            return

        self.ssh = paramiko.SSHClient()

        # This must be set so that connections from containers without the
        # host key can continue. There is no test for this line of code.
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.ssh.connect(hostname=self.host,
                         port=self.port,
                         username=self.username,
                         password=self.password,
                         # The following 2 settings are required to stop
                         # paramiko from using public keys. There is are no
                         # tests covering these settings.
                         allow_agent=False,
                         look_for_keys=False)

        self.client = self.ssh.open_sftp()

    def _disconnect_from_sftp_server(self):
        if hasattr(self, 'client'):
            self.client.close()
            self.ssh.close()
