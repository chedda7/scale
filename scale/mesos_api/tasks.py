"""Defines the functions for generating Mesos tasks"""


import logging
from mesos.interface import mesos_pb2
from django.conf import settings


logger = logging.getLogger(__name__)


def create_mesos_task(task):
    """Creates and returns a Mesos task from a Scale task

    :param task: The task
    :type task: :class:`job.tasks.base_task.Task`
    :returns: The Mesos task
    :rtype: :class:`mesos_pb2.TaskInfo`
    """

    if task.uses_docker:
        return _create_docker_task(task)

    return _create_command_task(task)


def _create_base_task(task):
    """Creates and returns a base Mesos task from a Scale task

    :param task: The task
    :type task: :class:`job.tasks.base_task.Task`
    :returns: The base Mesos task
    :rtype: :class:`mesos_pb2.TaskInfo`
    """

    mesos_task = mesos_pb2.TaskInfo()
    mesos_task.task_id.value = task.id
    mesos_task.slave_id.value = task.agent_id
    mesos_task.name = task.name
    resources = task.get_resources()

    if settings.CONFIG_URI:
        mesos_task.command.uris.add().value = settings.CONFIG_URI

    for resource in resources.resources:
        if resource.value > 0.0:
            task_resource = mesos_task.resources.add()
            task_resource.name = resource.name
            task_resource.type = mesos_pb2.Value.SCALAR
            task_resource.scalar.value = resource.value

    return mesos_task


def _create_command_task(task):
    """Creates and returns a command-line Mesos task from a Scale task

    :param task: The task
    :type task: :class:`job.tasks.base_task.Task`
    :returns: The command-line Mesos task
    :rtype: :class:`mesos_pb2.TaskInfo`
    """

    mesos_task = _create_base_task(task)
    command = task.command if task.command else 'echo'
    if task.command_arguments:
        command += ' ' + task.command_arguments
    mesos_task.command.value = command

    return mesos_task


def _create_docker_task(task):
    """Creates and returns a Dockerized Mesos task from a Scale task

    :param task: The task
    :type task: :class:`job.tasks.base_task.Task`
    returns: The Dockerized Mesos task
    rtype: :class:`mesos_pb2.TaskInfo`
    """

    mesos_task = _create_base_task(task)
    mesos_task.container.type = mesos_pb2.ContainerInfo.DOCKER
    mesos_task.container.docker.image = task.docker_image
    for param in task.docker_params:
        mesos_task.container.docker.parameters.add(key=param.flag, value=param.value)
    if task.is_docker_privileged:
        mesos_task.container.docker.privileged = True

    # Use Docker image entrypoint
    mesos_task.command.shell = False

    arguments = task.command_arguments.split(" ")
    for argument in arguments:
        mesos_task.command.arguments.append(argument)

    mesos_task.container.docker.network = mesos_pb2.ContainerInfo.DockerInfo.Network.Value('BRIDGE')
    mesos_task.container.docker.force_pull_image = False

    return mesos_task
