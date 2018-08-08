import unittest
from unittest.mock import Mock

import httpretty

from sdc.clients.users import Users, NoVerificationEmailFound, MultipleEmailsFound, VerificationLinkNotFound, \
    VerificationRequestFailed
from tests.shared.requests import Requests


class TestUsers(unittest.TestCase, Requests):
    VERIFICATION_LINK = \
        "http://frontstage.services.com/register/activate-account/" \
        "InVzZXItMjAxODA1LTFAZXhhbXBsZS5jb20i.DkXhaw.DbfocE4M99mRWhu3HbBVVRavjsY"
    VERIFICATION_EMAIL = {
        "reference": "05b3b493-aeeb-486e-9b63-f24cbd651fd8",
        "email_address": "user-201805-1@example.com",
        "personalisation": {
            "ACCOUNT_VERIFICATION_URL": VERIFICATION_LINK
        },
        "template_id": "53c59576-8c3b-4298-99d1-b245ddd28500"
    }

    def setUp(self):
        self.user_client = Mock()
        self.notify_client = Mock()

        self.users = Users(user_client=self.user_client,
                           notify_client=self.notify_client)

    def test_register_delegates_to_the_user_client(self):
        self.users.register(
            enrolment_code='abc1234',
            email_address='mad.hatter@example.com',
            first_name='Mad',
            last_name='Hatter',
            password='Top5ecret',
            telephone='0123456789'
        )

        self.user_client.register.assert_called_with(
            enrolment_code='abc1234',
            email_address='mad.hatter@example.com',
            first_name='Mad',
            last_name='Hatter',
            password='Top5ecret',
            telephone='0123456789'
        )

    @httpretty.activate
    def test_activate_account_fetches_emails_from_the_mock(self):
        self.notify_client.get_emails_for.return_value = [
            self.VERIFICATION_EMAIL
        ]

        httpretty.register_uri(
            httpretty.GET,
            self.VERIFICATION_LINK,
            status=200
        )

        self.users.verify('mad.hatter@example.com')

        self.notify_client \
            .get_emails_for \
            .assert_called_with('mad.hatter@example.com')

    def test_activate_account_fails_if_no_emails_are_found(self):
        self.notify_client.get_emails_for.return_value = []

        with self.assertRaises(NoVerificationEmailFound):
            self.users.verify('mad.hatter@example.com')

    def test_activate_account_fails_multiple_emails_are_found(self):
        self.notify_client.get_emails_for.return_value = [{'message': 'one'},
                                                          {'message': 'two'}]

        with self.assertRaises(MultipleEmailsFound):
            self.users.verify('mad.hatter@example.com')

    def test_activate_raises_if_no_verification_link_is_in_the_email(self):
        self.notify_client.get_emails_for.return_value = [
            {'personalisation': {}}
        ]

        with self.assertRaises(VerificationLinkNotFound):
            self.users.verify('mad.hatter@example.com')

    @httpretty.activate
    def test_activate_makes_a_get_request_to_the_verify_link(self):
        self.notify_client.get_emails_for.return_value = [
            self.VERIFICATION_EMAIL
        ]

        httpretty.register_uri(
            httpretty.GET,
            self.VERIFICATION_LINK,
            status=200
        )

        self.users.verify('mad.hatter@example.com')

    @httpretty.activate
    def test_activate_raise_if_activation_fails(self):
        self.notify_client.get_emails_for.return_value = [
            self.VERIFICATION_EMAIL
        ]

        httpretty.register_uri(
            httpretty.GET,
            self.VERIFICATION_LINK,
            status=400
        )

        with self.assertRaises(VerificationRequestFailed):
            self.users.verify('mad.hatter@example.com')