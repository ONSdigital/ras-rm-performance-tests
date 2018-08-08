import requests

from sdc.clients.http.authenticatedhttpclient import AuthenticatedHTTPClient
from sdc.clients.http.baseurlhttpclient import BaseURLHTTPClient
from sdc.clients.http.statuscodecheckinghttpclient import \
    StatusCodeCheckingHTTPClient


def create(base_url, username, password):
    return BaseURLHTTPClient(
        StatusCodeCheckingHTTPClient(
            AuthenticatedHTTPClient(requests, username, password)),
        base_url)
