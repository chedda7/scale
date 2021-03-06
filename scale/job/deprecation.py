from job.configuration.data.job_connection import JobConnection
from job.configuration.data.job_data import JobData as JobData_1_0
from job.configuration.interface.job_interface import JobInterface
from job.data.job_connection import SeedJobConnection
from job.data.job_data import JobData
from job.seed.manifest import SeedManifest


class JobInterfaceSunset(object):
    """Class responsible for providing backward compatibility support for old style JobType interfaces as well as new
    Seed compliant interfaces.

    """
    @staticmethod
    def create(interface_dict, do_validate=True):
        """Instantiate an instance of the JobInterface based on inferred type

        :param interface_dict: deserialized JSON interface
        :type interface_dict: dict
        :param do_validate: whether schema validation should be applied
        :type do_validate: bool
        :return: instance of the job interface appropriate for input data
        :rtype: :class:`job.configuration.interface.job_interface.JobInterface` or
                :class:`job.seed.manifest.SeedManifest`
        """
        if JobInterfaceSunset.is_seed_dict(interface_dict):
            return SeedManifest(interface_dict, do_validate=do_validate)
        else:
            return JobInterface(interface_dict, do_validate=do_validate)

    @staticmethod
    def is_seed_dict(interface_dict):
        """Determines whether a given interface dict is Seed

        :param interface_dict: deserialized JSON interface
        :type interface_dict: dict
        :return: whether interface is Seed compliant or not
        :rtype: bool
        """
        return 'seedVersion' in interface_dict

    @staticmethod
    def is_seed(interface):
        """Determines whether a given interface instance is Seed

        :param interface: instance of JSON interface
        :type interface: :class:`job.configuration.interface.job_interface.JobInterface` or
                         :class:`job.seed.manifest.SeedManifest`
        :return: whether interface is Seed compliant or not
        :rtype: bool
        """
        return isinstance(interface, SeedManifest)

class JobConnectionSunset(object):
    """Class responsible for providing backward compatibility for old JobConnection interfaces as well as new Seed
    compliant connections.
    """

    @staticmethod
    def create(interface):
        """Instantiate an appropriately typed Job connection based on interface type

        """

        if JobInterfaceSunset.is_seed(interface):
            return SeedJobConnection()
        else:
            return JobConnection()

class JobDataSunset(object):
    """Class responsible for providing backward compatibility for old JobData interfaces as well as new Seed
    compliant ones.
    """

    @staticmethod
    def create(interface, data=None):
        """Instantiate an appropriately typed Job data based on version"""

        if JobInterfaceSunset.is_seed(interface):
            return JobData(data)
        else:
            return JobData_1_0(data)