




import logging

from messaging.messages.message import CommandMessage

logger = logging.getLogger(__name__)


class EchoCommandMessage(CommandMessage):
    def __init__(self):
        super(EchoCommandMessage, self).__init__('echo')

        self._payload = None

    def execute(self):
        """See :meth:`messaging.messages.message.CommandMessage.execute`"""
        logger.info(self._payload)
        return True

    @staticmethod
    def from_json(json_dict):
        """See :meth:`messaging.messages.message.CommandMessage.from_json`"""
        this = EchoCommandMessage()
        this._payload = json_dict
        return this

    def to_json(self):
        """See :meth:`messaging.messages.message.CommandMessage.to_json`"""
        return self._payload
