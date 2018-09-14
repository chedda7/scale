"""Node Views"""


import logging

import rest_framework.status as status
from django.http.response import Http404
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

import mesos_api.api as mesos_api
import util.rest as rest_util
from node.models import Node
from node.serializers import NodeSerializer, NodeDetailsSerializer, NodeSerializerV4
from node.serializers_extra import NodeDetailsSerializerV4, NodeStatusSerializer
from scheduler.models import Scheduler

logger = logging.getLogger(__name__)


class NodesView(ListAPIView):
    """This view is the endpoint for viewing a list of nodes with metadata"""
    queryset = Node.objects.all()

    # TODO: remove when REST API v4 is removed
    def get_serializer_class(self):
        """Override the serializer for legacy API calls."""
        if self.request.version == 'v4':
            return NodeSerializerV4
        return NodeSerializer

    def list(self, request):
        """Determine api version and call specific method

        :param request: the HTTP POST request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        if request.version == 'v4':
            return self.list_impl(request)
        elif request.version == 'v5':
            return self.list_impl(request)
        elif request.version == 'v6':
            return self.list_impl(request)

        raise Http404()
        
    def list_impl(self, request):
        """Retrieves the list of all nodes and returns it in JSON form

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        started = rest_util.parse_timestamp(request, 'started', required=False)
        ended = rest_util.parse_timestamp(request, 'ended', required=False)
        rest_util.check_time_range(started, ended)
        is_active = rest_util.parse_bool(request, 'is_active', None, False)

        order = rest_util.parse_string_list(request, 'order', required=False)

        nodes = Node.objects.get_nodes(started, ended, order, is_active=is_active)

        page = self.paginate_queryset(nodes)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class NodeDetailsView(GenericAPIView):
    """This view is the endpoint for viewing and modifying a node"""

    queryset = Node.objects.all()
    update_fields = ('pause_reason', 'is_paused', 'is_active')

    # TODO: remove when REST API v4 is removed
    def get_serializer_class(self):
        """Override the serializer for legacy API calls."""
        if self.request.version == 'v4':
            return NodeDetailsSerializerV4
        return NodeDetailsSerializer

    def get(self, request, node_id):
        """Determine api version and call specific method

        :param request: the HTTP POST request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        if request.version == 'v4':
            return self.get_v4(request, node_id)
        elif request.version == 'v5':
            return self.get_impl(request, node_id)
        elif request.version == 'v6':
            return self.get_impl(request, node_id)

        raise Http404()
        
    def get_impl(self, request, node_id):
        """Gets node info

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :param node_id: The ID for the node.
        :type node_id: str
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        try:
            node = Node.objects.get_details(node_id)
        except Node.DoesNotExist:
            raise Http404

        serializer = self.get_serializer(node)
        return Response(serializer.data)

    def patch(self, request, node_id):
        """Determine api version and call specific method

        :param request: the HTTP PATCH request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        if request.version == 'v4':
            return self.patch_v4(request, node_id)
        elif request.version == 'v5':
            return self.patch_v5(request, node_id)
        elif request.version == 'v6':
            return self.patch_v6(request, node_id)

        raise Http404()
        
    def patch_v5(self, request, node_id):
        """Modify node info with a subset of fields

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :param node_id: The ID for the node.
        :type node_id: str
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """
        
        extra = list(filter(lambda x, y=self.update_fields: x not in y, list(request.data.keys())))
        if len(extra) > 0:
            return Response('Unexpected fields: %s' % ', '.join(extra), status=status.HTTP_400_BAD_REQUEST)

        if not len(request.data):
            return Response('No fields specified for update.', status=status.HTTP_400_BAD_REQUEST)

        try:
            Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            raise Http404

        Node.objects.update_node(dict(request.data), node_id=node_id)

        try:
            node = Node.objects.get_details(node_id)
        except Node.DoesNotExist:
            raise Http404

        serializer = self.get_serializer(node)
        return Response(serializer.data)
        
    def patch_v6(self, request, node_id):
        """Modify node info with a subset of fields

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :param node_id: The ID for the node.
        :type node_id: str
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """
        
        extra = list(filter(lambda x, y=self.update_fields: x not in y, list(request.data.keys())))
        if len(extra) > 0:
            return Response('Unexpected fields: %s' % ', '.join(extra), status=status.HTTP_400_BAD_REQUEST)

        if not len(request.data):
            return Response('No fields specified for update.', status=status.HTTP_400_BAD_REQUEST)

        try:
            Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            raise Http404

        Node.objects.update_node(dict(request.data), node_id=node_id)

        return Response(status=status.HTTP_204_NO_CONTENT)

    # TODO: remove when REST API v4 is removed
    def get_v4(self, request, node_id):
        """Gets node info

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :param node_id: The ID for the node.
        :type node_id: str
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        return Response(self._get_node_details_v4(node_id))

    # TODO: remove when REST API v4 is removed
    def patch_v4(self, request, node_id):
        """Modify node info with a subset of fields

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :param node_id: The ID for the node.
        :type node_id: str
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        extra = list(filter(lambda x, y=self.update_fields: x not in y, list(request.data.keys())))
        if len(extra) > 0:
            return Response('Unexpected fields: %s' % ', '.join(extra), status=status.HTTP_400_BAD_REQUEST)

        if not len(request.data):
            return Response('No fields specified for update.', status=status.HTTP_400_BAD_REQUEST)

        try:
            Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            raise Http404

        Node.objects.update_node(dict(request.data), node_id=node_id)

        result = self._get_node_details_v4(node_id)

        return Response(result, status=status.HTTP_200_OK)

    # TODO: remove when REST API v4 is removed
    def _get_node_details_v4(self, node_id):

        # Fetch the basic node attributes
        try:
            node = Node.objects.get_details(node_id)
        except Node.DoesNotExist:
            raise Http404
        serializer = self.get_serializer(node)
        result = serializer.data

        # Attempt to fetch resource usage for the node
        resources = None
        try:
            sched = Scheduler.objects.get_master()
            slave_info = mesos_api.get_slave(sched.master_hostname, sched.master_port, node.slave_id, True)
            if slave_info and slave_info.total:
                resources = slave_info.to_dict()['resources']
        except:
            logger.exception('Unable to fetch slave resource usage')
        if resources:
            result['resources'] = resources
        else:
            result['disconnected'] = True

        return result


# TODO: remove when REST API v4 is removed
class NodesStatusView(ListAPIView):
    """This view is the endpoint for retrieving overall node status information."""
    queryset = []
    serializer_class = NodeStatusSerializer

    def list(self, request):
        """Retrieves the list of all nodes with execution status and returns it in JSON form

        :param request: the HTTP GET request
        :type request: :class:`rest_framework.request.Request`
        :rtype: :class:`rest_framework.response.Response`
        :returns: the HTTP response to send back to the user
        """

        if request.version != 'v4':
            raise Http404

        # Get a list of all node status counts
        started = rest_util.parse_timestamp(request, 'started', 'PT3H0M0S')
        ended = rest_util.parse_timestamp(request, 'ended', required=False)
        node_statuses = Node.objects.get_status(started, ended)

        # Get the online nodes
        try:
            sched = Scheduler.objects.get_master()
            slaves = mesos_api.get_slaves(sched.master_hostname, sched.master_port)
            slaves_dict = {s.hostname for s in slaves}
        except:
            logger.exception('Unable to fetch nodes online status')
            slaves_dict = dict()

        # Add the online status to each node
        for node_status in node_statuses:
            node_status.is_online = node_status.node.hostname in slaves_dict

        page = self.paginate_queryset(node_statuses)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
