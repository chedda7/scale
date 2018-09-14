"""Backend supporting Amazon SQS"""





import json
import logging
import uuid

from messaging.backends.backend import MessagingBackend
from util.aws import AWSCredentials, SQSClient

logger = logging.getLogger(__name__)


class SQSMessagingBackend(MessagingBackend):
    """Backend supporting message passing via Amazon SQS"""

    def __init__(self):
        super(SQSMessagingBackend, self).__init__('sqs')

        self._region_name = self._broker.get_address()

        self._credentials = AWSCredentials(self._broker.get_user_name(),
                                           self._broker.get_password())

    def send_messages(self, messages):
        """See:meth:`messaging.backends.backend.MessagingBackend.send_messages`"""
        with SQSClient(self._credentials, self._region_name) as client:
            encoded_messages = []
            for message in messages:
                encoded_messages.append({'Id': str(uuid.uuid4()), 'MessageBody': json.dumps(message)})

            client.send_messages(self._queue_name, encoded_messages)

    def receive_messages(self, batch_size):
        """See :meth:`messaging.backends.backend.MessagingBackend.receive_messages`"""

        with SQSClient(self._credentials, self._region_name) as client:
            for message in client.receive_messages(self._queue_name, batch_size=batch_size):
                # Accept success back via generator send
                success = yield json.loads(message.body)
                if success:
                    message.delete()

