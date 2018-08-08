class BaseURLHTTPClient:
    def __init__(self, client, base_url):
        self.client = client
        self.base_url = base_url

    def get(self, **kwargs):
        args = self._get_args(kwargs)

        return self.client.get(**args)

    def post(self, **kwargs):
        args = self._get_args(kwargs)

        return self.client.post(**args)

    def put(self, **kwargs):
        args = self._get_args(kwargs)

        return self.client.put(**args)

    def _get_args(self, kwargs):
        args = kwargs.copy()
        if 'path' not in args:
            return args

        if 'url' in args:
            raise Exception(
                'path and url arguments cannot be provided together')

        args['url'] = f'{self.base_url}{args["path"]}'
        del args['path']

        return args
