class SurveyServiceClient:
    def __init__(self, http_client):
        self.http_client = http_client

    def get_by_id(self, id):
        return self.http_client.get(path=f'/surveys/{id}',
                                    expected_status=200).json()
