"""Defines the configuration for a storage Workspace"""


from jsonschema import validate
from jsonschema.exceptions import ValidationError

import storage.brokers.factory as broker_factory
from storage.configuration.exceptions import InvalidWorkspaceConfiguration

DEFAULT_VERSION = '1.0'

WORKSPACE_CONFIGURATION_SCHEMA = {
    'type': 'object',
    'required': ['broker'],
    'additionalProperties': False,
    'properties': {
        'version': {
            'description': 'Version of the Workspace configuration schema',
            'type': 'string',
            'pattern': '^.{0,50}$',
        },
        'broker': {
            'type': 'object',
            'required': ['type'],
            'additionalProperties': True,
            'properties': {
                'type': {
                    'type': 'string',
                    'enum': ['host', 'nfs', 's3'],
                },
            },
        },
    },
}


class ValidationWarning(object):
    """Tracks workspace configuration warnings during validation that may not prevent the workspace from working."""

    def __init__(self, key, details):
        """Constructor sets basic attributes.

        :param key: A unique identifier clients can use to recognize the warning.
        :type key: string
        :param details: A user-friendly description of the problem, including field names and/or associated values.
        :type details: string
        """
        self.key = key
        self.details = details


class WorkspaceConfiguration(object):
    """Represents the configuration for a storage Workspace.
    The configuration includes details about the storage broker system required to read, write, move, or delete files
    within the workspace.
    """

    def __init__(self, configuration):
        """Creates a Workspace configuration object from the given dictionary.

        The general format is checked for correctness, but the specified broker is not checked. Use the validate_broker
        method to perform the additional checks.

        :param configuration: The Workspace configuration
        :type configuration: dict

        :raises :class:`storage.configuration.exceptions.InvalidWorkspaceConfiguration`: If there is a configuration
            problem.
        """

        self._configuration = configuration

        # Valid the overall JSON schema
        try:
            validate(configuration, WORKSPACE_CONFIGURATION_SCHEMA)
        except ValidationError as ex:
            raise InvalidWorkspaceConfiguration('Invalid Workspace configuration: %s' % str(ex))

        self._populate_default_values()
        if not self._configuration['version'] == '1.0':
            msg = 'Invalid Workspace configuration: %s is an unsupported version number'
            raise InvalidWorkspaceConfiguration(msg % self._configuration['version'])

    def get_dict(self):
        """Returns the internal dictionary that represents this workspace configuration.

        :returns: The internal dictionary
        :rtype: dict
        """

        return self._configuration

    def validate_broker(self):
        """Validates the current broker-specific configuration.

        :returns: A list of warnings discovered during validation.
        :rtype: list[:class:`job.configuration.data.job_data.ValidationWarning`]

        :raises :class:`storage.configuration.exceptions.InvalidWorkspaceConfiguration`: If there is a configuration
            problem.
        """

        broker = broker_factory.get_broker(self._configuration['broker']['type'])
        return broker.validate_configuration(self._configuration['broker'])

    def _populate_default_values(self):
        """Goes through the configuration and populates any missing values with defaults."""

        if 'version' not in self._configuration:
            self._configuration['version'] = DEFAULT_VERSION
