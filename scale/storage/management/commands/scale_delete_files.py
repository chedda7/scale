"""Defines the command line method for running a delete files task"""
from __future__ import unicode_literals

import ast
import json
import logging
import os
import signal
import sys
from collections import namedtuple

from django.core.management.base import BaseCommand

import storage.delete_files_job as delete_files_job
from storage.brokers.factory import get_broker
from storage.configuration.workspace_configuration import WorkspaceConfiguration
from messaging.manager import CommandMessageManager
from storage import delete_files_job
from storage.messages.delete_files import create_delete_files_messages

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command that executes the delete file process for a given file
    """

    help = 'Perform a file destruction operation on a file'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--files', nargs='+', type=json.loads, required=True,
                            help='File path and ID in a JSON string.' +
                            ' e.g: "{"file_path":"some.file", "id":"399"}"')
        parser.add_argument('-w', '--workspace', action='store', type=json.loads, required=True,
                            help='Workspace configuration in a JSON string.')
        parser.add_argument('-p', '--purge', action='store', type=bool, required=True,
                            help='Purge all records for the given file')

    def handle(self, *args, **options):
        """See :meth:`django.core.management.base.BaseCommand.handle`.

        This method starts the file destruction process.
        """

        # Register a listener to handle clean shutdowns
        signal.signal(signal.SIGTERM, self._onsigterm)

        files = options.get('files')
        workspace_config = ast.literal_eval(options.get('workspace'))
        purge = options.get('purge')

        scale_file = namedtuple('ScaleFile', ['id', 'file_path'])
        files = [scale_file(id=int(x['id']), file_path=x['file_path']) for x in files]

        workspace = WorkspaceConfiguration(workspace_config)
        workspace.validate_broker()
        workspace_config = workspace.get_dict()
        broker = get_broker(workspace_config['broker']['type'])

        logger.info('Command starting: scale_delete_files')
        logger.info('File IDs: %s', [x.id for x in files])

        delete_files_job.delete_files(files=files, volume_path=workspace_config['broker']['host_path'],
                                      broker=broker)

        messages = create_delete_files_messages(files=files, purge=purge)
        CommandMessageManager().send_messages(messages)

        logger.info('Command completed: scale_delete_files')

        sys.exit(0)

    def _onsigterm(self, signum, _frame):
        """See signal callback registration: :py:func:`signal.signal`.

        This callback performs a clean shutdown when a TERM signal is received.
        """

        logger.info('Delete Files terminating due to receiving sigterm')
        sys.exit(1)
