"""Defines utility methods for testing jobs and job types"""
from __future__ import unicode_literals

import django.utils.timezone as timezone

import trigger.test.utils as trigger_test_utils
from job.configuration.data.exceptions import InvalidConnection
from job.configuration.json.execution.exe_config import ExecutionConfiguration
from job.models import Job, JobExecution, JobInputFile, JobType, JobTypeRevision, TaskUpdate
from job.tasks.update import TaskStatusUpdate
from job.triggers.configuration.trigger_rule import JobTriggerRuleConfiguration
from node.resources.node_resources import NodeResources
from node.test import utils as node_utils
import storage.test.utils as storage_test_utils
from trigger.handler import TriggerRuleHandler, register_trigger_rule_handler


JOB_TYPE_NAME_COUNTER = 1
JOB_TYPE_VERSION_COUNTER = 1
JOB_TYPE_CATEGORY_COUNTER = 1

RULE_EVENT_COUNTER = 1


MOCK_TYPE = 'MOCK_JOB_TRIGGER_RULE_TYPE'
MOCK_ERROR_TYPE = 'MOCK_JOB_TRIGGER_RULE_ERROR_TYPE'


class MockTriggerRuleConfiguration(JobTriggerRuleConfiguration):
    """Mock trigger rule configuration for testing
    """

    def __init__(self, trigger_rule_type, configuration):
        super(MockTriggerRuleConfiguration, self).__init__(trigger_rule_type, configuration)

    def validate(self):
        pass

    def validate_trigger_for_job(self, job_interface):
        return []


class MockErrorTriggerRuleConfiguration(JobTriggerRuleConfiguration):
    """Mock error trigger rule configuration for testing
    """

    def __init__(self, trigger_rule_type, configuration):
        super(MockErrorTriggerRuleConfiguration, self).__init__(trigger_rule_type, configuration)

    def validate(self):
        pass

    def validate_trigger_for_job(self, job_interface):
        raise InvalidConnection('Error!')


class MockTriggerRuleHandler(TriggerRuleHandler):
    """Mock trigger rule handler for testing
    """

    def __init__(self):
        super(MockTriggerRuleHandler, self).__init__(MOCK_TYPE)

    def create_configuration(self, config_dict):
        return MockTriggerRuleConfiguration(MOCK_TYPE, config_dict)


class MockErrorTriggerRuleHandler(TriggerRuleHandler):
    """Mock error trigger rule handler for testing
    """

    def __init__(self):
        super(MockErrorTriggerRuleHandler, self).__init__(MOCK_ERROR_TYPE)

    def create_configuration(self, config_dict):
        return MockErrorTriggerRuleConfiguration(MOCK_ERROR_TYPE, config_dict)


register_trigger_rule_handler(MockTriggerRuleHandler())
register_trigger_rule_handler(MockErrorTriggerRuleHandler())


def create_job(job_type=None, event=None, status='PENDING', error=None, data=None, num_exes=0, queued=None,
               started=None, ended=None, last_status_change=None, priority=100, results=None, superseded_job=None,
               delete_superseded=True, is_superseded=False, superseded=None):
    """Creates a job model for unit testing

    :returns: The job model
    :rtype: :class:`job.models.Job`
    """

    if not job_type:
        job_type = create_job_type()
    if not event:
        event = trigger_test_utils.create_trigger_event()
    if not last_status_change:
        last_status_change = timezone.now()
    if not data:
        data = {
            'version': '1.0',
            'input_data': [],
            'output_data': [],
        }
    if not results:
       results = dict() 
       
    if superseded_job and not superseded_job.is_superseded:
        Job.objects.supersede_jobs([superseded_job], timezone.now())
    if is_superseded and not superseded:
        superseded = timezone.now()

    job = Job.objects.create_job(job_type, event, superseded_job=superseded_job, delete_superseded=delete_superseded)
    job.priority = priority
    job.data = data
    job.status = status
    job.num_exes = num_exes
    job.queued = queued
    job.started = started
    job.ended = ended
    job.last_status_change = last_status_change
    job.error = error
    job.results = results
    job.is_superseded = is_superseded
    job.superseded = superseded
    job.save()
    return job


def create_job_exe(job_type=None, job=None, status='RUNNING', configuration=None, error=None,
                   command_arguments='test_arg', timeout=None, node=None, created=None, queued=None, started=None,
                   pre_started=None, pre_completed=None, job_started=None, job_completed=None, post_started=None,
                   post_completed=None, ended=None, last_modified=None, input_file_size=0.0, resources=None):
    """Creates a job execution model for unit testing

    :returns: The job execution model
    :rtype: :class:`job.models.JobExecution`
    """

    when = timezone.now()
    if not job:
        job = create_job(job_type=job_type)
    if not configuration:
        configuration = ExecutionConfiguration().get_dict()
    if not timeout:
        timeout = job.timeout
    if not node:
        node = node_utils.create_node()
    if not created:
        created = when
    if not queued:
        queued = when
    if not started:
        started = when
    if not last_modified:
        last_modified = when
    if not resources:
        resources = NodeResources()

    job_exe = JobExecution.objects.create(job=job, status=status, error=error, configuration=configuration,
                                          resources=resources.get_json().get_dict(), disk_in_scheduled=input_file_size,
                                          command_arguments=command_arguments, timeout=timeout, node=node,
                                          created=created, queued=queued, started=started, pre_started=pre_started,
                                          pre_completed=pre_completed, job_started=job_started,
                                          job_completed=job_completed, post_started=post_started,
                                          post_completed=post_completed, ended=ended, last_modified=last_modified)
    job_exe.set_cluster_id('1234')
    return job_exe


def create_job_type(name=None, version=None, category=None, interface=None, priority=50, timeout=3600, max_tries=3,
                    max_scheduled=None, cpus=1.0, mem=1.0, disk=1.0, error_mapping=None, is_active=True,
                    is_operational=True, trigger_rule=None, configuration=None):
    """Creates a job type model for unit testing

    :returns: The job type model
    :rtype: :class:`job.models.JobType`
    """

    if not name:
        global JOB_TYPE_NAME_COUNTER
        name = 'test-job-type-%i' % JOB_TYPE_NAME_COUNTER
        JOB_TYPE_NAME_COUNTER += 1

    if not version:
        global JOB_TYPE_VERSION_COUNTER
        version = '%i.0.0' % JOB_TYPE_VERSION_COUNTER
        JOB_TYPE_VERSION_COUNTER += 1

    if not category:
        global JOB_TYPE_CATEGORY_COUNTER
        category = 'test-category-%i' % JOB_TYPE_CATEGORY_COUNTER
        JOB_TYPE_CATEGORY_COUNTER += 1

    if not interface:
        interface = {
            'version': '1.4',
            'command': 'test_cmd',
            'command_arguments': 'test_arg',
            'env_vars': [],
            'mounts': [],
            'settings': [],
            'input_data': [],
            'output_data': [],
            'shared_resources': [],
        }
    if not error_mapping:
        error_mapping = {
            'version': '1.0',
            'exit_codes': {}
        }
    if not trigger_rule:
        trigger_rule = trigger_test_utils.create_trigger_rule()

    if not configuration:
        configuration = {
            'version': '1.0',
            'default_settings': {}
        }

    job_type = JobType.objects.create(name=name, version=version, category=category, interface=interface,
                                      priority=priority, timeout=timeout, max_tries=max_tries,
                                      max_scheduled=max_scheduled, cpus_required=cpus, mem_const_required=mem,
                                      disk_out_const_required=disk, error_mapping=error_mapping, is_active=is_active,
                                      is_operational=is_operational, trigger_rule=trigger_rule, configuration=configuration)
    JobTypeRevision.objects.create_job_type_revision(job_type)
    return job_type


def create_clock_rule(name=None, rule_type='CLOCK', event_type=None, schedule='PT1H0M0S', is_active=True):
    """Creates a scale clock trigger rule model for unit testing

    :returns: The trigger rule model
    :rtype: :class:`trigger.models.TriggerRule`
    """

    if not event_type:
        global RULE_EVENT_COUNTER
        event_type = 'TEST_EVENT_%i' % RULE_EVENT_COUNTER
        RULE_EVENT_COUNTER += 1

    config = {
        'version': '1.0',
        'event_type': event_type,
        'schedule': schedule,
    }

    return trigger_test_utils.create_trigger_rule(name=name, trigger_type=rule_type, configuration=config,
                                                  is_active=is_active)


def create_clock_event(rule=None, occurred=None):
    """Creates a scale clock trigger event model for unit testing

    :returns: The trigger event model
    :rtype: :class:`trigger.models.TriggerEvent`
    """

    if not rule:
        rule = create_clock_rule()

    if not occurred:
        occurred = timezone.now()

    event_type = None
    if rule.configuration and 'event_type' in rule.configuration:
        event_type = rule.configuration['event_type']

    return trigger_test_utils.create_trigger_event(trigger_type=event_type, rule=rule, occurred=occurred)


def create_task_status_update(task_id, agent_id, status, when, exit_code=None, reason=None, source=None, message=None,
                              data=None):
    """Creates a job model for unit testing

    :param task_id: The unique ID of the task
    :type task_id: string
    :param agent_id: The agent ID for the task
    :type agent_id: string
    :param status: The status of the task
    :type status: string
    :param when: The timestamp of the update
    :type when: :class:`datetime.datetime`
    :param exit_code: The task's exit code
    :type exit_code: int
    :param reason: The reason
    :type reason: string
    :param source: The source
    :type source: string
    :param message: The message
    :type message: string
    :param data: The data dict
    :type data: dict
    :returns: The task status update
    :rtype: :class:`job.tasks.update.TaskStatusUpdate`
    """

    if data is None:
        data = {}

    task_update_model = TaskUpdate()
    task_update_model.task_id = task_id
    task_update_model.timestamp = when
    task_update_model.message = message
    task_update_model.source = source
    task_update_model.reason = reason
    update = TaskStatusUpdate(task_update_model, agent_id, data)
    update.status = status
    if exit_code:
        update.exit_code = exit_code
    return update

def create_input_file(job=None, input_file=None, job_input=None, file_name='my_test_file.txt', media_type='text/plain',
                      file_size=100, file_path=None, workspace=None, countries=None, is_deleted=False, data_type='', 
                      last_modified=None, source_started=None, source_ended=None):
    """Creates a Scale file and job input file model for unit testing

    :returns: The file model
    :rtype: :class:`storage.models.ScaleFile`
    """

    if not job: 
        job = create_job()
    if not input_file:
        input_file = 'some_input'
    if not input_file:
        input_file = storage_test_utils.create_file(file_name=file_name, media_type=media_type, file_size=file_size, 
                                                    file_path=file_path, workspace=workspace, countries=countries, 
                                                    is_deleted=is_deleted, data_type=data_type, 
                                                    last_modified=last_modified, source_started=source_started, 
                                                    source_ended=source_ended)

    job_input_file = JobInputFile.objects.create(job=job, input_file=input_file, job_input=job_input)

    return input_file