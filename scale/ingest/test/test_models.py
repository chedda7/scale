

import django
from django.test import TestCase, TransactionTestCase

import storage.test.utils as storage_test_utils
from ingest.strike.configuration.json.configuration_2_0 import StrikeConfigurationV2
from ingest.strike.configuration.json.configuration_v6 import StrikeConfigurationV6
from ingest.models import Ingest, Strike
from storage.exceptions import InvalidDataTypeTag


class TestIngestAddDataTypeTag(TestCase):
    def setUp(self):
        django.setup()

    def test_valid(self):
        """Tests calling add_data_type_tag() with valid tags"""

        ingest = Ingest()
        ingest.add_data_type_tag('Hello1')
        ingest.add_data_type_tag('foo_BAR')
        tags = ingest.get_data_type_tags()

        correct_set = set()
        correct_set.add('Hello1')
        correct_set.add('foo_BAR')

        self.assertSetEqual(tags, correct_set)

    def test_invalid(self):
        """Tests calling add_data_type_tag() with invalid tags"""

        ingest = Ingest()

        self.assertRaises(InvalidDataTypeTag, ingest.add_data_type_tag, 'my.invalid.tag')
        self.assertRaises(InvalidDataTypeTag, ingest.add_data_type_tag, 'my\invalid\tag!')


class TestIngestGetDataTypeTags(TestCase):
    def setUp(self):
        django.setup()

    def test_tags(self):
        """Tests calling get_data_type_tags() with tags"""

        ingest = Ingest(data_type='A,B,c')
        tags = ingest.get_data_type_tags()

        correct_set = set()
        correct_set.add('A')
        correct_set.add('B')
        correct_set.add('c')

        self.assertSetEqual(tags, correct_set)

    def test_no_tags(self):
        """Tests calling get_data_type_tags() with no tags"""

        ingest = Ingest()
        tags = ingest.get_data_type_tags()

        self.assertSetEqual(tags, set())


class TestStrikeManagerCreateStrikeProcess(TransactionTestCase):
    fixtures = ['ingest_job_types.json']

    def setUp(self):
        django.setup()

        self.workspace = storage_test_utils.create_workspace()

    def test_successful(self):
        """Tests calling StrikeManager.create_strike() successfully"""

        config = {
            'version': '1.0',
            'mount': 'host:/my/path',
            'transfer_suffix': '_tmp',
            'files_to_ingest': [{
                'filename_regex': 'foo',
                'workspace_path': 'my/path',
                'workspace_name': self.workspace.name,
            }]
        }

        config = StrikeConfigurationV2(config).get_configuration()
        strike = Strike.objects.create_strike('my_name', 'my_title', 'my_description', config)
        self.assertEqual(strike.job.status, 'QUEUED')
        
    def test_successful_v6(self):
        """Tests calling StrikeManager.create_strike successfully with v6 config"""

        config = {
            'version': '6',
            'workspace': self.workspace.name, 
            'monitor': {'type': 'dir-watcher', 'transfer_suffix': '_tmp'},
            'files_to_ingest': [{
                'filename_regex': 'foo',
                'data_types': ['test1','test2'],
                'new_workspace': self.workspace.name,
                'new_file_path': 'my/path'
            }]
        }

        config = StrikeConfigurationV6(config).get_configuration()
        strike = Strike.objects.create_strike('my_name', 'my_title', 'my_description', config)
        self.assertEqual(strike.job.status, 'QUEUED')
