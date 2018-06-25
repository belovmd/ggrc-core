# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module containing Cycle tasks.
"""

from logging import getLogger
from sqlalchemy import orm
import sqlalchemy as sa
from sqlalchemy.ext import hybrid
from werkzeug.exceptions import BadRequest

from ggrc import builder
from ggrc import db
from ggrc import login
from ggrc.access_control import roleable
from ggrc.fulltext import attributes as ft_attributes
from ggrc.fulltext import mixin as ft_mixin
from ggrc.models import mixins
from ggrc.models import reflection
from ggrc.models import relationship
from ggrc.models import types
from ggrc.models.mixins import base
from ggrc_workflows.models.cycle import Cycle
from ggrc_workflows.models.workflow import Workflow
from ggrc_workflows.models.cycle_task_group import CycleTaskGroup
from ggrc_workflows.models import mixins as wf_mixins


LOGGER = getLogger(__name__)


class CycleTaskGroupObjectTask(roleable.Roleable,
                               wf_mixins.CycleTaskStatusValidatedMixin,
                               mixins.WithLastDeprecatedDate,
                               mixins.Timeboxed,
                               relationship.Relatable,
                               mixins.Notifiable,
                               mixins.Described,
                               mixins.Titled,
                               mixins.Slugged,
                               mixins.Base,
                               base.ContextRBAC,
                               ft_mixin.Indexed,
                               db.Model):
  """Cycle task model
  """
  __tablename__ = 'cycle_task_group_object_tasks'

  readable_name_alias = 'cycle task'

  _title_uniqueness = False

  IMPORTABLE_FIELDS = (
      'slug', 'title', 'description', 'start_date',
      'end_date', 'finished_date', 'verified_date',
      'status', '__acl__:Task Assignees', '__acl__:Task Secondary Assignees',
  )

  @classmethod
  def generate_slug_prefix(cls):
    return "CYCLETASK"

  # Note: this statuses are used in utils/query_helpers to filter out the tasks
  # that should be visible on My Tasks pages.

  PROPERTY_TEMPLATE = u"task {}"

  _fulltext_attrs = [
      ft_attributes.DateFullTextAttr("end_date", 'end_date',),
      ft_attributes.FullTextAttr("group title",
                                 'cycle_task_group',
                                 ['title'],
                                 False),
      ft_attributes.FullTextAttr("object approval",
                                 'object_approval',
                                 with_template=False),
      ft_attributes.FullTextAttr("cycle title", 'cycle', ['title'], False),
      ft_attributes.FullTextAttr("group assignee",
                                 lambda x: x.cycle_task_group.contact,
                                 ['email', 'name'],
                                 False),
      ft_attributes.FullTextAttr("cycle assignee",
                                 lambda x: x.cycle.contact,
                                 ['email', 'name'],
                                 False),
      ft_attributes.DateFullTextAttr(
          "group due date",
          lambda x: x.cycle_task_group.next_due_date,
          with_template=False),
      ft_attributes.DateFullTextAttr("cycle due date",
                                     lambda x: x.cycle.next_due_date,
                                     with_template=False),
      ft_attributes.MultipleSubpropertyFullTextAttr("comments",
                                                    "cycle_task_entries",
                                                    ["description"]),
      "folder",
  ]

  AUTO_REINDEX_RULES = [
      ft_mixin.ReindexRule("CycleTaskEntry",
                           lambda x: x.cycle_task_group_object_task),
  ]

  cycle_id = db.Column(
      db.Integer,
      db.ForeignKey('cycles.id', ondelete="CASCADE"),
      nullable=False,
  )
  cycle_task_group_id = db.Column(
      db.Integer,
      db.ForeignKey('cycle_task_groups.id', ondelete="CASCADE"),
      nullable=False,
  )
  task_group_task_id = db.Column(
      db.Integer, db.ForeignKey('task_group_tasks.id'), nullable=True)
  task_group_task = db.relationship(
      "TaskGroupTask",
      foreign_keys="CycleTaskGroupObjectTask.task_group_task_id"
  )
  task_type = db.Column(db.String(length=250), nullable=False)
  response_options = db.Column(types.JsonType(), nullable=False, default=[])
  selected_response_options = db.Column(types.JsonType(),
                                        nullable=False,
                                        default=[])

  sort_index = db.Column(db.String(length=250), default="", nullable=False)

  finished_date = db.Column(db.DateTime)
  verified_date = db.Column(db.DateTime)

  @hybrid.hybrid_property
  def object_approval(self):
    return self.cycle.workflow.object_approval

  @object_approval.expression
  def object_approval(cls):  # pylint: disable=no-self-argument
    return sa.select([
        Workflow.object_approval,
    ]).where(
        sa.and_((Cycle.id == cls.cycle_id), (Cycle.workflow_id == Workflow.id))
    ).label(
        'object_approval'
    )

  @builder.simple_property
  def folder(self):
    if self.cycle:
      return self.cycle.folder
    return ""

  @property
  def cycle_task_objects_for_cache(self):
    """Changing task state must invalidate `workflow_state` on objects
    """
    return [(object_.__class__.__name__, object_.id) for object_ in
            self.related_objects]  # pylint: disable=not-an-iterable

  _api_attrs = reflection.ApiAttributes(
      'cycle',
      'cycle_task_group',
      'task_group_task',
      'cycle_task_entries',
      'sort_index',
      'task_type',
      'response_options',
      'selected_response_options',
      reflection.Attribute('related_sources', create=False, update=False),
      reflection.Attribute('related_destinations', create=False, update=False),
      reflection.Attribute('object_approval', create=False, update=False),
      reflection.Attribute('finished_date', create=False, update=False),
      reflection.Attribute('verified_date', create=False, update=False),
      reflection.Attribute('allow_change_state', create=False, update=False),
      reflection.Attribute('folder', create=False, update=False),
      reflection.Attribute('workflow', create=False, update=False),
      reflection.Attribute('workflow_title', create=False, update=False),
      reflection.Attribute('cycle_task_group_title', create=False,
                           update=False),
  )

  default_description = "<ol>"\
                        + "<li>Expand the object review task.</li>"\
                        + "<li>Click on the Object to be reviewed.</li>"\
                        + "<li>Review the object in the Info tab.</li>"\
                        + "<li>Click \"Approve\" to approve the object.</li>"\
                        + "<li>Click \"Decline\" to decline the object.</li>"\
                        + "</ol>"

  _aliases = {
      "title": "Summary",
      "description": "Task Details",
      "finished_date": {
          "display_name": "Actual Finish Date",
          "description": ("Make sure that 'Actual Finish Date' isn't set, "
                          "if cycle task state is <'Assigned' / "
                          "'In Progress' / 'Declined' / 'Deprecated'>. "
                          "Type double dash '--' into "
                          "'Actual Finish Date' cell to remove it.")
      },
      "verified_date": {
          "display_name": "Actual Verified Date",
          "description": ("Make sure that 'Actual Verified Date' isn't set, "
                          "if cycle task state is <'Assigned' / "
                          "'In Progress' / 'Declined' / 'Deprecated' / "
                          "'Finished'>. Type double dash '--' into "
                          "'Actual Verified Date' cell to remove it.")
      },
      "cycle": {
          "display_name": "Cycle",
          "filter_by": "_filter_by_cycle",
      },
      "cycle_task_group": {
          "display_name": "Task Group",
          "mandatory": True,
          "filter_by": "_filter_by_cycle_task_group",
      },
      "task_type": {
          "display_name": "Task Type",
          "mandatory": True,
      },
      "end_date": "Due Date",
      "start_date": "Start Date",
  }

  @builder.simple_property
  def cycle_task_group_title(self):
    """Property. Returns parent CycleTaskGroup title."""
    return self.cycle_task_group.title

  @builder.simple_property
  def workflow_title(self):
    """Property. Returns parent Workflow's title."""
    return self.workflow.title

  @builder.simple_property
  def workflow(self):
    """Property which returns parent workflow object."""
    return self.cycle.workflow

  @builder.simple_property
  def related_objects(self):
    """Compute and return a list of all the objects related to this cycle task.

    Related objects are those that are found either on the "source" side, or
    on the "destination" side of any of the instance's relations.

    Returns:
      (list) All objects related to the instance.
    """
    # pylint: disable=not-an-iterable
    sources = [r.source for r in self.related_sources]
    destinations = [r.destination for r in self.related_destinations]
    return sources + destinations

  @builder.simple_property
  def allow_change_state(self):
    return self.cycle.is_current and self.current_user_wfa_or_assignee()

  def current_user_wfa_or_assignee(self):
    """Current user is WF Admin, Assignee or Secondary Assignee for self."""
    wfa_ids = self.workflow.get_person_ids_for_rolename("Admin")
    ta_ids = self.get_person_ids_for_rolename("Task Assignees")
    tsa_ids = self.get_person_ids_for_rolename("Task Secondary Assignees")
    return login.get_current_user_id() in set().union(wfa_ids, ta_ids, tsa_ids)

  @classmethod
  def _filter_by_cycle(cls, predicate):
    """Get query that filters cycle tasks by related cycles.

    Args:
      predicate: lambda function that excepts a single parameter and returns
      true of false.

    Returns:
      An sqlalchemy query that evaluates to true or false and can be used in
      filtering cycle tasks by related cycles.
    """
    return Cycle.query.filter(
        (Cycle.id == cls.cycle_id) &
        (predicate(Cycle.slug) | predicate(Cycle.title))
    ).exists()

  @classmethod
  def _filter_by_cycle_task_group(cls, predicate):
    """Get query that filters cycle tasks by related cycle task groups.

    Args:
      predicate: lambda function that excepts a single parameter and returns
      true of false.

    Returns:
      An sqlalchemy query that evaluates to true or false and can be used in
      filtering cycle tasks by related cycle task groups.
    """
    return CycleTaskGroup.query.filter(
        (CycleTaskGroup.id == cls.cycle_id) &
        (predicate(CycleTaskGroup.slug) | predicate(CycleTaskGroup.title))
    ).exists()

  @classmethod
  def eager_query(cls):
    """Add cycle task entries to cycle task eager query

    This function adds cycle_task_entries as a join option when fetching cycles
    tasks, and makes sure that with one query we fetch all cycle task related
    data needed for generating cycle taks json for a response.

    Returns:
      a query object with cycle_task_entries added to joined load options.
    """
    query = super(CycleTaskGroupObjectTask, cls).eager_query()
    return query.options(
        orm.joinedload('cycle')
           .joinedload('workflow')
           .undefer_group('Workflow_complete'),
        orm.joinedload('cycle_task_entries'),
    )

  @classmethod
  def indexed_query(cls):
    return super(CycleTaskGroupObjectTask, cls).indexed_query().options(
        orm.Load(cls).load_only(
            "end_date",
            "start_date",
            "created_at",
            "updated_at"
        ),
        orm.Load(cls).joinedload("cycle_task_group").load_only(
            "id",
            "title",
            "end_date",
            "next_due_date",
        ),
        orm.Load(cls).joinedload("cycle").load_only(
            "id",
            "title",
            "next_due_date"
        ),
        orm.Load(cls).joinedload("cycle_task_group").joinedload(
            "contact"
        ).load_only(
            "email",
            "name",
            "id"
        ),
        orm.Load(cls).joinedload("cycle").joinedload(
            "contact"
        ).load_only(
            "email",
            "name",
            "id"
        ),
        orm.Load(cls).subqueryload("cycle_task_entries").load_only(
            "description",
            "id"
        ),
        orm.Load(cls).joinedload("cycle").joinedload("workflow").undefer_group(
            "Workflow_complete"
        ),
    )

  def log_json(self):
    out_json = super(CycleTaskGroupObjectTask, self).log_json()
    out_json["folder"] = self.folder
    return out_json

  @classmethod
  def bulk_update(cls, src):
    """Update statuses for bunch of tasks in a bulk.

    Args:
        src: input json with next structure:
          [{"status": "Assigned", "id": 1}, {"status": "In Progress", "id": 2}]

    Returns:
        list of updated_instances
    """
    new_prv_state_map = {
        cls.DEPRECATED: (cls.ASSIGNED, cls.IN_PROGRESS, cls.FINISHED,
                         cls.VERIFIED, cls.DECLINED),
        cls.IN_PROGRESS: (cls.ASSIGNED, ),
        cls.FINISHED: (cls.IN_PROGRESS, cls.DECLINED),
        cls.VERIFIED: (cls.FINISHED, ),
        cls.DECLINED: (cls.FINISHED, ),
        cls.ASSIGNED: (),
    }
    uniq_states = set([item['state'] for item in src])
    if len(list(uniq_states)) != 1:
      raise BadRequest("Request's JSON contains multiple statuses for "
                       "CycleTasks")
    new_state = uniq_states.pop()
    LOGGER.info("Do bulk update CycleTasks with '%s' status", new_state)
    if new_state not in cls.VALID_STATES:
      raise BadRequest("Request's JSON contains invalid statuses for "
                       "CycleTasks")
    prv_states = new_prv_state_map[new_state]
    all_ids = {item['id'] for item in src}
    # Eagerly loading is needed to get user permissions for CycleTask faster
    updatable_objects = cls.eager_query().filter(
        cls.id.in_(list(all_ids)),
        cls.status.in_(prv_states))
    if new_state in (cls.VERIFIED, cls.DECLINED):
      updatable_objects = [obj for obj in updatable_objects
                           if obj.cycle.is_verification_needed]
    # Bulk update works only on MyTasks page. Don't need to check for
    # WorkflowMembers' permissions here. User should update only his own tasks.
    updatable_objects = [obj for obj in updatable_objects
                         if obj.current_user_wfa_or_assignee()]
    # Queries count is constant because we are using eager query for objects.
    for obj in updatable_objects:
      obj.status = new_state
      obj.modified_by_id = login.get_current_user_id()
    return updatable_objects


class CycleTaskable(object):
  """ Requires the Relatable mixin, otherwise cycle_task_group_object_tasks
  fails to fetch related objects
  """
  @builder.simple_property
  def cycle_task_group_object_tasks(self):
    """ Lists all the cycle tasks related to a certain object
    """
    sources = [r.CycleTaskGroupObjectTask_source
               for r in self.related_sources
               if r.CycleTaskGroupObjectTask_source is not None]
    destinations = [r.CycleTaskGroupObjectTask_destination
                    for r in self.related_destinations
                    if r.CycleTaskGroupObjectTask_destination is not None]
    return sources + destinations

  @classmethod
  def eager_query(cls):
    query = super(CycleTaskable, cls).eager_query()
    return query.options(
        orm.subqueryload('related_sources')
           .joinedload('CycleTaskGroupObjectTask_source')
           .undefer_group('CycleTaskGroupObjectTask_complete')
           .joinedload('cycle'),
        orm.subqueryload('related_destinations')
           .joinedload('CycleTaskGroupObjectTask_destination')
           .undefer_group('CycleTaskGroupObjectTask_complete')
           .joinedload('cycle')
    )
