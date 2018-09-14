

import logging

import django.contrib.postgres.fields
import mesos_api.api as mesos_api
from django.db import models, transaction
from mesos_api.api import MesosError

from queue.models import Queue, QUEUE_ORDER_FIFO, QUEUE_ORDER_LIFO

logger = logging.getLogger(__name__)

class SchedulerManager(models.Manager):
    """Provides additional methods for handling scheduler db entry
    """

    def get_master(self):
        """Gets the current master scheduler instance for the cluster.

        :returns: The master scheduler.
        :rtype: :class:`scheduler.models.Scheduler`
        """
        try:
            return Scheduler.objects.all().defer('status').get(pk=1)
        except Scheduler.DoesNotExist:
            logger.exception('Initial database import missing master scheduler: 1')
            raise

    def initialize_scheduler(self):
        """Initializes the scheduler table by creating a model if one does not already exist
        """

        if self.all().count() == 0:
            logger.info('Creating initial scheduler model in database')
            scheduler = Scheduler()
            scheduler.save()

    def is_master_active(self):
        """Checks whether the current master scheduler is ready to schedule.

        :returns: True if the master scheduler is not registered or not paused.
        :rtype: bool
        """
        scheduler = None
        try:
            scheduler = Scheduler.objects.get(pk=1)
            return not scheduler.is_paused
        except Scheduler.DoesNotExist:
            logger.warning('Unable to check master scheduler status.')
            pass
        return True

    def update_scheduler(self, new_data):
        """Update the data for the scheduler.

        :param new_data: Updated data for the node
        :type new_data: dict
        """

        self.all().update(**new_data)

    def update_master(self, hostname, port):
        """Update mesos master information.

        :param hostname: Hostname for the master
        :type hostname: str
        :param port: Port for the mesos master RESTful API
        :type port: int
        """

        self.all().update(master_hostname=hostname, master_port=port)

    def get_status(self):
        """Fetch summary hardware resource usage for the scheduler framework.

        :returns: Node resource usage information.
        :rtype: dict
        """
        master_dict = {
            'is_online': False,
            'hostname': None,
            'port': 0,
        }
        sched_dict = {
            'is_online': False,
            'is_paused': False,
            'hostname': None,
            'system_logging_level':'INFO'
        }
        res_dict = None

        try:
            # Set the master info
            sched = self.get_master()
            master_dict['hostname'] = sched.master_hostname
            master_dict['port'] = sched.master_port

            # Set the scheduler framework info
            sched_info = mesos_api.get_scheduler(sched.master_hostname, sched.master_port)
            sched_dict['is_online'] = sched_info.is_online
            sched_dict['is_paused'] = sched.is_paused  # Note this must be pulled from the database
            sched_dict['hostname'] = sched_info.hostname
            sched_dict['system_logging_level'] = sched.system_logging_level

            # Master is online if the API above succeeded
            master_dict['is_online'] = True

            # Set the cluster resource info
            res_dict = sched_info.to_dict()['resources']
        except Scheduler.DoesNotExist:
            logger.exception('Unable to find master scheduler')
        except MesosError:
            logger.exception('Failed to query master info')

        status_dict = {
            'master': master_dict,
            'scheduler': sched_dict,
            'queue_depth': Queue.objects.all().count(),
        }
        if res_dict:
            status_dict['resources'] = res_dict
        return status_dict


# TODO: remove master_hostname and master_port fields when REST API v4 is removed
class Scheduler(models.Model):
    """Represents a scheduler instance. There should only be a single instance of this and it's used for storing
    cluster-wide state related to scheduling in mesos.

    :keyword is_paused: True if the entire cluster is currently paused and should not accept new jobs
    :type is_paused: :class:`django.db.models.BooleanField()`
    :keyword num_message_handlers: The number of message handlers to have scheduled 
    :type num_message_handlers: :class:`django.db.models.IntegerField`
    :keyword system_logging_level: The logging level for all scale system components
    :type system_logging_level: :class:`django.db.models.CharField`
    :keyword master_hostname: The full domain-qualified hostname of the Mesos master
    :type master_hostname: :class:`django.db.models.CharField`
    :keyword master_port: The port being used by the Mesos master REST API
    :type master_port: :class:`django.db.models.IntegerField`
    """

    QUEUE_MODES = (
        (QUEUE_ORDER_FIFO, QUEUE_ORDER_FIFO),
        (QUEUE_ORDER_LIFO, QUEUE_ORDER_LIFO),
    )

    is_paused = models.BooleanField(default=False)
    num_message_handlers = models.IntegerField(default=1)
    queue_mode = models.CharField(choices=QUEUE_MODES, default=QUEUE_ORDER_FIFO, max_length=50)
    status = django.contrib.postgres.fields.JSONField(default=dict)
    master_hostname = models.CharField(max_length=250, default='localhost')
    master_port = models.IntegerField(default=5050)
    system_logging_level = models.CharField(max_length=10, default='INFO')

    objects = SchedulerManager()

    class Meta(object):
        """meta information for the db"""
        db_table = 'scheduler'
