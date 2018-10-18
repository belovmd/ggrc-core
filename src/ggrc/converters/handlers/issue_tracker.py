# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Handlers for Issue Tracker fields"""

from ggrc.converters.handlers import handlers


class IssueTrackerColumnHandler(handlers.ColumnHandler):
  """Column handler used for Issue Tracker related fields.

  This class provides method for Issue Tracker fields export.
  """
  def get_value(self):
    return self.row_converter.issue_tracker.get(self.key, "")
