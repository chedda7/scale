"""Defines the class for representing the diff for a node within a recipe definition"""


from abc import ABCMeta, abstractmethod
from collections import namedtuple

from recipe.definition.node import JobNodeDefinition, RecipeNodeDefinition
from util.exceptions import ScaleLogicBug


Change = namedtuple('Change', ['name', 'description'])


def create_diff_for_node(node, diff_can_be_reprocessed, status):
    """Creates a node diff for the given node

    :param node: The node
    :type node: :class:`recipe.definition.node.NodeDefinition`
    :param diff_can_be_reprocessed: Whether the top-level diff can be reprocessed
    :type diff_can_be_reprocessed: bool
    :param status: The diff status
    :type status: string
    :returns: The node diff
    :rtype: :class:`recipe.diff.node.NodeDiff`
    """

    if node.node_type == JobNodeDefinition.NODE_TYPE:
        return JobNodeDiff(node, diff_can_be_reprocessed, status)
    if node.node_type == RecipeNodeDefinition.NODE_TYPE:
        return RecipeNodeDiff(node, diff_can_be_reprocessed, status)

    raise ScaleLogicBug('Unknown node type %s' % node.node_type)


class NodeDiff(object, metaclass=ABCMeta):
    """Represents a diff for a node within a recipe definition
    """

    # Node statuses
    UNCHANGED = 'UNCHANGED'
    CHANGED = 'CHANGED'
    NEW = 'NEW'
    DELETED = 'DELETED'

    # The statuses that cause a new node to be created when reprocessed
    STATUSES_REPROCESS_NEW_NODE = [CHANGED, NEW]

    def __init__(self, node, diff_can_be_reprocessed, status=NEW):
        """Constructor

        :param node: The node from the recipe definition
        :type node: :class:`recipe.definition.node.NodeDefinition`
        :param diff_can_be_reprocessed: Whether the top-level diff can be reprocessed
        :type diff_can_be_reprocessed: bool
        :param status: The diff status, defaults to NEW
        :type status: string
        """

        self._node = node
        self._diff_can_be_reprocessed = diff_can_be_reprocessed

        self.name = node.name
        self.prev_node_type = None
        self.node_type = node.node_type
        self.status = status
        self.reprocess_new_node = False
        self.force_reprocess = False
        self.changes = []  # [Change]
        self.parents = {}  # {Node name: NodeDiff}
        self.children = {}  # {Node name: NodeDiff}

        self._calculate_reprocess_new_node()

    def add_dependency(self, node_diff):
        """Adds a dependency that this node diff has on the given node diff

        :param node_diff: The dependency node diff to add
        :type node_diff: :class:`recipe.diff.node.NodeDiff`
        """

        self.parents[node_diff.name] = node_diff
        node_diff.children[self.name] = self

    def compare_to_previous(self, prev_node):
        """Compares this node to the given node from the previous revision and calculates the diff between the nodes

        :param prev_node: The node from the previous revision
        :type prev_node: :class:`recipe.definition.node.NodeDefinition`
        """

        self.changes = []

        if self.node_type == prev_node.node_type:
            self._compare_node_type(prev_node)
        else:
            self.prev_node_type = prev_node.node_type
            msg = 'Node type changed from %s to %s' % (self.node_type, prev_node.node_type)
            self.changes.append(Change('NODE_TYPE_CHANGE', msg))

        self._compare_dependencies(prev_node)
        self._compare_connections(prev_node)

        self.status = NodeDiff.CHANGED if self.changes else NodeDiff.UNCHANGED
        self._calculate_reprocess_new_node()

    @abstractmethod
    def get_node_type_dict(self):
        """Returns a JSON dict describing the node type details for this node diff

        :returns: The JSON dict describing the node type details
        :rtype: dict
        """

        raise NotImplementedError()

    def set_force_reprocess(self, reprocess_nodes):
        """Sets this node to force to reprocess. The given dict contains node names as keys representing the nodes to
        force to reprocess. Each node name maps to a dict, which is empty for non-recipe nodes. For recipe nodes, the
        dict recursively represents the node names within that recipe that should be foreced to reprocess, and so on.

        :param reprocess_nodes: Dict where each key is a node name mapping recursively to another dict of nodes
        :type reprocess_nodes: dict
        """

        self.force_reprocess = True
        self._calculate_reprocess_new_node()

        for child_node_diff in list(self.children.values()):
            child_node_diff.set_force_reprocess(reprocess_nodes)

    def should_be_copied(self):
        """Indicates whether this node should be copied from the previous recipe during a reprocess

        :returns: Whether this node should be copied
        :rtype: bool
        """

        # Should be copied if node is not deleted from previous recipe and not being created in new recipe
        return self.status != NodeDiff.DELETED and not self.reprocess_new_node

    def should_be_superseded(self):
        """Indicates whether this node should be superseded in the previous recipe during a reprocess

        :returns: Whether this node should be superseded
        :rtype: bool
        """

        # Should be superseded if node is deleted or being replaced
        being_deleted = self.status == NodeDiff.DELETED
        being_replaced = self.status == NodeDiff.CHANGED or (self.status == NodeDiff.UNCHANGED and self.force_reprocess)
        return being_deleted or being_replaced

    def should_be_unpublished(self):
        """Indicates whether this node requires unpublishing as a result of a reprocess

        :returns: Whether this node should be unpublished
        :rtype: bool
        """

        # Deleted nodes should be unpublished, superseded nodes are unpublished when their replacements fully complete
        return self.status == NodeDiff.DELETED

    def _calculate_reprocess_new_node(self):
        """Recalculates the reprocess_new_node field
        """

        if not self._diff_can_be_reprocessed:
            self.reprocess_new_node = False
            return

        reprocess_due_to_status = self.status in NodeDiff.STATUSES_REPROCESS_NEW_NODE
        reprocess_due_to_force = self.force_reprocess and self.status != NodeDiff.DELETED
        self.reprocess_new_node = reprocess_due_to_status or reprocess_due_to_force

    def _compare_connections(self, prev_node):
        """Compares this node's input connections to the input connections of the given node

        :param prev_node: The node from the previous revision
        :type prev_node: :class:`recipe.definition.node.NodeDefinition`
        """

        for connection in list(self._node.connections.values()):
            if connection.input_name not in prev_node.connections:
                self.changes.append(Change('INPUT_NEW', 'New input %s added' % connection.input_name))
            else:
                prev_connection = prev_node.connections[connection.input_name]
                if not connection.is_equal_to(prev_connection):
                    self.changes.append(Change('INPUT_CHANGE', 'Input %s changed' % connection.input_name))

        input_names = list(self._node.connections.keys())
        for prev_input_name in list(prev_node.connections.keys()):
            if prev_input_name not in input_names:
                self.changes.append(Change('INPUT_REMOVED', 'Previous input %s removed' % prev_input_name))

    def _compare_dependencies(self, prev_node):
        """Compares this node's dependencies to the dependencies of the given node

        :param prev_node: The node from the previous revision
        :type prev_node: :class:`recipe.definition.node.NodeDefinition`
        """

        prev_parent_names = list(prev_node.parents.keys())
        for parent_diff in list(self.parents.values()):
            if parent_diff.name not in prev_parent_names:
                self.changes.append(Change('PARENT_NEW', 'New parent node %s added' % parent_diff.name))
            else:
                if parent_diff.status == NodeDiff.CHANGED:
                    self.changes.append(Change('PARENT_CHANGED', 'Parent node %s changed' % parent_diff.name))

        parent_names = list(self.parents.keys())
        for prev_parent_name in list(prev_node.parents.keys()):
            if prev_parent_name not in parent_names:
                self.changes.append(Change('PARENT_REMOVED', 'Previous parent node %s removed' % prev_parent_name))

    @abstractmethod
    def _compare_node_type(self, prev_node):
        """Performs comparison specifc to the node type sublass

        :param prev_node: The node from the previous revision
        :type prev_node: :class:`recipe.definition.node.NodeDefinition`
        """

        raise NotImplementedError()


class JobNodeDiff(NodeDiff):
    """Represents a diff for a job node within a recipe definition
    """

    def __init__(self, job_node, diff_can_be_reprocessed, status=NodeDiff.NEW):
        """Constructor

        :param job_node: The job node from the recipe definition
        :type job_node: :class:`recipe.definition.node.JobNodeDefinition`
        :param diff_can_be_reprocessed: Whether the top-level diff can be reprocessed
        :type diff_can_be_reprocessed: bool
        :param status: The diff status, defaults to NEW
        :type status: string
        """

        super(JobNodeDiff, self).__init__(job_node, diff_can_be_reprocessed, status)

        self.job_type_name = job_node.job_type_name
        self.job_type_version = job_node.job_type_version
        self.revision_num = job_node.revision_num
        self.prev_job_type_name = None
        self.prev_job_type_version = None
        self.prev_revision_num = None

    def get_node_type_dict(self):
        """See :meth:`recipe.diff.node.NodeDiff.get_node_type_dict`
        """

        json_dict = {'node_type': self.node_type, 'job_type_name': self.job_type_name,
                     'job_type_version': self.job_type_version, 'job_type_revision': self.revision_num}

        if self.prev_job_type_name is not None:
            json_dict['prev_job_type_name'] = self.prev_job_type_name
        if self.prev_job_type_version is not None:
            json_dict['prev_job_type_version'] = self.prev_job_type_version
        if self.prev_revision_num is not None:
            json_dict['prev_job_type_revision'] = self.prev_revision_num

        return json_dict

    def _compare_node_type(self, prev_node):
        """See :meth:`recipe.diff.node.NodeDiff._compare_node_type`
        """

        if self.job_type_name != prev_node.job_type_name:
            self.prev_job_type_name = prev_node.job_type_name
            msg = 'Job type changed from %s to %s' % (self.job_type_name, prev_node.job_type_name)
            self.changes.append(Change('JOB_TYPE_CHANGE', msg))

        if self.job_type_version != prev_node.job_type_version:
            self.prev_job_type_version = prev_node.job_type_version
            msg = 'Job type version changed from %s to %s' % (self.job_type_version, prev_node.job_type_version)
            self.changes.append(Change('JOB_TYPE_VERSION_CHANGE', msg))

        if self.revision_num != prev_node.revision_num:
            self.prev_revision_num = prev_node.revision_num
            msg = 'Job type revision changed from %s to %s' % (self.revision_num, prev_node.revision_num)
            self.changes.append(Change('JOB_TYPE_REVISION_CHANGE', msg))


class RecipeNodeDiff(NodeDiff):
    """Represents a diff for a recipe node within a recipe definition
    """

    def __init__(self, recipe_node, diff_can_be_reprocessed, status=NodeDiff.NEW):
        """Constructor

        :param recipe_node: The recipe node from the recipe definition
        :type recipe_node: :class:`recipe.definition.node.RecipeNodeDefinition`
        :param diff_can_be_reprocessed: Whether the top-level diff can be reprocessed
        :type diff_can_be_reprocessed: bool
        :param status: The diff status, defaults to NEW
        :type status: string
        """

        super(RecipeNodeDiff, self).__init__(recipe_node, diff_can_be_reprocessed, status)

        self.recipe_type_name = recipe_node.recipe_type_name
        self.revision_num = recipe_node.revision_num
        self.prev_recipe_type_name = None
        self.prev_revision_num = None
        self.force_reprocess_nodes = {}  # {Node name: dict}

    def get_node_type_dict(self):
        """See :meth:`recipe.diff.node.NodeDiff.get_node_type_dict`
        """

        json_dict = {'node_type': self.node_type, 'recipe_type_name': self.recipe_type_name,
                     'recipe_type_revision': self.revision_num}

        if self.prev_recipe_type_name is not None:
            json_dict['prev_recipe_type_name'] = self.prev_recipe_type_name
        if self.prev_revision_num is not None:
            json_dict['prev_recipe_type_revision'] = self.prev_revision_num

        return json_dict

    def set_force_reprocess(self, reprocess_nodes):
        """See :meth:`recipe.diff.node.NodeDiff.set_force_reprocess`
        """

        super(RecipeNodeDiff, self).set_force_reprocess(reprocess_nodes)

        # Grab sub-node names to force reprocess within this recipe
        if self.name in reprocess_nodes:
            self.force_reprocess_nodes = reprocess_nodes[self.name]

    def _compare_node_type(self, prev_node):
        """See :meth:`recipe.diff.node.NodeDiff._compare_node_type`
        """

        if self.recipe_type_name != prev_node.recipe_type_name:
            self.prev_recipe_type_name = prev_node.recipe_type_name
            msg = 'Recipe type changed from %s to %s' % (self.recipe_type_name, prev_node.recipe_type_name)
            self.changes.append(Change('RECIPE_TYPE_CHANGE', msg))

        if self.revision_num != prev_node.revision_num:
            self.prev_revision_num = prev_node.revision_num
            msg = 'Recipe type revision changed from %s to %s' % (self.revision_num, prev_node.revision_num)
            self.changes.append(Change('RECIPE_TYPE_REVISION_CHANGE', msg))
