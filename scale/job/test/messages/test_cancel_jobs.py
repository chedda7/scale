

import django
from django.test import TestCase
from django.utils.timezone import now

from job.configuration.data.job_data import JobData
from job.messages.cancel_jobs import CancelJobs
from job.models import Job
from job.test import utils as job_test_utils


class TestCancelJobs(TestCase):

    def setUp(self):
        django.setup()

    def test_json(self):
        """Tests coverting a CancelJobs message to and from JSON"""

        when = now()
        data = JobData()
        job_type = job_test_utils.create_job_type()
        job_1 = job_test_utils.create_job(job_type=job_type, status='PENDING')
        job_2 = job_test_utils.create_job(job_type=job_type, num_exes=3, status='FAILED', input=data.get_dict())
        job_ids = [job_1.id, job_2.id]

        # Add jobs to message
        message = CancelJobs()
        message.when = when
        if message.can_fit_more():
            message.add_job(job_1.id)
        if message.can_fit_more():
            message.add_job(job_2.id)

        # Convert message to JSON and back, and then execute
        message_json_dict = message.to_json()
        new_message = CancelJobs.from_json(message_json_dict)
        result = new_message.execute()

        self.assertTrue(result)
        jobs = Job.objects.filter(id__in=job_ids).order_by('id')
        # Both jobs should have been canceled
        self.assertEqual(jobs[0].status, 'CANCELED')
        self.assertEqual(jobs[0].last_status_change, when)
        self.assertEqual(jobs[1].status, 'CANCELED')
        self.assertEqual(jobs[1].last_status_change, when)
        # No new messages since these jobs do not belong to a recipe
        self.assertEqual(len(new_message.new_messages), 0)

    def test_execute(self):
        """Tests calling CancelJobs.execute() successfully"""

        when = now()
        data = JobData()
        job_type = job_test_utils.create_job_type()
        job_1 = job_test_utils.create_job(job_type=job_type, num_exes=3, status='FAILED', input=data.get_dict())
        job_2 = job_test_utils.create_job(job_type=job_type, num_exes=3, status='CANCELED', input=data.get_dict())
        job_3 = job_test_utils.create_job(job_type=job_type, num_exes=1, status='COMPLETED', input=data.get_dict())
        job_4 = job_test_utils.create_job(job_type=job_type, num_exes=0, status='PENDING')
        job_ids = [job_1.id, job_2.id, job_3.id, job_4.id]
        from recipe.test import utils as recipe_test_utils
        recipe = recipe_test_utils.create_recipe()
        recipe_test_utils.create_recipe_job(recipe=recipe, job_name='job_1', job=job_1)
        recipe_test_utils.create_recipe_job(recipe=recipe, job_name='job_2', job=job_2)
        recipe_test_utils.create_recipe_job(recipe=recipe, job_name='job_3', job=job_3)
        recipe_test_utils.create_recipe_job(recipe=recipe, job_name='job_4', job=job_4)

        # Add jobs to message
        message = CancelJobs()
        message.when = when
        if message.can_fit_more():
            message.add_job(job_1.id)
        if message.can_fit_more():
            message.add_job(job_2.id)
        if message.can_fit_more():
            message.add_job(job_3.id)
        if message.can_fit_more():
            message.add_job(job_4.id)

        # Execute message
        result = message.execute()
        self.assertTrue(result)

        jobs = Job.objects.filter(id__in=job_ids).order_by('id')
        # Job 1 should have been canceled
        self.assertEqual(jobs[0].status, 'CANCELED')
        self.assertEqual(jobs[0].last_status_change, when)
        # Job 2 was already canceled
        self.assertEqual(jobs[1].status, 'CANCELED')
        self.assertNotEqual(jobs[1].last_status_change, when)
        # Job 3 was already COMPLETED, so can't be canceled
        self.assertEqual(jobs[2].status, 'COMPLETED')
        self.assertNotEqual(jobs[2].last_status_change, when)
        # Job 4 should have been canceled
        self.assertEqual(jobs[3].status, 'CANCELED')
        self.assertEqual(jobs[3].last_status_change, when)
        # Should be messages to update recipes and update recipe metrics after canceling jobs
        self.assertEqual(len(message.new_messages), 2)
        update_recipes_msg = None
        update_recipe_metrics_msg = None
        for msg in message.new_messages:
            if msg.type == 'update_recipes':
                update_recipes_msg = msg
            elif msg.type == 'update_recipe_metrics':
                update_recipe_metrics_msg = msg
        self.assertIsNotNone(update_recipes_msg)
        self.assertIsNotNone(update_recipe_metrics_msg)
        self.assertListEqual(update_recipes_msg._recipe_ids, [recipe.id])
        self.assertListEqual(update_recipe_metrics_msg._recipe_ids, [recipe.id])

        # Test executing message again
        message.new_messages = []
        result = message.execute()
        self.assertTrue(result)

        # All results should be the same
        jobs = Job.objects.filter(id__in=job_ids).order_by('id')
        # Job 1 should have been canceled
        self.assertEqual(jobs[0].status, 'CANCELED')
        self.assertEqual(jobs[0].last_status_change, when)
        # Job 2 was already canceled
        self.assertEqual(jobs[1].status, 'CANCELED')
        self.assertNotEqual(jobs[1].last_status_change, when)
        # Job 3 was already COMPLETED, so can't be canceled
        self.assertEqual(jobs[2].status, 'COMPLETED')
        self.assertNotEqual(jobs[2].last_status_change, when)
        # Job 4 should have been canceled
        self.assertEqual(jobs[3].status, 'CANCELED')
        self.assertEqual(jobs[3].last_status_change, when)
        # Should be messages to update recipes and update recipe metrics after canceling jobs
        self.assertEqual(len(message.new_messages), 2)
        update_recipes_msg = None
        update_recipe_metrics_msg = None
        for msg in message.new_messages:
            if msg.type == 'update_recipes':
                update_recipes_msg = msg
            elif msg.type == 'update_recipe_metrics':
                update_recipe_metrics_msg = msg
        self.assertIsNotNone(update_recipes_msg)
        self.assertIsNotNone(update_recipe_metrics_msg)
        self.assertListEqual(update_recipes_msg._recipe_ids, [recipe.id])
        self.assertListEqual(update_recipe_metrics_msg._recipe_ids, [recipe.id])
