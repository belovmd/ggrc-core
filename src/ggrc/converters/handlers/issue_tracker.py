# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Handlers for Issue Tracker fields"""

from ggrc.converters.handlers import handlers
from ggrc.models.hooks.issue_tracker import \
    issue_tracker_params_container as params_container
from ggrc.converters import errors


class IssueTrackerColumnHandler(handlers.ColumnHandler):
  """Column handler used for Issue Tracker related fields.

  This class provides method for Issue Tracker fields export.
  """
  def get_value(self):
    return self.row_converter.issue_tracker.get(self.key, "")


class PriorityColumnHandler(IssueTrackerColumnHandler):
  """Column handler for Priority Issue Tracker field."""
  def __init__(self, row_converter, key, **options):
    self.valid_states = \
        params_container.IssueTrackerParamsContainer.AVAILABLE_PRIORITIES
    super(PriorityColumnHandler, self).__init__(row_converter, key, **options)

  def parse_item(self):
    value = self.raw_value.upper()
    if value not in self.valid_states:
      self.add_warning(errors.WRONG_VALUE, column_name=self.display_name)
      return None
    return value

  def set_obj_attr(self):
    if self.dry_run or not self.value:
      return
    self.row_converter.issue_tracker[self.key] = self.value


class SeverityColumnHandler(IssueTrackerColumnHandler):
  """Column handler for Priority Issue Tracker field."""
  def __init__(self, row_converter, key, **options):
    self.valid_states = \
      params_container.IssueTrackerParamsContainer.AVAILABLE_SEVERITIES
    super(SeverityColumnHandler, self).__init__(row_converter, key, **options)

  def parse_item(self):
    value = self.raw_value.upper()
    if value not in self.valid_states:
      self.add_warning(errors.WRONG_VALUE, column_name=self.display_name)
      return None
    return value

  def set_obj_attr(self):
    if self.dry_run or not self.value:
      return
    self.row_converter.issue_tracker[self.key] = self.value
