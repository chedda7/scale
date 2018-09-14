"""Defines the methods for handling file systems in the container's local volume"""


import os


SCALE_ROOT_PATH = '/scale'
SCALE_ROOT_WORKSPACE_VOLUME_PATH = os.path.join(SCALE_ROOT_PATH, 'workspace_mounts')


def get_workspace_volume_path(name):
    """Returns the absolute local path within the container onto which this workspace broker's container volume is
    mounted

    :param name: The name of the workspace
    :type name: string
    :returns: The absolute local path of the workspace's mount
    :rtype: string
    """

    return os.path.join(SCALE_ROOT_WORKSPACE_VOLUME_PATH, name)
