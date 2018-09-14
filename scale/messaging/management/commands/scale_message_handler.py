"""Defines the command for retrieval and execution of CommandMessages"""





import logging
import signal

from django.core.management.base import BaseCommand

from error.models import Error
from messaging.manager import CommandMessageManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command for retrieval and execution of CommandMessages from queue
    """

    help = 'Command for retrieval and execution of CommandMessages from queue'

    def handle(self, *args, **options):
        """See :meth:`django.core.management.base.BaseCommand.handle`.

        This method starts the command.
        """

        logger.info('Command starting: scale_message_handler')

        self.running = True

        logger.info('Initializing message handler')
        logger.info('Caching builtin errors...')
        Error.objects.cache_builtin_errors()
        logger.info('Initialization complete, ready to process messages')
        
        # Set the signal handler
        signal.signal(signal.SIGINT, self.interupt)
        signal.signal(signal.SIGTERM, self.interupt)

        manager = CommandMessageManager()

        while self.running:
            manager.receive_messages()

        logger.info('Command completed: scale_message_handler')

    def interupt(self, signum, frame):

        logger.info('Halting queue processing as a result of signal: {}'.format(signum))
        self.running = False
