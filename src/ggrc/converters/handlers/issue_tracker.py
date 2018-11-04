# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Handlers for Issue Tracker fields"""

import re

from ggrc.converters.handlers import handlers
from ggrc.models.hooks.issue_tracker import \
    issue_tracker_params_container as params_container
from ggrc.converters import errors
from ggrc.integrations.constants import DEFAULT_ISSUETRACKER_VALUES as \
    default_values


class IssueTrackerColumnHandler(handlers.ColumnHandler):
  """Column handler used for Issue Tracker related fields.

  This class provides method for Issue Tracker fields export and Issue Traceker
  default values.
  """

  def get_value(self):
    return self.row_converter.issue_tracker.get(self.key, "")

  def set_obj_attr(self):
    if self.dry_run or not self.value:
      return
    self.row_converter.issue_tracker[self.key] = self.value


class IssueTrackerWithValidStates(IssueTrackerColumnHandler):
  """Column handler for columns with available valid states"""

  available_items = {
      'issue_type':
          params_container.IssueTrackerParamsContainer.AVAILABLE_TYPES,
      'issue_priority':
          params_container.IssueTrackerParamsContainer.AVAILABLE_PRIORITIES,
      'issue_severity':
          params_container.IssueTrackerParamsContainer.AVAILABLE_SEVERITIES,
  }

  def __init__(self, row_converter, key, **options):
    self.valid_states = self.available_items.get(key)
    super(IssueTrackerWithValidStates, self).__init__(row_converter,
                                                      key,
                                                      **options)

  def parse_item(self):
    value = self.raw_value.upper()
    if value not in self.valid_states:
      self.add_warning(errors.WRONG_VALUE_DEFAULT,
                       column_name=self.display_name)
      return default_values.get(self.key)
    return value


class AddsColumnHandler(IssueTrackerColumnHandler):
  """Column handler for hotlist and components ids"""

  def parse_item(self):
    try:
      value = int(self.raw_value)
    except ValueError:
      self.add_warning(errors.WRONG_VALUE_DEFAULT,
                       column_name=self.display_name)
      return default_values.get(self.key)
    return value


class TitleColumnHandler(IssueTrackerColumnHandler):
  """Column handler for Issue title for IssueTracked models"""

  def get_value(self):
    return self.row_converter.issue_tracker.get("title", "")

  def parse_item(self):
    """ Remove multiple spaces and new lines from text """
    value = self.raw_value or ""
    value = self.clean_whitespaces(value)
    if not value:
      value = self.row_converter.obj.title or \
          self.row_converter.attrs['title'].value
      self.add_warning(errors.WRONG_VALUE_DEFAULT,
                       column_name=self.display_name)
    return value

  @staticmethod
  def clean_whitespaces(value):
    """Change multiply whitespaces with single one in the value string."""
    return re.sub(r'\s+', " ", value)

  def set_obj_attr(self):
    if self.dry_run or not self.value:
      return
    self.row_converter.issue_tracker["title"] = self.value
