




import django
from django.test import TestCase
from mock import patch, Mock

from messaging.apps import MessagingConfig


class TestMessagingConfig(TestCase):
    def setUp(self):
        django.setup()

    @patch('messaging.apps.add_message_backend')
    @patch('messaging.apps.add_message_type')
    def test_ready(self, add_message_type, add_message_backends):
        """Validate backends and message type registration has been done.

        :param add_message_type: mock for adding message types
        :param add_message_backends: mock for adding messaging backends
        """

        # Mock out init so we don't have to worry about AppConfig init complexity
        MC = MessagingConfig
        MC.__init__ = Mock(return_value=None)
        MC().ready()

        self.assertTrue(add_message_type.called)
        self.assertTrue(add_message_backends.called)
