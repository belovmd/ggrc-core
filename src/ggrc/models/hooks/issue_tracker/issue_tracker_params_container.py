# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Container for Issue Tracker parameters."""

# pylint: disable=too-many-instance-attributes

from ggrc.models import exceptions
from ggrc.utils.custom_dict import MissingKeyDict


class IssueTrackerParamsContainer(object):
  """Container for Issue Tracker parameters."""

  ISSUE_TRACKER_FIELDS_MAPPING = MissingKeyDict({
      "issue_severity": "severity",
      "issue_priority": "priority",
      "issue_type": "type",
      "cc_list": "ccs",
  })

  # Fields which IssueTracker can store.
  ALL_ISSUE_TRACKER_FIELDS = (
      "issue_priority", "issue_severity", "title", "issue_type",
      "status", "verifier", "assignee", "reporter", "cc_list", "component_id",
      "comment", "hotlist_id",
  )

  # Fields which stored in 'issuetracker_issue' table.
  GGRC_REQUIRED_FIELDS = (
      "enabled", "issue_priority", "issue_severity", "title", "issue_type",
      "status", "assignee", "cc_list", "component_id", "hotlist_id",
  )

  # Available values for Issue Tracker severity and priority.
  AVAILABLE_PRIORITIES = ("P0", "P1", "P2", "P3", "P4", )
  AVAILABLE_SEVERITIES = ("S0", "S1", "S2", "S3", "S4", )
  AVAILABLE_TYPES = ("PROCESS", "BUG")

  def __init__(self):
    """Basic initialization."""
    self.enabled = None
    self.title = None
    self.issue_type = None
    self.status = None
    self.verifier = None
    self.assignee = None
    self.reporter = None
    self.cc_list = None

    self._component_id = None
    self._hotlist_id = None
    self._issue_priority = None
    self._issue_severity = None
    self._comments = []

  @property
  def component_id(self):
    """Returns 'component_id'."""
    return self._component_id

  @component_id.setter
  def component_id(self, value):
    """Validate and set 'component_id'."""
    if not value:
      return

    try:
      self._component_id = int(value)
    except (TypeError, ValueError):
      raise exceptions.ValidationError("Component ID must be a number.")

  @property
  def hotlist_id(self):
    """Returns 'hotlist_id'."""
    return self._hotlist_id

  @hotlist_id.setter
  def hotlist_id(self, value):
    """Validate and set 'hotlist_id'."""
    if not value:
      return

    try:
      self._hotlist_id = int(value)
    except (TypeError, ValueError):
      raise exceptions.ValidationError("Hotlist ID must be a number.")

  @property
  def issue_priority(self):
    """Returns issue priority for Issue Tracker."""
    return self._issue_priority

  @issue_priority.setter
  def issue_priority(self, value):
    """Validate and set issue priority."""
    if not value:
      return

    if value not in self.AVAILABLE_PRIORITIES:
      raise exceptions.ValidationError(
          "Invalid priority value: {}. Valid priority values: '{}'"
          .format(value, ", ".join(self.AVAILABLE_PRIORITIES))
      )
    self._issue_priority = value

  @property
  def issue_severity(self):
    """Returns issue severity for Issue Tracker."""
    return self._issue_severity

  @issue_severity.setter
  def issue_severity(self, value):
    """Validate and set issue severity."""
    if not value:
      return

    if value not in self.AVAILABLE_SEVERITIES:
      raise exceptions.ValidationError(
          "Invalid severity value: {}. Valid severity values: '{}'"
          .format(value, ", ".join(self.AVAILABLE_SEVERITIES))
      )
    self._issue_severity = value

  @property
  def comment(self):
    """Returns joined comments."""
    return "\n\n".join(self._comments) if self._comments else None

  def add_comment(self, comment):
    """Append comment into container."""
    self._comments.append(comment)

  def is_empty(self):
    """Returns True if all Issue Tracker fields are empty."""
    return all(
        not getattr(self, field)
        for field in self.ALL_ISSUE_TRACKER_FIELDS
    )

  def get_issue_tracker_params(self):
    """Returns dict with non-null issue tracker params."""
    fields = self.ALL_ISSUE_TRACKER_FIELDS
    name_mapping = self.ISSUE_TRACKER_FIELDS_MAPPING
    issue_tracker_params = {
        name_mapping[field]: getattr(self, field) for field in fields
        if getattr(self, field) is not None
    }

    # hotlist_ids should be sent to issue tracker as list.
    hotlist_ids = [self.hotlist_id, ] if self.hotlist_id else []
    if hotlist_ids:
      issue_tracker_params["hotlist_ids"] = hotlist_ids

    # And we don't need to send hotlist_id, because it uses for GGRC purposes
    if "hotlist_id" in issue_tracker_params:
      del issue_tracker_params["hotlist_id"]

    return issue_tracker_params

  def get_params_for_ggrc_object(self):
    """Returns dict with all issue tracker fields."""
    fields = self.GGRC_REQUIRED_FIELDS
    return {
        field: getattr(self, field) for field in fields
        if getattr(self, field) is not None
    }
