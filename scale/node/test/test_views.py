

import json
from datetime import timedelta

import django
from django.test import TransactionTestCase
from django.utils.timezone import now
from mock import patch
from rest_framework import status

import error.test.utils as error_test_utils
import job.test.utils as job_test_utils
import node.test.utils as node_test_utils
import util.rest as rest_util
from mesos_api.api import SlaveInfo, HardwareResources
from scheduler.models import Scheduler


class TestNodesViewV5(TransactionTestCase):

    def setUp(self):
        django.setup()

        self.node1 = node_test_utils.create_node()
        self.node2 = node_test_utils.create_node()

    def test_nodes_view(self):
        """Test the REST call to retrieve a list of nodes"""

        url = '/v5/nodes/'
        response = self.client.generic('GET', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        results = json.loads(response.content)
        self.assertEqual(len(results['results']), 2)

        for entry in results['results']:
            if entry['id'] == self.node1.id:
                self.assertEqual(entry['hostname'], self.node1.hostname)
            elif entry['id'] == self.node2.id:
                self.assertEqual(entry['hostname'], self.node2.hostname)
            else:
                self.fail('Unexpected node in results: %i' % entry['id'])

class TestNodesViewV6(TransactionTestCase):

    def setUp(self):
        django.setup()

        self.node1 = node_test_utils.create_node()
        self.node2 = node_test_utils.create_node()

    def test_nodes_view(self):
        """Test the REST call to retrieve a list of nodes"""

        url = '/v6/nodes/'
        response = self.client.generic('GET', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        results = json.loads(response.content)
        self.assertEqual(len(results['results']), 2)

        for entry in results['results']:
            if entry['id'] == self.node1.id:
                self.assertEqual(entry['hostname'], self.node1.hostname)
            elif entry['id'] == self.node2.id:
                self.assertEqual(entry['hostname'], self.node2.hostname)
            else:
                self.fail('Unexpected node in results: %i' % entry['id'])

class TestNodesViewEmptyV5(TransactionTestCase):

    def setUp(self):
        django.setup()

    def test_nodes_view(self):
        """ test the REST call to retrieve an empty list of nodes"""
        url = '/v5/nodes/'
        response = self.client.generic('GET', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        results = json.loads(response.content)
        self.assertEqual(len(results['results']), 0)

class TestNodesViewEmptyV6(TransactionTestCase):

    def setUp(self):
        django.setup()

    def test_nodes_view(self):
        """ test the REST call to retrieve an empty list of nodes"""
        url = '/v6/nodes/'
        response = self.client.generic('GET', url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        results = json.loads(response.content)
        self.assertEqual(len(results['results']), 0)
        
class TestNodeDetailsViewV5(TransactionTestCase):

    def setUp(self):
        django.setup()

        self.node1 = node_test_utils.create_node()
        self.node2 = node_test_utils.create_node()
        self.node3 = node_test_utils.create_node()

        Scheduler.objects.create(id=1, master_hostname='localhost', master_port=5050)

    def test_get_node_success(self):
        """Test successfully calling the Get Node method."""

        url = '/v5/nodes/%d/' % self.node2.id
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        result = json.loads(response.content)
        self.assertIn('hostname', result)
        self.assertEqual(result['hostname'], self.node2.hostname)

    # TODO: remove when REST API v4 is removed
    @patch('mesos_api.api.get_slave')
    def test_get_node_master_disconnected(self, mock_get_slave):
        """Test calling the Get Node method with a disconnected master."""
        mock_get_slave.return_value = SlaveInfo(self.node2.hostname, self.node2.port)

        response = self.client.get('/v4/nodes/%d/' % self.node2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        result = json.loads(response.content)
        self.assertNotIn('resources', result)
        self.assertEqual(result['disconnected'], True)

    def test_get_node_not_found(self):
        """Test calling the Get Node method with a bad node id."""

        url = '/v5/nodes/9999/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_node_success(self):
        """Test successfully calling the Update Node method."""

        json_data = {
            'is_paused': True,
            'pause_reason': 'Test reason',
        }

        url = '/v5/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        result = json.loads(response.content)
        self.assertEqual(result['is_paused'], True)
        self.assertEqual(result['pause_reason'], json_data['pause_reason'])
        self.assertIn('hostname', result)
        self.assertEqual(result['hostname'], self.node2.hostname)

    def test_update_node_unpause(self):
        """Tests unpausing the node and specifying a reason."""

        json_data = {'is_paused': False, 'pause_reason': 'Test reason'}

        url = '/v5/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        result = json.loads(response.content)
        self.assertEqual(result['is_paused'], False)
        self.assertIsNone(result['pause_reason'])
        self.assertIn('hostname', result)
        self.assertEqual(result['hostname'], self.node2.hostname)

    def test_update_node_not_found(self):
        """Test calling the Update Node method with a bad node id."""

        json_data = {
            'is_paused': False,
        }

        url = '/v5/nodes/9999/'
        response = self.client.patch(url, json.dumps(json_data), 'application/json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_node_no_fields(self):
        """Test calling the Update Node method with no fields."""

        json_data = {}
        url = '/v5/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_update_node_extra_fields(self):
        """Test calling the Update Node method with extra fields."""

        json_data = {
            'foo': 'bar',
        }

        url = '/v5/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_update_active(self):
        """Test successfully deactivating a node."""

        json_data = {
            'is_active': False,
        }

        url = '/v5/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        result = json.loads(response.content)
        self.assertEqual(result['is_active'], False)
        self.assertIn('deprecated', result)

class TestNodeDetailsViewV6(TransactionTestCase):

    def setUp(self):
        django.setup()

        self.node1 = node_test_utils.create_node()
        self.node2 = node_test_utils.create_node()
        self.node3 = node_test_utils.create_node()

        Scheduler.objects.create(id=1, master_hostname='localhost', master_port=5050)

    def test_get_node_success(self):
        """Test successfully calling the Get Node method."""

        url = '/v6/nodes/%d/' % self.node2.id
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        result = json.loads(response.content)
        self.assertIn('hostname', result)
        self.assertEqual(result['hostname'], self.node2.hostname)

    def test_get_node_not_found(self):
        """Test calling the Get Node method with a bad node id."""

        url = '/v6/nodes/9999/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_node_success(self):
        """Test successfully calling the Update Node method."""

        json_data = {
            'is_paused': True,
            'pause_reason': 'Test reason',
        }

        url = '/v6/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)

    def test_update_node_unpause(self):
        """Tests unpausing the node and specifying a reason."""

        json_data = {'is_paused': False, 'pause_reason': 'Test reason'}

        url = '/v6/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)

    def test_update_node_not_found(self):
        """Test calling the Update Node method with a bad node id."""

        json_data = {
            'is_paused': False,
        }

        url = '/v6/nodes/9999/'
        response = self.client.patch(url, json.dumps(json_data), 'application/json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_node_no_fields(self):
        """Test calling the Update Node method with no fields."""

        json_data = {}
        url = '/v6/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_update_node_extra_fields(self):
        """Test calling the Update Node method with extra fields."""

        json_data = {
            'foo': 'bar',
        }

        url = '/v6/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_update_active(self):
        """Test successfully deactivating a node."""

        json_data = {
            'is_active': False,
        }

        url = '/v6/nodes/%d/' % self.node2.id
        response = self.client.patch(url, json.dumps(json_data), 'application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)

        
# TODO: remove when REST API v4 is removed
class TestNodesStatusViewV4(TransactionTestCase):
    """ Test class to test the REST service to retrieve the node status for all the nodes in the cluster."""

    def setUp(self):
        django.setup()

        self.scheduler = Scheduler.objects.create(id=1, master_hostname='master', master_port=5050)

        self.node1 = node_test_utils.create_node()
        self.node2 = node_test_utils.create_node()
        self.node3 = node_test_utils.create_node()

        self.job = job_test_utils.create_job(status='COMPLETED')

        data_error = error_test_utils.create_error(category='DATA')
        system_error = error_test_utils.create_error(category='SYSTEM')

        job_exe_1 = job_test_utils.create_job_exe(job=self.job, status='FAILED', error=data_error, node=self.node2)
        job_exe_1.created = now() - timedelta(hours=3)
        job_exe_1.job_completed = now() - timedelta(hours=2)
        job_exe_1.save()
        job_exe_2 = job_test_utils.create_job_exe(job=self.job, status='FAILED', error=system_error, node=self.node2)
        job_exe_2.created = now() - timedelta(hours=3)
        job_exe_2.job_completed = now() - timedelta(hours=2)
        job_exe_2.save()
        job_exe_3 = job_test_utils.create_job_exe(job=self.job, status='FAILED', error=system_error, node=self.node1)
        job_exe_3.created = now() - timedelta(hours=2)
        job_exe_3.job_completed = now() - timedelta(hours=1)
        job_exe_3.save()
        job_exe_4 = job_test_utils.create_job_exe(job=self.job, status='COMPLETED', node=self.node1)
        job_exe_4.created = now() - timedelta(hours=1)
        job_exe_4.job_completed = now()
        job_exe_4.save()
        job_exe_5 = job_test_utils.create_job_exe(job=self.job, status='RUNNING', node=self.node3)
        job_exe_5.created = now()
        job_exe_5.save()

    # TODO: remove when REST API v4 is removed
    @patch('mesos_api.api.get_slaves')
    def test_nodes_system_stats(self, mock_get_slaves):
        """This method tests for when a node has not processed any jobs for the duration of time requested."""
        mock_get_slaves.return_value = [
            SlaveInfo(self.node1.hostname, self.node1.port, HardwareResources(1, 2, 3)),
            SlaveInfo(self.node3.hostname, self.node3.port, HardwareResources(4, 5, 6)),
        ]

        response = self.client.generic('GET', '/v4/nodes/status/?started=PT1H30M0S')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        result = json.loads(response.content)
        self.assertTrue(isinstance(result, dict), 'result  must be a dictionary')

        assert_message = '({0} != 3) Expected to get the 3 nodes'.format(len(result['results']))
        self.assertEqual(len(result['results']), 3, assert_message)

        for entry in result['results']:
            hostname = entry['node']['hostname']
            self.assertIn(hostname, [self.node1.hostname, self.node2.hostname, self.node3.hostname])

            if hostname == self.node1.hostname:
                self.assertTrue(entry['is_online'])
                self.assertEqual(len(entry['job_exe_counts']), 2)
                for status_count in entry['job_exe_counts']:
                    if status_count['status'] == 'COMPLETED':
                        self.assertEqual(status_count['count'], 1)
                    elif status_count['status'] == 'FAILED':
                        self.assertEqual(status_count['count'], 1)
                    else:
                        self.fail('Unexpected job execution status found: %s' % status_count['status'])
            elif hostname == self.node2.hostname:
                self.assertFalse(entry['is_online'])
                for status_count in entry['job_exe_counts']:
                    if status_count['status'] == 'FAILED' and status_count['category'] == 'DATA':
                        self.assertEqual(status_count['count'], 1)
                    elif status_count['status'] == 'FAILED' and status_count['category'] == 'SYSTEM':
                        self.assertEqual(status_count['count'], 1)
                    else:
                        self.fail('Unexpected job execution status found: %s' % status_count['status'])
            elif hostname == self.node3.hostname:
                self.assertTrue(entry['is_online'])
                self.assertEqual(len(entry['job_exes_running']), 1)
                for status_count in entry['job_exe_counts']:
                    if status_count['status'] == 'RUNNING':
                        self.assertEqual(status_count['count'], 1)

    # TODO: remove when REST API v4 is removed
    @patch('mesos_api.api.get_slaves')
    def test_nodes_stats(self, mock_get_slaves):
        """This method tests retrieving all the nodes statistics
        for the three hour duration requested"""
        mock_get_slaves.return_value = [
            SlaveInfo(self.node1.hostname, self.node1.port, HardwareResources(1, 2, 3)),
            SlaveInfo(self.node3.hostname, self.node3.port, HardwareResources(4, 5, 6)),
        ]

        response = self.client.generic('GET', '/v4/nodes/status/?started=PT3H00M0S')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        result = json.loads(response.content)
        self.assertTrue(isinstance(result, dict), 'result  must be a dictionary')

        assert_message = '({0} != 3) Expected to get the 3 nodes'.format(len(result['results']))
        self.assertEqual(len(result['results']), 3, assert_message)

        for entry in result['results']:
            hostname = entry['node']['hostname']
            self.assertIn(hostname, [self.node1.hostname, self.node2.hostname, self.node3.hostname])

            if hostname == self.node1.hostname:
                self.assertTrue(entry['is_online'])
                self.assertEqual(len(entry['job_exe_counts']), 2)
                for status_count in entry['job_exe_counts']:
                    if status_count['status'] == 'COMPLETED':
                        self.assertEqual(status_count['count'], 1)
                    elif status_count['status'] == 'FAILED':
                        self.assertEqual(status_count['count'], 1)
                    else:
                        self.fail('Unexpected job execution status found: %s' % status_count['status'])
            elif hostname == self.node2.hostname:
                self.assertFalse(entry['is_online'])
                for status_count in entry['job_exe_counts']:
                    if status_count['status'] == 'FAILED' and status_count['category'] == 'DATA':
                        self.assertEqual(status_count['count'], 1)
                    elif status_count['status'] == 'FAILED' and status_count['category'] == 'SYSTEM':
                        self.assertEqual(status_count['count'], 1)
                    else:
                        self.fail('Unexpected job execution status found: %s' % status_count['status'])
            elif hostname == self.node3.hostname:
                self.assertTrue(entry['is_online'])
                self.assertEqual(len(entry['job_exes_running']), 1)
                for status_count in entry['job_exe_counts']:
                    if status_count['status'] == 'RUNNING':
                        self.assertEqual(status_count['count'], 1)
