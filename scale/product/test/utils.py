"""Defines utility methods for testing products"""


import hashlib

import django.utils.timezone as timezone

from job.test import utils as job_utils
from product.models import FileAncestryLink
from storage.models import ScaleFile
from storage.test import utils as storage_utils


def create_file_link(ancestor=None, descendant=None, job=None, job_exe=None, recipe=None, batch=None):
    """Creates a file ancestry link model for unit testing

    :returns: The file ancestry link model
    :rtype: :class:`product.models.FileAncestryLink`
    """

    if not job:
        if descendant and descendant.job:
            job = descendant.job
        else:
            job = job_utils.create_job()
    if not job_exe:
        if descendant and descendant.job_exe:
            job_exe = descendant.job_exe
        else:
            job_exe = job_utils.create_job_exe(job_type=job.job_type, job=job)

    return FileAncestryLink.objects.create(ancestor=ancestor, descendant=descendant, job=job, job_exe=job_exe,
                                           recipe=recipe, batch=batch)


def create_product(job_exe=None, workspace=None, has_been_published=False, is_published=False, uuid=None,
                   file_name='my_test_file.txt', file_path='/file/path/my_test_file.txt', media_type='text/plain',
                   file_size=100, countries=None, is_superseded=False, superseded=None):
    """Creates a product file model for unit testing

    :returns: The product model
    :rtype: :class:`storage.models.ScaleFile`
    """

    if not job_exe:
        job_exe = job_utils.create_job_exe()
    if not workspace:
        workspace = storage_utils.create_workspace()

    if not uuid:
        builder = hashlib.md5()
        builder.update(str(job_exe.job.job_type.id))
        builder.update(file_name)
        uuid = builder.hexdigest()

    if is_superseded and not superseded:
        superseded = timezone.now()

    product_file = ScaleFile.objects.create(file_type='PRODUCT', job_exe=job_exe, job=job_exe.job,
                                            job_type=job_exe.job.job_type, has_been_published=has_been_published,
                                            is_published=is_published, uuid=uuid, file_name=file_name,
                                            media_type=media_type, file_size=file_size, file_path=file_path,
                                            workspace=workspace, is_superseded=is_superseded, superseded=superseded)
    if countries:
        product_file.countries = countries
        product_file.save()
    return product_file
