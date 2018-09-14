"""Defines the command line method for downloading a file"""


import logging
import os
import sys

from django.core.management.base import BaseCommand

from storage.brokers.broker import FileDownload
from storage.models import ScaleFile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command that downloads a stored file to the local file system."""

    help = 'Downloads a stored file to the local file system'
    
    def add_arguments(self, parser):
        parser.add_argument('file_id', type=int,
                            help='ID of the ScaleFile object to delete.')
        parser.add_argument('local_path', help='Local file name to download to.')

    def handle(self, *args, **options):
        """See :meth:`django.core.management.base.BaseCommand.handle`.

        This method starts the file download process.
        """

        logger.info('Command starting: scale_download_file')
        
        file_id = options.get('file_id')
        local_path = options.get('local_path')

        # Validate the file paths
        if os.path.exists(local_path):
            logger.exception('Local file already exists: %s', local_path)
            sys.exit(1)

        # Attempt to fetch the file model
        try:
            scale_file = ScaleFile.objects.get(pk=file_id)
        except ScaleFile.DoesNotExist:
            logger.exception('Stored file does not exist: %s', file_id)
            sys.exit(1)

        try:
            ScaleFile.objects.download_files([FileDownload(scale_file, local_path)])
        except:
            logger.exception('Unknown error occurred, exit code 1 returning')
            sys.exit(1)
        logger.info('Command completed: scale_download_file')
