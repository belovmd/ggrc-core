# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module provides basic class to wrap communication integration service."""
# pylint: disable=too-few-public-methods

import functools
import json
import logging
import urlparse

from google.appengine.api import urlfetch
from google.appengine.api import urlfetch_errors

from ggrc import settings
from ggrc.integrations import constants
from ggrc.integrations import integrations_errors


def value_for_http_error(func=None, predicates=None):
  """Decorator to return predefined value for given HTTP error codes.

  Example:
    @value_for_http_error({404: 'Default value'})
    def get(self):
      raise HttpError('Not Found', 404)

  the function above returns a string 'Default value' instead of
  raising HttpError.

  Default value might be a callable object which is used as value generator.

  Example:
    @value_for_http_error({404: list})
    def get(self):
      raise HttpError('Not Found', 404)

  the function above returns an empty list instead of raising HttpError.

  Args:
    func: A callable to decorate.
    predicates: A dict with HTTP return codes as keys and the values to return
        for these codes accordingly if there is an HttpError raised.

  Returns:
    Decorated callable.
  """
  if not func:
    return functools.partial(value_for_http_error, predicates=predicates)

  predicates = predicates or {}

  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    """Wrapper for external func."""
    try:
      return func(*args, **kwargs)
    except integrations_errors.HttpError as exc:
      if exc.status not in predicates:
        raise
      value = predicates[exc.status]
      if hasattr(value, '__call__'):
        return value()
      return value
  return wrapper


class BaseClient(object):
  """Base Client to communicate with integration service."""

  ENDPOINT = settings.INTEGRATION_SERVICE_URL
  DEFAULT_HEADERS = {
      'X-URLFetch-Service-Id': settings.URLFETCH_SERVICE_ID,
  }

  def _perform_request(self, url, method=urlfetch.GET, payload=None,
                       headers=None):
    """Performs request to given URL on integration service endpoint.

    Args:
      url: A string for request URL.
      method: A urlfetch method.
      payload: A string for request body. Ignored if method is not POST,
          PUT or PATCH.
      headers: An optional dict to use as HTTP headers.

    Returns:
      A string content from response.

    Raises:
      integrations_errors.HttpError: If not expected HTTP status occurs
          or fetch is not successful.
    """
    headers = headers or {}
    if self.DEFAULT_HEADERS:
      headers.update(self.DEFAULT_HEADERS)

    url = urlparse.urljoin(self.ENDPOINT, url)
    try:
      response = urlfetch.fetch(
          url,
          method=method,
          payload=payload,
          headers=headers,
          follow_redirects=False,
          deadline=constants.REQUEST_DEADLINE,
      )

      if response.status_code != 200:
        logging.error(
            'Unable to perform request to %s: %s %s',
            url, response.status_code, response.content)
        if (403 == response.status_code and
            "does not have permission to append to hotlist" in
                response.content):
          raise integrations_errors.HotlistPermissionError(
              response
          )
        raise integrations_errors.HttpError(
            response.content, status=response.status_code)

      return response.content
    except urlfetch_errors.Error as error:
      logging.exception('Unable to perform urlfetch request: %s', error)
      raise integrations_errors.HttpError('Unable to perform a request')

  def _get(self, url, headers=None):
    """Performs GET HTTP request to given URL."""
    return self._perform_request(url, method=urlfetch.GET, headers=headers)

  def _post(self, url, payload=None, headers=None):
    """Performs POST HTTP request to given URL with given data."""
    return self._perform_request(url, method=urlfetch.POST, payload=payload,
                                 headers=headers)

  def _put(self, url, payload=None, headers=None):
    """Performs PUT HTTP request to given URL with given data."""
    return self._perform_request(url, method=urlfetch.PUT, payload=payload,
                                 headers=headers)


class JsonClient(BaseClient):
  """JsonClient wraps base class to process data conversion to JSON and back"""

  def _perform_request(self, url, method=urlfetch.GET, payload=None,
                       headers=None):
    """Sends requests with respect to given parameters.

    Performs converting payload to JSON and parses JSON from response.

    Args:
      url: A string for request URL.
      method: A urlfetch method.
      payload: An object of parameters to be converted to JSON and sent
          as a payload.
      headers: An optional dict to use as HTTP headers.

    Returns:
      An object parsed from response.

    Raises:
      integrations_errors.BadResponseError: if response has wrong format and
          cannot be parsed.
    """
    headers = headers or {}
    headers['Content-Type'] = 'application/json'

    if payload is not None:
      payload = json.dumps(payload)

    data = super(JsonClient, self)._perform_request(
        url, method=method, payload=payload, headers=headers)

    try:
      return json.loads(data)
    except (TypeError, ValueError) as error:
      logging.error('Unable to parse JSON from response: %s', error)
      raise integrations_errors.BadResponseError(
          'Unable to parse JSON from response.')


class PersonClient(JsonClient):
  """Proxy Client class."""

  _BASE_PATH = '/api/persons'

  def search_persons(self, usernames):
    """Performs search persons request to integration server.

    Args:
      usernames: A list of strings with usernames.

    Returns:
      A list of dicts representing a person.
    """
    response = self._post(
        '%s:search' % self._BASE_PATH,
        payload={'usernames': usernames})
    return response['persons']

  def suggest_persons(self, tokens):
    """Performs suggest persons request to integration server.

    Args:
      tokens: prefixes to lookup for in 'email', 'first name' and 'last name'
      of person's info.

    Returns:
      A list of dicts representing a person.
    """
    response = self._post(
        '%s:suggest' % self._BASE_PATH,
        payload={'tokens': tokens})
    return response['persons']
