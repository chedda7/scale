"""Defines the views for the RESTful queue services"""


import datetime
import logging

import rest_framework.status as status
from django.http.response import Http404
from rest_framework.parsers import JSONParser
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

import util.rest as rest_util
from job.configuration.data.exceptions import InvalidData
from job.models import Job, JobType
from job.serializers import JobDetailsSerializerV6, JobSerializerV6, JobSerializerV5, JobDetailsSerializerV5
from queue.models import JobLoad, Queue
from queue.serializers import JobLoadGroupSerializer, QueueStatusSerializer, RequeueJobSerializer
from recipe.configuration.data.exceptions import InvalidRecipeData
from recipe.configuration.data.recipe_data import LegacyRecipeData
from recipe.models import Recipe, RecipeType
from recipe.serializers import RecipeDetailsSerializerV6, OldRecipeDetailsSerializer

logger = logging.getLogger(__name__)


class JobLoadView(ListAPIView):
    """This view is the endpoint for retrieving the job load for a given time range."""
    queryset = JobLoad.objects.all()
    serializer_class = JobLoadGroupSerializer

    def list(self, request):
        """Retrieves the job load for a given time range and returns it in JSON form

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """
        started = rest_util.parse_timestamp(request, 'started', default_value=rest_util.get_relative_days(7))
        ended = rest_util.parse_timestamp(request, 'ended', required=False)
        rest_util.check_time_range(started, ended, max_duration=datetime.timedelta(days=31))

        job_type_ids = rest_util.parse_int_list(request, 'job_type_id', required=False)
        job_type_names = rest_util.parse_string_list(request, 'job_type_name', required=False)
        job_type_categories = rest_util.parse_string_list(request, 'job_type_category', required=False)
        job_type_priorities = rest_util.parse_string_list(request, 'job_type_priority', required=False)

        job_loads = JobLoad.objects.get_job_loads(started, ended, job_type_ids, job_type_names, job_type_categories,
                                                  job_type_priorities)
        job_loads_grouped = JobLoad.objects.group_by_time(job_loads)

        page = self.paginate_queryset(job_loads_grouped)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class QueueNewJobView(GenericAPIView):
    """This view is the endpoint for creating new jobs and putting them on the queue."""
    parser_classes = (JSONParser,)
    queryset = Job.objects.all()

    # TODO: remove this class and un-comment serializer declaration when REST API v5 is removed
    # serializer_class = JobDetailsSerializer
    def get_serializer_class(self):
        """Returns the appropriate serializer based off the requests version of the REST API. """

        if self.request.version == 'v6':
            return JobDetailsSerializerV6
        else:
            return JobDetailsSerializerV5
    
    def post(self, request):
        """Creates a new job, places it on the queue, and returns the new job information in JSON form

        :param request: the HTTP POST request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        job_type_id = rest_util.parse_int(request, 'job_type_id')
        job_data = rest_util.parse_dict(request, 'job_data', {})

        try:
            job_type = JobType.objects.get(pk=job_type_id)
        except JobType.DoesNotExist:
            raise Http404

        try:
            job_id = Queue.objects.queue_new_job_for_user(job_type, job_data)
        except InvalidData as err:
            logger.exception('Invalid job data.')
            return Response('Invalid job data: ' + str(err), status=status.HTTP_400_BAD_REQUEST)

        try:
            # TODO: remove this check when REST API v5 is removed. 
            if request.version == 'v6':
                job_details = Job.objects.get_details(job_id)
            else:
                job_details = Job.objects.get_details_v5(job_id)
        except Job.DoesNotExist:
            raise Http404

        serializer = self.get_serializer(job_details)
        job_url = reverse('job_details_view', args=[job_id], request=request)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=dict(location=job_url))


class QueueNewRecipeView(GenericAPIView):
    """This view is the endpoint for queuing recipes and returns the detail information for the recipe that was queued.
    """
    parser_classes = (JSONParser,)
    queryset = Recipe.objects.all()
    
    # TODO: remove this class and un-comment serializer declaration when REST API v5 is removed
    # serializer_class = RecipeDetailsSerializer
    def get_serializer_class(self):
        """Returns the appropriate serializer based off the requests version of the REST API. """

        if self.request.version == 'v6':
            return RecipeDetailsSerializerV6
        else:
            return OldRecipeDetailsSerializer

    def post(self, request):
        """Queue a recipe and returns the new job information in JSON form

        :param request: the HTTP POST request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        recipe_type_id = rest_util.parse_int(request, 'recipe_type_id')
        recipe_data = rest_util.parse_dict(request, 'recipe_data', {})

        try:
            recipe_type = RecipeType.objects.get(pk=recipe_type_id)
        except RecipeType.DoesNotExist:
            raise Http404

        try:
            handler = Queue.objects.queue_new_recipe_for_user(recipe_type, LegacyRecipeData(recipe_data))
        except InvalidRecipeData as err:
            return Response('Invalid recipe data: ' + str(err), status=status.HTTP_400_BAD_REQUEST)

        try:
            # TODO: remove this check when REST API v5 is removed
            if request.version == 'v6':
                recipe = Recipe.objects.get_details(handler.recipe.id)
            else:
                recipe = Recipe.objects.get_details_v5(handler.recipe.id)
        except Recipe.DoesNotExist:
            raise Http404
            
        serializer = self.get_serializer(recipe)
        recipe_url = reverse('recipe_details_view', args=[recipe.id], request=request)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=dict(location=recipe_url))


class QueueStatusView(ListAPIView):
    """This view is the endpoint for retrieving the queue status."""
    queryset = Queue.objects.all()
    serializer_class = QueueStatusSerializer

    def list(self, request):
        """Retrieves the current status of the queue and returns it in JSON form

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """
        queue_statuses = Queue.objects.get_queue_status()

        page = self.paginate_queryset(queue_statuses)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


# TODO: remove this when REST API v5 is removed
class RequeueJobsView(GenericAPIView):
    """This view is the endpoint for requeuing jobs which have already been executed."""
    parser_classes = (JSONParser,)
    queryset = Job.objects.all()
    serializer_class = JobSerializerV5

    def post(self, request):
        """Increase max_tries, place it on the queue, and returns the new job information in JSON form

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :returns: the HTTP response to send back to the user
        """

        if request.version == 'v6':
            raise Http404

        started = rest_util.parse_timestamp(request, 'started', required=False)
        ended = rest_util.parse_timestamp(request, 'ended', required=False)
        rest_util.check_time_range(started, ended)

        job_status = rest_util.parse_string(request, 'status', required=False)
        job_ids = rest_util.parse_int_list(request, 'job_ids', required=False)
        job_type_ids = rest_util.parse_int_list(request, 'job_type_ids', required=False)
        job_type_names = rest_util.parse_string_list(request, 'job_type_names', required=False)
        job_type_categories = rest_util.parse_string_list(request, 'job_type_categories', required=False)
        error_categories = rest_util.parse_string_list(request, 'error_categories', required=False)

        priority = rest_util.parse_int(request, 'priority', required=False)

        # Fetch all the jobs matching the filters
        job_status = [job_status] if job_status else job_status
        jobs = Job.objects.get_jobs_v5(started=started, ended=ended, statuses=job_status, job_ids=job_ids,
                                    job_type_ids=job_type_ids, job_type_names=job_type_names,
                                    job_type_categories=job_type_categories, error_categories=error_categories)

        # Attempt to queue all jobs matching the filters
        requested_job_ids = {job.id for job in jobs}
        if requested_job_ids:
            Queue.objects.requeue_jobs(requested_job_ids, priority)

            # Refresh models to get the new status information for all originally requested jobs
            jobs = Job.objects.get_jobs_v5(job_ids=requested_job_ids)

        page = self.paginate_queryset(jobs)
        serializer = JobSerializerV5(page, many=True)

        return self.get_paginated_response(serializer.data)
