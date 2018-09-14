"""Defines the class for handling files inputs"""


from job.handlers.inputs.base_input import Input


class FilesInput(Input):
    """Represents a multiple file input
    """

    def __init__(self, input_name, required):
        """Constructor

        :param input_name: The name of the input
        :type input_name: str
        :param required: Whether the input is required
        :type required: bool
        """

        super(FilesInput, self).__init__(input_name, 'files', required)
