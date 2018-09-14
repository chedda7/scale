"""Defines the JSON schema for a job configuration"""


import logging

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from job.configuration.exceptions import InvalidJobConfiguration

logger = logging.getLogger(__name__)

JOB_CONFIG_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'version': {
            'description': 'Version of the job configuration schema',
            'type': 'string',
            'pattern': '^.{0,50}$',
        },
        'default_settings': {
            'type': 'object',
            'item': {
                'type': 'string',
            },
        },
    },
}


class JobConfigurationV1(object):
    """Represents the schema for a job configuration"""

    def __init__(self, definition=None):
        """Creates a configuration interface from the given definition.

        If the definition is invalid, a :class:`job.configuration.interface.exceptions.InvalidInterfaceDefinition`
        exception will be thrown.

        :param definition: The interface definition
        :type definition: dict
        """
        if definition is None:
            definition = {}

        self.definition = definition

        self._default_setting_names = set()

        try:
            validate(definition, JOB_CONFIG_SCHEMA)
        except ValidationError as validation_error:
            raise InvalidJobConfiguration('INVALID_CONFIGURATION', validation_error)

        self._populate_default_values()
        self._validate_default_settings()

        if self.definition['version'] != '1.0':
            msg = '%s is an unsupported version number'
            raise InvalidJobConfiguration('INVALID_VERSION', msg % self.definition['version'])

    def get_dict(self):
        """Returns the internal dictionary that represents this error mapping

        :returns: The internal dictionary
        :rtype: dict
        """

        return self.definition

    def _validate_default_settings(self):
        """Ensures that no settings have duplicate names or blank values

        :raises :class:`job.configuration.interface.exceptions.InvalidInterface`: If there is a duplicate name or blank
            value/name.
        """

        for setting_name, setting_value in self.definition['default_settings'].items():
            if setting_name in self._default_setting_names:
                msg = 'Duplicate setting name %s in default_settings'
                raise InvalidJobConfiguration('INVALID_CONFIGURATION', msg % setting_name)
            self._default_setting_names.add(setting_name)

            if not setting_name:
                msg = 'Blank setting name (value = %s) in default_settings'
                raise InvalidJobConfiguration('INVALID_CONFIGURATION', msg % setting_value)

            if not setting_value:
                msg = 'Blank setting value (name = %s) in default_settings'
                raise InvalidJobConfiguration('INVALID_CONFIGURATION', msg % setting_name)

            if not isinstance(setting_value, str):
                msg = 'Setting value (name = %s) is not a string'
                raise InvalidJobConfiguration('INVALID_CONFIGURATION', msg % setting_name)

    def _populate_default_values(self):
        """Goes through the definition and fills in any missing default values"""
        if 'version' not in self.definition:
            self.definition['version'] = '1.0'
        if 'default_settings' not in self.definition:
            self.definition['default_settings'] = {}
