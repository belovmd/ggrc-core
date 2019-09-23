# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration exceptions definitions."""


class Error(Exception):
  """General integration error."""


class HttpError(Error):
  """Base HTTP error."""

  def __init__(self, data, status=500):
    """Instantiates error with give parameters.

    Args:
      data: A string or object describing an error.
      status: An integer representing HTTP status.
    """
    super(HttpError, self).__init__('HTTP Error %s' % status)
    self.data = data
    self.status = status

  def __str__(self):
    return '%s %s' % (self.status, self.data)

  def __repr__(self):
    """Return representation of an HttpError."""
    return '%s(status=%s, data=%s)' % (
        self.__class__.__name__, self.status, self.data)


class BadResponseError(Error):
  """Wrong formatted response error."""


class HotlistPermissionError(Error):
  """Not enough rights to the Hotlist"""
