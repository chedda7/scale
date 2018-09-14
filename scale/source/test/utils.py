"""Defines utility methods for testing source files"""


import hashlib

import django.utils.timezone as timezone

from storage.models import ScaleFile
from storage.test import utils as storage_utils


def create_source(file_name='my_test_file.txt', file_size=100, media_type='text/plain',
                  file_path='/file/path/my_test_file.txt', data_started=None, data_ended=None, is_parsed=True,
                  parsed=None, workspace=None, countries=None):
    """Creates a source file model for unit testing

    :returns: The source file model
    :rtype: :class:`storage.models.ScaleFile`
    """

    if not data_started:
        data_started = timezone.now()
    if not data_ended:
        data_ended = data_started
    if not parsed and is_parsed:
        parsed = timezone.now()
    if not workspace:
        workspace = storage_utils.create_workspace()

    source_file = ScaleFile.objects.create(file_name=file_name, file_type='SOURCE', media_type=media_type,
                                           file_size=file_size, file_path=file_path, data_started=data_started,
                                           data_ended=data_ended, is_parsed=is_parsed, parsed=parsed,
                                           workspace=workspace, uuid=hashlib.md5(file_name).hexdigest())
    if countries:
        source_file.countries = countries
        source_file.save()
    return source_file
