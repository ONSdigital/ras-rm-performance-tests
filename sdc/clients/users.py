import logging

import requests


class Users:
    def __init__(self, user_client, notify_client):
        self.user_client = user_client
        self.notify_client = notify_client

    def register(self, **kwargs):
        self.user_client.register(**kwargs)

    def verify(self, email_address):
        logging.info(f'Verifying account for {email_address}')

        message = self._get_message_from_inbox(email_address)

        verify_link = self._get_verification_link_from_message(
            email_address,
            message)

        logging.debug(f'Found verification link: {verify_link}')

        response = requests.get(verify_link)

        if response.status_code != requests.codes.ok:
            raise VerificationRequestFailed(verify_link, response.status_code)

    def _get_message_from_inbox(self, email_address):
        messages = self.notify_client.get_emails_for(email_address)

        num_messages = len(messages)

        if num_messages < 1:
            raise NoVerificationEmailFound(email_address)

        if num_messages > 1:
            raise MultipleEmailsFound(email_address, num_messages)

        return messages[0]

    def _get_verification_link_from_message(self, email_address, message):
        if 'ACCOUNT_VERIFICATION_URL' not in message['personalisation']:
            raise VerificationLinkNotFound(email_address)

        return message['personalisation']['ACCOUNT_VERIFICATION_URL']


class NoVerificationEmailFound(Exception):
    def __init__(self, email_address):
        self.message = \
            f'Expected to find exactly 1 message for {email_address}; ' \
            f'found none.'


class MultipleEmailsFound(Exception):
    def __init__(self, email_address, found):
        self.message = \
            f'Expected to find exactly 1 message for {email_address}; ' \
            f'found {found}.'


class VerificationLinkNotFound(Exception):
    def __init__(self, email_address):
        self.message = f'Verification link not found for {email_address}.'


class VerificationRequestFailed(Exception):
    def __init__(self, email_address, status_code):
        self.message = f'Verification request failed for {email_address}; ' \
                       f'get status code {status_code}.'
