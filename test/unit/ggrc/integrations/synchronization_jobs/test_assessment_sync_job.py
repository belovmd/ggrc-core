# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Unit tests for client module."""
# pylint: disable=protected-access

import unittest

import mock

from ggrc.integrations.synchronization_jobs import assessment_sync_job
from ggrc.integrations import integrations_errors
from ggrc.integrations.synchronization_jobs import sync_utils


class BaseClientTest(unittest.TestCase):
  """Tests basic functions."""

  def test_collect_assessment_issues(self):
    """Tests collection issues associated with Assessments."""
    assessment1_mock = mock.MagicMock(id=1, status='In Review')
    issue1_mock = mock.MagicMock(
        issue_tracked_obj=assessment1_mock,
        issue_id='t1',
        issue_type='bug1',
        issue_priority='P1',
        issue_severity='S1',
        due_date=None
    )
    issue2_mock = mock.MagicMock(
        issue_tracked_obj=None,
        issue_id='t2',
        issue_type='bug2',
        issue_priority='P3',
        issue_severity='S3',
        due_date=None
    )
    filter_mock = mock.MagicMock()
    filter_mock.return_value.order_by.return_value.all.return_value = [
        issue1_mock,
        issue2_mock,
    ]
    with mock.patch.multiple(
        sync_utils.models.IssuetrackerIssue,
        query=mock.MagicMock(filter=filter_mock)
    ):
      actual = sync_utils.collect_issue_tracker_info("Assessment")
      self.assertEquals(actual, {
          't1': {
              'object_id': 1,
              'state': {
                  'status': 'In Review',
                  'type': 'bug1',
                  'priority': 'P1',
                  'severity': 'S1',
                  'due_date': None,
              },
          }
      })

  def test_iter_issue_batches(self):
    """Tests fetching issues from Issue Tracer in batches."""
    cli_mock = mock.MagicMock()
    cli_mock.search.side_effect = iter([
        {
            'issues': [
                {
                    'issueId': 't1',
                    'issueState': {
                        'status': 'FIXED',
                        'type': 'bug1',
                        'priority': 'P1',
                        'severity': 'S1',
                        'custom_fields': [{
                            'name': 'Due Date',
                            'value': '2018-09-13',
                            'type': 'Date',
                            'display_string': 'Due Date',
                        }],
                    },
                },
                {
                    'issueId': 't2',
                    'issueState': {
                        'status': 'FIXED',
                        'type': 'bug2',
                        'priority': 'P2',
                        'severity': 'S2',
                    },
                },
            ],
        },
    ])
    with mock.patch.object(sync_utils.issues, 'Client', return_value=cli_mock):
      actual = list(sync_utils.iter_issue_batches([1, 2, 3]))
      self.assertEquals(actual, [
          {
              't1': {
                  'status': 'FIXED',
                  'type': 'bug1',
                  'priority': 'P1',
                  'severity': 'S1',
                  'custom_fields': [{
                      'name': 'Due Date',
                      'value': '2018-09-13',
                      'type': 'Date',
                      'display_string': 'Due Date',
                  }],
              },
              't2': {
                  'status': 'FIXED',
                  'type': 'bug2',
                  'priority': 'P2',
                  'severity': 'S2',
                  'custom_fields': [],
              },
          },
      ])
      self.assertEqual(cli_mock.search.call_args_list, [
          mock.call({
              'issue_ids': [1, 2, 3],
              'page_size': 100,
          }),
      ])

  def test_iter_issue_batches_error(self):
    """Tests handling error fetching issues from Issue Tracer in batches."""
    cli_mock = mock.MagicMock()
    cli_mock.search.side_effect = integrations_errors.HttpError('Test')
    with mock.patch.object(sync_utils.issues, 'Client', return_value=cli_mock):
      actual = list(sync_utils.iter_issue_batches([1, 2, 3]))
      self.assertEqual(actual, [])

  def test_update_issue(self):
    """Tests updating issue."""
    cli_mock = mock.MagicMock()
    self.assertIsNone(sync_utils.update_issue(cli_mock, 1, 'params'))
    cli_mock.update_issue.assert_called_once_with(1, 'params')

  def test_update_issue_with_retry(self):
    """Tests updating issue with retry."""
    cli_mock = mock.MagicMock()
    exception = integrations_errors.HttpError('Test', status=429)
    cli_mock.update_issue.side_effect = iter([
        exception,
        exception,
        exception,
        exception,
        None,
    ])
    with mock.patch.object(sync_utils.time, 'sleep') as sleep_mock:
      sync_utils.update_issue(cli_mock, 1, 'params')
      self.assertEqual(cli_mock.update_issue.call_args_list, [
          mock.call(1, 'params'),
          mock.call(1, 'params'),
          mock.call(1, 'params'),
          mock.call(1, 'params'),
          mock.call(1, 'params'),
      ])
      self.assertEqual(sleep_mock.call_args_list, [
          mock.call(1),
          mock.call(1),
          mock.call(1),
          mock.call(1),
      ])

  def test_update_issue_with_raise(self):
    """Tests updating issue with raising an exception."""
    cli_mock = mock.MagicMock()
    exception = integrations_errors.HttpError('Test', status=429)
    cli_mock.update_issue.side_effect = iter([
        exception,
        exception,
        exception,
        exception,
        exception,
    ])
    with mock.patch.object(sync_utils.time, 'sleep') as sleep_mock:
      with self.assertRaises(integrations_errors.HttpError) as exc_mock:
        sync_utils.update_issue(cli_mock, 1, 'params')
        self.assertEqual(exc_mock.exception.status, 429)
        self.assertEqual(cli_mock.update_issue.call_args_list, [
            mock.call(1, 'params'),
            mock.call(1, 'params'),
            mock.call(1, 'params'),
            mock.call(1, 'params'),
            mock.call(1, 'params'),
        ])
        self.assertEqual(sleep_mock.call_args_list, [
            mock.call(1),
            mock.call(1),
            mock.call(1),
            mock.call(1),
        ])

  def test_sync_issue_tracker_statuses(self):  # pylint: disable=invalid-name
    """Tests issue synchronization flow."""
    assessment_issues = {
        '1': {
            'object_id': 1,
            'state': {
                'status': 'In Review',
                'type': 'BUG1',
                'priority': 'P1',
                'severity': 'S1',
                'due_date': None,
            },
        },
        '2': {
            'object_id': 2,
            'state': {
                'status': 'Not Started',
                'type': 'BUG2',
                'priority': 'P2',
                'severity': 'S2',
                'due_date': None,
            },
        },
    }
    batches = [
        {
            1: {
                'status': 'FIXED',
                'type': 'BUG1',
                'priority': 'P1',
                'severity': 'S1',
                'custom_fields': [],
            },
        },
        {
            2: {
                'status': 'FIXED',
                'type': 'BUG2',
                'priority': 'P2',
                'severity': 'S2',
                'custom_fields': [],
            },
            3: {
                'status': 'FIXED',
                'type': 'BUG2',
                'priority': 'P2',
                'severity': 'S2',
                'custom_fields': [],
            },
        },
    ]

    cli_mock = mock.MagicMock()
    cli_patch = mock.patch.object(
        sync_utils.issues, 'Client', return_value=cli_mock)

    with cli_patch, mock.patch.multiple(
        sync_utils,
        iter_issue_batches=mock.MagicMock(
            return_value=iter(batches)),
        update_issue=mock.DEFAULT
    ):
      with mock.patch.object(sync_utils,
                             "collect_issue_tracker_info",
                             return_value=assessment_issues):
        assessment_sync_job.sync_assessment_attributes()
        iter_calls = sync_utils.iter_issue_batches.call_args_list
        self.assertEqual(len(iter_calls), 1)
        self.assertItemsEqual(iter_calls[0][0][0], ['1', '2'])
        sync_utils.update_issue.assert_called_once_with(cli_mock, '2', {
            'status': 'ASSIGNED',
            'type': 'BUG2',
            'priority': 'P2',
            'severity': 'S2',
        })
