from urllib.parse import quote_plus


class NotifyMockClient:
    def __init__(self, http_client):
        self.http_client = http_client

    def get_emails_for(self, email_address):
        return self.http_client.get(
            path=f'/inbox/emails/{quote_plus(email_address)}'
        ).json()
