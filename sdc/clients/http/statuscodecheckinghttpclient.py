from sdc.clients.http.httpcodeexception import HTTPCodeException


class StatusCodeCheckingHTTPClient:
    EXPECTED_STATUS_KEY = 'expected_status'

    def __init__(self, client):
        self.client = client

    def get(self, **kwargs):
        args = self._parse_args(kwargs)

        response = self.client.get(**args)

        self._assert_success('GET', kwargs, response)

        return response

    def post(self, **kwargs):
        args = self._parse_args(kwargs)

        response = self.client.post(**args)

        self._assert_success('POST', kwargs, response)

        return response

    def put(self, **kwargs):
        args = self._parse_args(kwargs)

        response = self.client.put(**args)

        self._assert_success('PUT', kwargs, response)

        return response

    def _parse_args(self, kwargs):
        args = kwargs.copy()

        has_status_code_expectation = self.EXPECTED_STATUS_KEY in kwargs

        if has_status_code_expectation:
            del args[self.EXPECTED_STATUS_KEY]

        return args

    def _http_code_exception(self, method, url, expected, response):
        raise HTTPCodeException(
            expected,
            response.status_code,
            f'{method} {url} returned an unexpected '
            f'status code {response.status_code} '
            f'(expected {expected}): {response.text}')

    def _assert_success(self, method, kwargs, response):
        if self.EXPECTED_STATUS_KEY not in kwargs:
            return

        expected_status_code = kwargs[self.EXPECTED_STATUS_KEY]

        if response.status_code != expected_status_code:
            self._http_code_exception(method,
                                      kwargs['url'],
                                      expected_status_code,
                                      response)
