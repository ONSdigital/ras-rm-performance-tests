class CaseServiceClient(object):
    def __init__(self, http_client):
        self.http_client = http_client

    def find_by_enrolment_code(self, enrolment_code):
        response = self.http_client.get(path=f'/cases/iac/{enrolment_code}',
                                        expected_status=200)
        return response.json()