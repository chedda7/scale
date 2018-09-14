"""Defines the command for performing testing with EchoCommandMessage"""





import logging
from datetime import datetime

from django.core.management.base import BaseCommand

from messaging.manager import CommandMessageManager
from messaging.messages.echo import EchoCommandMessage

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command for performing testing with EchoCommandMessage
    """

    help = 'Command for performing testing with EchoCommandMessage'

    def add_arguments(self, parser):
        parser.add_argument('-c', '--count', action='store', type=int,
                            help='Number of echo messages to generate.')

    def handle(self, *args, **options):
        """See :meth:`django.core.management.base.BaseCommand.handle`.

        This method starts the command.
        """

        count = options.get('count')
        if not count:
            count = 1

        logger.info('Command starting: scale_echo_message - sending {} message(s)'.format(count))

        manager = CommandMessageManager()
        messages = []
        for x in range(count):
            messages.append(EchoCommandMessage.from_json(
                {'message': 'Greetings, this is echo #{} at {}!'.format(x + 1, datetime.utcnow())}))
                
        
        manager.send_messages(messages)

        logger.info('Command completed: scale_echo_message')
