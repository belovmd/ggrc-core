# -*- coding: utf-8 -*-

# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Notification handlers for object in the ggrc module.

This module contains all function needed for handling notification objects
needed by ggrc notifications.
"""

# pylint: disable=too-few-public-methods,broad-except

from collections import namedtuple
from datetime import date, datetime, time
from functools import partial
from itertools import chain, izip
from logging import getLogger
from operator import attrgetter

from enum import Enum

from sqlalchemy import inspect
from sqlalchemy.sql.expression import true
from werkzeug.exceptions import InternalServerError

from ggrc import db
from ggrc import notifications
from ggrc.services import signals
from ggrc import models
from ggrc.utils import errors
from ggrc.models.mixins.statusable import Statusable

# pylint: disable=invalid-name
logger = getLogger(__name__)


class Transitions(Enum):
  """Assesment state transitions names."""
  TO_STARTED = "assessment_started"
  TO_COMPLETED = "assessment_completed"
  TO_REVIEW = "assessment_ready_for_review"
  TO_VERIFIED = "assessment_verified"
  TO_REOPENED = "assessment_reopened"


IdValPair = namedtuple("IdValPair", ["id", "val"])

SEND_TIME = time(8, 0)


def _add_notification(obj, notif_type, when=None):
  """Add notification for an object.

  Args:
    obj (Model): an object for which we want te add a notification.
    notif_type (NotificationType): type of notification that we want to store.
    when (datetime): date and time when we want the notification to be sent.
      default value is now.
  """
  if not notif_type:
    return
  if not when:
    when = date.today()
  db.session.add(models.Notification(
      object=obj,
      send_on=when,
      notification_type=notif_type,
  ))


def _has_unsent_notification(notif_type, obj):
  """Check if object has unsent notification of specified type.

  Check if there are unsent notification of `notif_type` type for `obj` object
  in the DB or in current DB session.

  Args:
    notif_type (NotificationType): type of the notifications too look for.
    obj (db.Model): Object for which to look for notifications.

  Returns:
    True if there are unsent notifications and False otherwise.
  """
  notification = _get_unsent_notification(notif_type, obj, for_update=False)
  return notification is not None


def _get_unsent_notification(notif_type, obj, for_update=True):
  """Get object's first unsent notification of specified type.

  Get first `obj` object's unsent notification of type `notif_type`. Note that
  notification is considered unsent if it was not send or the one is repeating.
  Unsent notification present in current DB session has priority over
  notifications stored in DB. If there are not any unsent notifications, None
  will be returned.

  Args:
    notif_type (NotificationType): type of the notifications too look for.
    obj (db.Model): Object for which to look for notifications.
    for_update (bool): Flag indicating the way notification should be selected
      from the DB. If True, `FOR UPDATE` SQL clause will be applied. Defaults
      to True.

  Returns:
    Notification object or None.
  """

  def _get_notif_key(notif):
    """Return key to use during notification comparison."""
    return (notif.object_id,
            notif.object_type,
            notif.notification_type_id or notif.notification_type.id)

  obj_key = (obj.id, obj.type, notif_type.id)
  notifs = (o for o in db.session if isinstance(o, models.Notification))
  for notification in notifs:
    if obj_key == _get_notif_key(notification):
      return notification

  notif_q = db.session.query(
      models.Notification,
  ).filter(
      models.Notification.notification_type_id == notif_type.id,
      models.Notification.object_id == obj.id,
      models.Notification.object_type == obj.type,
      (
          models.Notification.sent_at.is_(None) | (
              models.Notification.repeating == true()
          )
      )
  )

  if for_update:
    notif_q = notif_q.with_for_update()

  return notif_q.first()


def _add_assignable_declined_notif(obj):
  """Add entries for assignable declined notifications.

  Args:
    obj (Assignable): Any object with assignable mixin for which we want to add
      notifications.
  """
  # pylint: disable=protected-access
  name = "{}_declined".format(obj._inflector.table_singular)
  notif_type = models.NotificationType.query.filter_by(name=name).first()

  if not _has_unsent_notification(notif_type, obj):
    _add_notification(obj, notif_type)


def _add_assessment_updated_notif(obj):
  """Add a notification record on the change of an object.

  If the same notification type for the object already exists and has not been
  sent yet, do not do anything. The same if there already exist unsent status
  change notifications for the object.

  Args:
    obj (models.mixins.Assignable): an object for which to add a notification
  """
  # If there already exists a status change notification, an assessment updated
  # notification should not be sent, and is thus not added.
  notif_type = models.NotificationType.query.filter_by(
      name="assessment_updated").first()

  unsent_notification = _get_unsent_notification(notif_type, obj)
  if unsent_notification is None:
    _add_notification(obj, notif_type)
  else:
    unsent_notification.updated_at = datetime.utcnow()
    db.session.add(unsent_notification)


def _add_state_change_notif(obj, state_change, remove_existing=False):
  """Add a notification record on changing the given object's status.

  If the same notification type for the object already exists and has not been
  sent yet, do not do anything.

  Args:
    obj (models.mixins.Assignable): an object for which to add a notification
    state_change (Transitions): the state transition that has happened
    remove_existing (bool): whether or not to remove all exisiting state change
      notifications for `obj`
  """
  # Assessment updated notifications should not be sent if there is a state
  # change notification - we must thus delete the former.
  notif_type_names = ["assessment_updated"]

  if remove_existing:
    notif_type_names.extend(item.value for item in Transitions)
    notif_type_names.append("assessment_declined")

  notif_types = models.NotificationType.query.filter(
      models.NotificationType.name.in_(notif_type_names)
  )
  notif_type_ids = [ntype.id for ntype in notif_types]

  models.Notification.query.filter(
      models.Notification.object_id == obj.id,
      models.Notification.object_type == obj.type,
      models.Notification.notification_type_id.in_(notif_type_ids)
  ).delete(synchronize_session='fetch')

  notif_type = models.NotificationType.query.filter_by(
      name=state_change.value).first()

  if not _has_unsent_notification(notif_type, obj):
    _add_notification(obj, notif_type)


def handle_assignable_modified(obj, event=None):  # noqa: ignore=C901
  """A handler for the Assignable object modified event.

  Args:
    obj (models.mixins.Assignable): an object that has been modified
    event (models.Event): event which lead to object modification
  """
  attrs = inspect(obj).attrs
  status_history = attrs["status"].history

  old_state = status_history.deleted[0] if status_history.deleted else None
  new_state = status_history.added[0] if status_history.added else None

  # The transition from "ready to review" to "in progress" happens when an
  # object is declined, so this is used as a triger for declined notifications.
  if (old_state == Statusable.DONE_STATE and
          new_state == Statusable.PROGRESS_STATE):
    _add_assignable_declined_notif(obj)

  transitions_map = {
      (Statusable.START_STATE, Statusable.PROGRESS_STATE):
          Transitions.TO_STARTED,
      (Statusable.START_STATE, Statusable.FINAL_STATE):
          Transitions.TO_COMPLETED,
      (Statusable.START_STATE, Statusable.DONE_STATE):
          Transitions.TO_REVIEW,
      (Statusable.PROGRESS_STATE, Statusable.FINAL_STATE):
          Transitions.TO_COMPLETED,
      (Statusable.PROGRESS_STATE, Statusable.DONE_STATE):
          Transitions.TO_REVIEW,
      (Statusable.DONE_STATE, Statusable.FINAL_STATE):
          Transitions.TO_VERIFIED,
      (Statusable.FINAL_STATE, Statusable.PROGRESS_STATE):
          Transitions.TO_REOPENED,
      (Statusable.DONE_STATE, Statusable.PROGRESS_STATE):
          Transitions.TO_REOPENED,
  }

  state_change = transitions_map.get((old_state, new_state))
  if state_change:
    _add_state_change_notif(obj, state_change, remove_existing=True)

  is_changed = obj.has_acl_changes()

  for attr_name, val in attrs.items():
    if attr_name in notifications.IGNORE_ATTRS:
      continue

    if val.history.has_changes():
      # the exact order of recipients in the string does not matter, hence the
      # need for an extra check
      if attr_name == u"recipients" and not _recipients_changed(val.history):
        continue
      is_changed = True
      break

  is_changed = is_changed or \
      _ca_values_changed(obj, event)  # CA check only if needed

  if not is_changed:
    return  # no changes detected, nothing left to do

  # When modified, a done Assessment gets automatically reopened, but that is
  # not directly observable via status change history, thus an extra check.
  if obj.status in Statusable.DONE_STATES:
    _add_state_change_notif(obj, Transitions.TO_REOPENED, remove_existing=True)
  elif obj.status == Statusable.START_STATE:
    _add_state_change_notif(obj, Transitions.TO_STARTED, remove_existing=True)

  _add_assessment_updated_notif(obj)


def _ca_values_changed(obj, event):
  """Check if object's custom attribute values have been changed.

  The changes are determined by comparing the current object custom attributes
  with the CA values from object's last known revision. If the latter does not
  exist, it is considered that there are no changes - since the object has
  apparently just been created.

  Args:
    obj (models.mixins.Assignable): the object to check
    event (models.Event): event which lead to object modification

  Returns:
    (bool) True if there is a change to any of the CA values, False otherwise.
  """
  filters = [models.Revision.resource_id == obj.id,
             models.Revision.resource_type == obj.type]
  if event and event.revisions:
    filters.append(
        ~models.Revision.id.in_(
            [rev.id for rev in event.revisions
             if rev.resource_type == obj.type and rev.resource_id == obj.id]
        )
    )
  revision = db.session.query(
      models.Revision
  ).filter(
      *filters
  ).order_by(models.Revision.id.desc()).first()
  if not revision:
    raise InternalServerError(errors.MISSING_REVISION)
  new_attrs = {
      "custom_attribute_values":
      [value.log_json() for value in obj.custom_attribute_values],
      "custom_attribute_definitions":
      [defn.log_json() for defn in obj.custom_attribute_definitions]
  }
  return any(notifications.get_updated_cavs(new_attrs, revision.content))


def _align_by_ids(items, items2):
  """Generate pairs of items from both iterables, matching them by IDs.

  The items within each iterable must have a unique id attribute (with a value
  other than None). If an item from one iterable does not have a matching item
  in the other, None is used for the missing item.

  Args:
    items: The first iterable.
    items2: The second iterable.

  Yields:
    Pairs of items with matching IDs (one of the items can be None).
  """
  STOP = Ellipsis  # iteration sentinel alias  # pylint: disable=invalid-name

  sort_by_id = partial(sorted, key=attrgetter("id"))
  items = chain(sort_by_id(items), [STOP])
  items2 = chain(sort_by_id(items2), [STOP])

  first, second = next(items), next(items2)

  while first is not STOP or second is not STOP:
    min_id = min(pair.id for pair in (first, second) if pair is not STOP)
    id_one, id_two = getattr(first, "id", None), getattr(second, "id", None)

    yield (first if id_one == min_id else None,
           second if id_two == min_id else None)

    if id_one == min_id:
      first = next(items)
    if id_two == min_id:
      second = next(items2)


def _recipients_changed(history):
  """Check if the recipients attribute has been semantically modified.

  The recipients attribute is a comma-separated string, and the exact order of
  the items in it does not matter, i.e. it is not considered a change.

  Args:
    history (sqlalchemy.orm.attributes.History): recipients' value history

  Returns:
    True if there was a (semantic) change, False otherwise
  """
  old_val = history.deleted[0] if history.deleted else ""
  new_val = history.added[0] if history.added else ""

  if old_val is None:
    old_val = ""

  if new_val is None:
    new_val = ""

  return sorted(old_val.split(",")) != sorted(new_val.split(","))


def handle_assignable_created(objects):
  """Handler for new assignable objects."""
  names = ["{}_open".format(obj._inflector.table_singular) for obj in objects]
  notif_types = models.NotificationType.query.filter(
      models.NotificationType.name.in_(set(names))
  )
  notif_types_map = {notif.name: notif for notif in notif_types}
  for obj, notif_name in zip(objects, names):
    notif_type = notif_types_map[notif_name]
    _add_notification(obj, notif_type)


def handle_assignable_deleted(obj):
  models.Notification.query.filter_by(
      object_id=obj.id,
      object_type=obj.type,
  ).delete()


def handle_reminder(obj, reminder_type):
  """Handles reminders for an object

  Args:
    obj: Object to process
    reminder_type: Reminder handler to use for processing event
    """
  if reminder_type in obj.REMINDERABLE_HANDLERS:
    reminder_settings = obj.REMINDERABLE_HANDLERS[reminder_type]
    handler = reminder_settings['handler']
    data = reminder_settings['data']
    handler(obj, data)


def handle_comment_created(obj, src):
  """Add notification entries for new comments.

  Args:
    obj (Comment): New comment.
    src (dict): Dictionary containing the comment post request data.
  """
  if src.get("send_notification"):
    notif_type = models.NotificationType.query.filter_by(
        name="comment_created").first()
    _add_notification(obj, notif_type)


def handle_relationship_altered(rel):
  """Handle creation or deletion of a relationship between two objects.

  Relationships not involving an Assessment are ignored. For others, if a
  Person or a Document is assigned/attached (or removed from) an Assessment,
  that is considered an Assessment modification and hence a notification is
  created (unless the Assessment has not been started yet, of course).

  Args:
    rel (Relationship): Created (or deleted) relationship instance.
  """
  if rel.source.type != u"Assessment" != rel.destination.type:
    return

  asmt, other = rel.source, rel.destination
  if asmt.type != u"Assessment":
    asmt, other = other, asmt

  status_is_changed = inspect(asmt).attrs.status.history.has_changes()
  if other.type in (u"Evidence", u"Person", u"Snapshot"):
    if asmt.status != Statusable.START_STATE:
      _add_assessment_updated_notif(asmt)
    elif not status_is_changed:
      _add_state_change_notif(
          asmt, Transitions.TO_STARTED, remove_existing=True)

  if other.type in (u"Evidence", u"Snapshot"):
    # when modified, a done Assessment gets automatically reopened
    if asmt.status in Statusable.DONE_STATES and not status_is_changed:
      _add_state_change_notif(
          asmt, Transitions.TO_REOPENED, remove_existing=True)


def register_handlers():  # noqa: C901
  """Register listeners for notification handlers."""

  # Variables are used as listeners, and arguments are needed for callback
  # functions.
  #
  # pylint: disable=unused-argument,unused-variable

  @signals.Restful.model_deleted.connect_via(models.Assessment)
  def assignable_deleted_listener(sender, obj=None, src=None, service=None):
    """Listener for deletion of assessments."""
    try:
      handle_assignable_deleted(obj)
    except Exception as ex:
      logger.warning(
          "Unable to send notification about deletion of"
          " Assessment: %s.\n Error: %s", obj.id, ex.message
      )

  @signals.Restful.model_put.connect_via(models.Assessment)
  def assignable_modified_listener(sender, obj=None, src=None, service=None):
    """Listener for modification of assessments."""
    try:
      handle_assignable_modified(obj)
    except Exception as ex:
      logger.warning(
          "Unable to send notification about modification of"
          " Assessment: %s.\n Error: %s", obj.id, ex.message
      )

  @signals.Restful.model_put_before_commit.connect_via(models.Assessment)
  def assignable_put_listener(sender, obj=None, event=None, **kwargs):
    """Assessment put before commit listener."""
    try:
      handle_assignable_modified(obj, event)
    except Exception as ex:
      logger.warning(
          "Unable to send notification about modification of"
          " Assessment: %s.\n Error: %s", obj.id, ex.message
      )

  @signals.Restful.collection_posted.connect_via(models.Assessment)
  def assignable_created_listener(sender, objects=None, **kwargs):
    """Listener for creation of assessments."""
    try:
      handle_assignable_created(objects)
    except Exception as ex:
      object_ids = (o.id for o in objects)
      logger.warning(
          "Unable to send notification about creation of"
          " Assessments: %s.\n Error: %s", object_ids, ex.message
      )

  @signals.Restful.model_put.connect_via(models.Assessment)
  def assessment_send_reminder(sender, obj=None, src=None, service=None):
    """Assessment put listener."""
    reminder_type = src.get("reminderType", False)
    if reminder_type:
      try:
        handle_reminder(obj, reminder_type)
      except Exception as ex:
        logger.warning(
            "Unable to send notification reminder for"
            " Assessment: %s.\n Error: %s", obj.id, ex.message
        )

  @signals.Restful.collection_posted.connect_via(models.Comment)
  def comment_created_listener(sender, objects=None, sources=None, **kwargs):
    """Listener for comments posted."""
    for obj, src in izip(objects, sources):
      try:
        handle_comment_created(obj, src)
      except Exception as ex:
        logger.warning(
            "Unable to send notification about"
            " Comment: %s.\n Error: %s", obj.id, ex.message
        )

  @signals.Restful.model_posted.connect_via(models.Relationship)
  @signals.Restful.model_deleted.connect_via(models.Relationship)
  def relationship_altered_listener(sender, obj=None, src=None, service=None):
    """Listener for creation/deletion of relationships."""
    try:
      handle_relationship_altered(obj)
    except Exception as ex:
      logger.warning(
          "Unable to send notification about relationship"
          " Source:%s-%s <-> Destination:%s-%s.\n Error: %s",
          obj.source_type,
          obj.source_id,
          obj.destination_type,
          obj.destination_id,
          ex.message
      )
