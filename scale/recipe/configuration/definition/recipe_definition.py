"""Defines the class for managing a recipe definition"""
from __future__ import unicode_literals

from django.db.models import Q
from job.configuration.data.exceptions import InvalidConnection
from job.configuration.data.job_connection import JobConnection
from job.configuration.interface.scale_file import ScaleFileDescription
from job.data.job_connection import SeedJobConnection
from job.deprecation import JobConnectionSunset
from job.handlers.inputs.file import FileInput
from job.handlers.inputs.files import FilesInput
from job.handlers.inputs.property import PropertyInput
from job.models import JobType
from job.seed.manifest import SeedManifest
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from recipe.configuration.data.exceptions import InvalidRecipeConnection
from recipe.configuration.definition.exceptions import InvalidDefinition
from recipe.handlers.graph import RecipeGraph


DEFAULT_VERSION = '1.0'


RECIPE_DEFINITION_SCHEMA = {
    'type': 'object',
    'required': [
        'jobs',
    ],
    'additionalProperties': False,
    'properties': {
        'version': {
            'description': 'Version of the recipe definition schema',
            'type': 'string',
            'pattern': '^.{0,50}$',
        },
        'input_data': {
            'type': 'array',
            'items': {
                '$ref': '#/definitions/input_data_item',
            },
        },
        'jobs': {
            'type': 'array',
            'items': {
                '$ref': '#/definitions/job_item',
            },
        },
    },
    'definitions': {
        'input_data_item': {
            'type': 'object',
            'required': [
                'name', 'type',
            ],
            'additionalProperties': False,
            'properties': {
                'name': {
                    'type': 'string',
                    'pattern': '^[a-zA-Z0-9\\-_ ]{0,255}$',
                },
                'type': {
                    'type': 'string',
                    'enum': [
                        'file', 'files', 'property',
                    ],
                },
                'required': {
                    'type': 'boolean',
                },
                'media_types': {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                    },
                },
            },
        },

        'job_item': {
            'type': 'object',
            'required': [
                'name',
                'job_type',
            ],
            'additionalProperties': False,
            'properties': {
                'name': {
                    'type': 'string',
                    'pattern': '^[a-zA-Z0-9\\-_ ]{1,255}$',
                },
                'job_type': {
                    'type': 'object',
                    'required': [
                        'name', 'version',
                    ],
                    'additionalProperties': False,
                    'properties': {
                        'name': {
                            'type': 'string',
                            'pattern': '^[a-zA-Z0-9\\-_ ]{1,255}$',
                        },
                        'version': {
                            'type': 'string',
                        },
                    },
                },
                'recipe_inputs': {
                    'type': 'array',
                    'items': {
                        '$ref': '#/definitions/recipe_input_item',
                    },
                },
                'dependencies': {
                    'type': 'array',
                    'items': {
                        '$ref': '#/definitions/dependency_item',
                    },
                },
            },
        },
        'recipe_input_item': {
            'type': 'object',
            'required': [
                'recipe_input', 'job_input',
            ],
            'additionalProperties': False,
            'properties': {
                'recipe_input': {
                    'type': 'string',
                },
                'job_input': {
                    'type': 'string',
                },
            },
        },
        'dependency_item': {
            'type': 'object',
            'required': [
                'name',
            ],
            'additionalProperties': False,
            'properties': {
                'name': {
                    'type': 'string',
                },
                'connections': {
                    'type': 'array',
                    'items': {
                        '$ref': '#/definitions/connection_item',
                    },
                },
            },
        },
        'connection_item': {
            'type': 'object',
            'required': [
                'output', 'input',
            ],
            'additionalProperties': False,
            'properties': {
                'output': {
                    'type': 'string',
                },
                'input': {
                    'type': 'string',
                },
            },
        },
    },
}


class LegacyRecipeDefinition(object):
    """Represents the definition for a recipe. The definition includes the recipe inputs, the jobs that make up the
    recipe, and how the inputs and outputs of those jobs are connected together.
    """

    def __init__(self, definition):
        """Creates a recipe definition object from the given dictionary. The general format is checked for correctness,
        but the actual job details are not checked for correctness.

        :param definition: The recipe definition
        :type definition: dict

        :raises InvalidDefinition: If the given definition is invalid
        """

        self._definition = definition
        self._inputs_by_name = {}  # Name -> input data dict
        self._jobs_by_name = {}  # Name -> job dict
        self._property_validation_dict = {}  # Property Input name -> required
        self._input_file_validation_dict = {}  # File Input name -> (required, multiple, file description)

        try:
            validate(definition, RECIPE_DEFINITION_SCHEMA)
        except ValidationError as ex:
            raise InvalidDefinition('Invalid recipe definition: %s' % unicode(ex))

        self._populate_default_values()
        if not self._definition['version'] == '1.0':
            raise InvalidDefinition('%s is an unsupported version number' % self._definition['version'])

        for input_dict in self._definition['input_data']:
            name = input_dict['name']
            if name in self._inputs_by_name:
                raise InvalidDefinition('Invalid recipe definition: %s is a duplicate input data name' % name)
            self._inputs_by_name[name] = input_dict
        for job_dict in self._definition['jobs']:
            name = job_dict['name']
            if name in self._jobs_by_name:
                raise InvalidDefinition('Invalid recipe definition: %s is a duplicate job name' % name)
            self._jobs_by_name[name] = job_dict

        self._create_validation_dicts()
        self._validate_job_dependencies()
        self._validate_no_dup_job_inputs()
        self._validate_recipe_inputs()

    def get_dict(self):
        """Returns the internal dictionary that represents this recipe definition

        :returns: The internal dictionary
        :rtype: dict
        """

        return self._definition

    def get_graph(self):
        """Returns the recipe graph for this definition

        :returns: The recipe graph
        :rtype: :class:`recipe.handlers.graph.RecipeGraph`
        """

        graph = RecipeGraph()
        for input_name in self._inputs_by_name:
            input_dict = self._inputs_by_name[input_name]
            input_type = input_dict['type']
            required = input_dict['required']
            recipe_input = None
            if input_type == 'property':
                recipe_input = PropertyInput(input_name, required)
            elif input_type == 'file':
                recipe_input = FileInput(input_name, required)
            elif input_type == 'files':
                recipe_input = FilesInput(input_name, required)
            graph.add_input(recipe_input)

        for job_name in self._jobs_by_name:
            job_dict = self._jobs_by_name[job_name]
            job_type = job_dict['job_type']
            job_type_name = job_type['name']
            job_type_version = job_type['version']
            graph.add_job(job_name, job_type_name, job_type_version)
            for recipe_input_dict in job_dict['recipe_inputs']:
                recipe_input_name = recipe_input_dict['recipe_input']
                job_input_name = recipe_input_dict['job_input']
                graph.add_recipe_input_connection(recipe_input_name, job_name, job_input_name)

        for job_name in self._jobs_by_name:
            job_dict = self._jobs_by_name[job_name]
            for dependency_dict in job_dict['dependencies']:
                dependency_name = dependency_dict['name']
                dependency_connections = []
                for conn_dict in dependency_dict['connections']:
                    conn_input = conn_dict['input']
                    job_output = conn_dict['output']
                    dependency_connections.append((job_output, conn_input))
                graph.add_dependency(dependency_name, job_name, dependency_connections)

        return graph

    def get_job_types(self, lock=False):
        """Returns a set of job types for each job in the recipe

        :param lock: Whether to obtain select_for_update() locks on the job type models
        :type lock: bool
        :returns: Set of referenced job types
        :rtype: set[:class:`job.models.JobType`]
        """

        filters = []
        for job_type_key in self.get_job_type_keys():
            job_type_filter = Q(name=job_type_key[0], version=job_type_key[1])
            filters = filters | job_type_filter if filters else job_type_filter
        if filters:
            job_type_query = JobType.objects.all()
            if lock:
                job_type_query = job_type_query.select_for_update().order_by('id')
            return {job_type for job_type in job_type_query.filter(filters)}
        return set()

    def get_job_type_keys(self):
        """Returns a set of tuples that represent keys for each job in the recipe

        :returns: Set of referenced job types as a tuple of (name, version)
        :rtype: set[(str, str)]
        """
        job_type_keys = set()
        for job_dict in self._jobs_by_name.itervalues():
            if 'job_type' in job_dict:
                job_type = job_dict['job_type']
                if 'name' in job_type and 'version' in job_type:
                    job_type_keys.add((job_type['name'], job_type['version']))
        return job_type_keys

    def get_job_type_map(self):
        """Returns a mapping of job name to job type for each job in the recipe

        :returns: Dictionary with the recipe job name of each job mapping to its job type
        :rtype: dict of str -> :class:`job.models.JobType`
        """
        results = {}
        job_types = self.get_job_types()
        job_type_map = {(job_type.name, job_type.version): job_type for job_type in job_types}
        for job_name, job_dict in self._jobs_by_name.iteritems():
            if 'job_type' in job_dict:
                job_type = job_dict['job_type']
                if 'name' in job_type and 'version' in job_type:
                    job_type_key = (job_type['name'], job_type['version'])
                    if job_type_key in job_type_map:
                        results[job_name] = job_type_map[job_type_key]

        return results

    def get_jobs_to_create(self):
        """Returns the list of job names and types to create for the recipe, in the order that they should be created

        :returns: List of tuples with each job's name and type
        :rtype: [(str, :class:`job.models.JobType`)]
        """

        results = []
        job_type_map = self.get_job_type_map()
        ordering = self.get_graph().get_topological_order()
        for job_name in ordering:
            job_tuple = (job_name, job_type_map[job_name])
            results.append(job_tuple)
        return results

    def validate_connection(self, recipe_conn):
        """Validates the given recipe connection to ensure that the connection will provide sufficient data to run a
        recipe with this definition

        :param recipe_conn: The recipe definition
        :type recipe_conn: :class:`recipe.configuration.data.recipe_connection.LegacyRecipeConnection`
        :returns: A list of warnings discovered during validation
        :rtype: list[:class:`recipe.configuration.data.recipe_data.ValidationWarning`]

        :raises :class:`recipe.configuration.data.exceptions.InvalidRecipeConnection`: If there is a configuration
            problem
        """

        warnings = []
        warnings.extend(recipe_conn.validate_input_files(self._input_file_validation_dict))
        warnings.extend(recipe_conn.validate_properties(self._property_validation_dict))

        # Check all recipe jobs for any file outputs
        file_outputs = False
        for job_type in self.get_job_types():
            if job_type.get_job_interface().get_file_output_names():
                file_outputs = True
                break

        # Make sure connection has a workspace if the recipe has any output files
        if file_outputs and not recipe_conn.has_workspace():
            raise InvalidRecipeConnection('No workspace provided for output files')
        return warnings

    def validate_data(self, recipe_data):
        """Validates the given data against the recipe definition

        :param recipe_data: The recipe data
        :type recipe_data: :class:`recipe.configuration.data.recipe_data.LegacyRecipeData`
        :returns: A list of warnings discovered during validation.
        :rtype: list[:class:`recipe.configuration.data.recipe_data.ValidationWarning`]

        :raises :class:`recipe.configuration.data.exceptions.InvalidRecipeData`: If there is a configuration problem
        """

        warnings = []
        warnings.extend(recipe_data.validate_input_files(self._input_file_validation_dict))
        warnings.extend(recipe_data.validate_properties(self._property_validation_dict))

        # Check all recipe jobs for any file outputs
        file_outputs = False
        for job_type in self.get_job_types():
            if job_type.get_job_interface().get_file_output_names():
                file_outputs = True
                break

        # If there is at least one file output, we must have a workspace to store the output(s)
        if file_outputs:
            warnings.extend(recipe_data.validate_workspace())
        return warnings

    def validate_job_interfaces(self):
        """Validates the interfaces of the recipe jobs in the definition to ensure that all of the input and output
        connections are valid

        :returns: A list of warnings discovered during validation.
        :rtype: list[:class:`job.configuration.data.job_data.ValidationWarning`]

        :raises :class:`recipe.configuration.definition.exceptions.InvalidDefinition`:
            If there are any invalid job connections in the definition
        """

        # Query for job types
        job_types_by_name = self.get_job_type_map()  # Job name in recipe -> job type model
        for job_name, job_data in self._jobs_by_name.iteritems():
            if job_name not in job_types_by_name:
                if 'job_type' in job_data:
                    job_type = job_data['job_type']
                    if 'name' in job_type and 'version' in job_type:
                        raise InvalidDefinition('Unknown job type: (%s, %s)' % (job_type['name'], job_type['version']))
                    else:
                        raise InvalidDefinition('Missing job type name or version: %s' % job_name)
                else:
                    raise InvalidDefinition('Missing job type declaration: %s' % job_name)

        warnings = []
        for job_name in self._jobs_by_name:
            job_dict = self._jobs_by_name[job_name]
            warnings.extend(self._validate_job_interface(job_dict, job_types_by_name))
        return warnings

    def _add_recipe_inputs_to_conn(self, job_conn, recipe_inputs):
        """Populates the given connection for a job with its recipe inputs

        :param job_conn: The job's connection
        :type job_conn: :class:`job.configuration.data.job_connection.JobConnection`
        :param recipe_inputs: List of recipe inputs used for the job
        :type recipe_inputs: list of dict
        """

        for recipe_dict in recipe_inputs:
            recipe_input = recipe_dict['recipe_input']
            job_input = recipe_dict['job_input']
            input_data_dict = self._inputs_by_name[recipe_input]
            input_data_type = input_data_dict['type']
            if input_data_type == 'property':
                job_conn.add_property(job_input)
            elif input_data_type in ['file', 'files']:
                multiple = (input_data_type == 'files')
                media_types = input_data_dict['media_types']
                optional = not input_data_dict['required']
                job_conn.add_input_file(job_input, multiple, media_types, optional, False)

    def _create_validation_dicts(self):
        """Creates the validation dicts required by recipe_data to perform its validation"""

        for input_data in self._definition['input_data']:
            name = input_data['name']
            required = input_data['required']
            if input_data['type'] == 'property':
                self._property_validation_dict[name] = required
            elif input_data['type'] == 'file':
                file_desc = ScaleFileDescription()
                if 'media_types' in input_data:
                    for media_type in input_data['media_types']:
                        file_desc.add_allowed_media_type(media_type)
                self._input_file_validation_dict[name] = (required, False, file_desc)
            elif input_data['type'] == 'files':
                file_desc = ScaleFileDescription()
                if 'media_types' in input_data:
                    for media_type in input_data['media_types']:
                        file_desc.add_allowed_media_type(media_type)
                self._input_file_validation_dict[name] = (required, True, file_desc)

    def _populate_default_values(self):
        """Goes through the definition and populates any missing values with defaults
        """

        if not 'version' in self._definition:
            self._definition['version'] = DEFAULT_VERSION

        if not 'input_data' in self._definition:
            self._definition['input_data'] = []
        for input_dict in self._definition['input_data']:
            if not 'required' in input_dict:
                input_dict['required'] = True

        for job_dict in self._definition['jobs']:
            if not 'recipe_inputs' in job_dict:
                job_dict['recipe_inputs'] = []
            if not 'dependencies' in job_dict:
                job_dict['dependencies'] = []
            for dependency_dict in job_dict['dependencies']:
                if not 'connections' in dependency_dict:
                    dependency_dict['connections'] = []

    def _validate_job_interface(self, job_dict, job_types_by_name):
        """Validates the input connections for the given job in the recipe definition

        :param job_dict: The job dictionary
        :type job_dict: dict
        :param job_types_by_name: Dict mapping all job names in the recipe to their job type models
        :type job_types_by_name: dict
        :returns: A list of warnings discovered during validation.
        :rtype: list[:class:`job.configuration.data.job_data.ValidationWarning`]

        :raises :class:`recipe.configuration.definition.exceptions.InvalidDefinition`:
            If there are any invalid job connections in the definition
        """

        job_type = job_types_by_name[job_dict['name']]

        # Job connection will represent data to be passed to the job to validate
        job_conn = JobConnectionSunset.create(job_type.get_job_interface())
        # Assume a workspace is provided, this will be verified when validating the recipe data
        job_conn.add_workspace()

        # Populate connection with data that will come from recipe inputs
        self._add_recipe_inputs_to_conn(job_conn, job_dict['recipe_inputs'])

        # Populate connection with data that will come from job dependencies
        warnings = []
        for dependency_dict in job_dict['dependencies']:
            dependency_name = dependency_dict['name']
            job_type = job_types_by_name[dependency_name]
            for conn_dict in dependency_dict['connections']:
                conn_input = conn_dict['input']
                job_output = conn_dict['output']
                job_type.get_job_interface().add_output_to_connection(job_output, job_conn, conn_input)

        job_type = job_types_by_name[job_dict['name']]
        try:
            warnings.extend(job_type.get_job_interface().validate_connection(job_conn))
        except InvalidConnection as ex:
            raise InvalidDefinition(unicode(ex))

        return warnings

    def _validate_job_dependencies(self):
        """Validates that every job dependency is listed in jobs and that there are no cyclic dependencies

        :raises InvalidDefinition: If there is an undefined job or a cyclic dependency
        """

        # Make sure all dependencies are defined
        for job_dict in self._definition['jobs']:
            job_name = job_dict['name']
            for dependency_dict in job_dict['dependencies']:
                dependency_name = dependency_dict['name']
                if dependency_name not in self._jobs_by_name:
                    msg = 'Invalid recipe definition: Job %s has undefined dependency %s' % (job_name, dependency_name)
                    raise InvalidDefinition(msg)

        # Ensure no cyclic dependencies
        for job_dict in self._definition['jobs']:
            job_name = job_dict['name']

            dependencies_to_check = set()
            dependencies_to_check.add(job_name)
            while dependencies_to_check:
                next_layer = set()
                for dependency in dependencies_to_check:
                    job_dict = self._jobs_by_name[dependency]
                    for dependency_dict in job_dict['dependencies']:
                        dependency_name = dependency_dict['name']
                        if dependency_name == job_name:
                            msg = 'Invalid recipe definition: Job %s has a circular dependency' % job_name
                            raise InvalidDefinition(msg)
                        next_layer.add(dependency_name)
                dependencies_to_check = next_layer

    def _validate_no_dup_job_inputs(self):
        """Validates that there are no duplicate inputs for any job

        :raises InvalidDefinition: If there is a duplicate input
        """

        for job_dict in self._definition['jobs']:
            job_name = job_dict['name']
            input_names = set()
            for recipe_dict in job_dict['recipe_inputs']:
                name = recipe_dict['job_input']
                if name in input_names:
                    msg = 'Invalid recipe definition: Job %s has duplicate input %s' % (job_name, name)
                    raise InvalidDefinition(msg)
                input_names.add(name)
            for dependency_dict in job_dict['dependencies']:
                for conn_dict in dependency_dict['connections']:
                    name = conn_dict['input']
                    if name in input_names:
                        msg = 'Invalid recipe definition: Job %s has duplicate input %s' % (job_name, name)
                        raise InvalidDefinition(msg)
                    input_names.add(name)

    def _validate_recipe_inputs(self):
        """Validates that the recipe inputs used when listing the jobs are defined in the input data section

        :raises InvalidDefinition: If there is an undefined recipe input
        """

        for job_dict in self._definition['jobs']:
            job_name = job_dict['name']
            for recipe_dict in job_dict['recipe_inputs']:
                recipe_input = recipe_dict['recipe_input']
                if recipe_input not in self._inputs_by_name:
                    msg = 'Invalid recipe definition: Job %s has undefined recipe input %s' % (job_name, recipe_input)
                    raise InvalidDefinition(msg)
