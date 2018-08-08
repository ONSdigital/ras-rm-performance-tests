import pytest


@pytest.fixture(scope="class")
def sftpserver(request, sftpserver):
    request.cls.sftpserver = sftpserver
