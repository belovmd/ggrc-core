# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Unit tests for client module."""
# pylint: disable=protected-access

import datetime
import unittest

import mock

from ggrc.models.hooks.issue_tracker import assessment_integration

from ggrc.integrations.synchronization_jobs import assessment_sync_job
from ggrc.integrations import integrations_errors, constants
from ggrc.integrations.synchronization_jobs import sync_utils


class BaseClientTest(unittest.TestCase):
  """Tests basic functions."""

  def test_collect_assessment_issues(self):
    """Tests collection issues associated with Assessments."""
    assessment1_mock = mock.MagicMock(id=1, status='In Review')
    issue1_mock = mock.MagicMock(
        issue_tracked_obj=assessment1_mock,
        component_id='1',
        issue_id='t1',
        issue_type='bug1',
        issue_priority='P1',
        issue_severity='S1',
        due_date=None,
        reporter='reporter@example.com',
        assignee='assignee@example.com'
    )
    issue2_mock = mock.MagicMock(
        issue_tracked_obj=None,
        component_id=None,
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
              'object': assessment1_mock,
              'state': {
                  'component_id': '1',
                  'status': 'In Review',
                  'type': 'bug1',
                  'priority': 'P1',
                  'severity': 'S1',
                  'due_date': None,
                  'reporter': 'reporter@example.com',
                  'assignee': 'assignee@example.com'
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
                        'component_id': None,
                        'hotlist_ids': None,
                        'verifier': 'verifier@example.com',
                        'assignee': 'assignee@example.com',
                        'reporter': 'reporter@example.com',
                        'custom_fields': [{
                            'name': 'Due Date',
                            'value': '2018-09-13',
                            'type': 'Date',
                            'display_string': 'Due Date',
                        }],
                        'ccs': []
                    },
                },
                {
                    'issueId': 't2',
                    'issueState': {
                        'status': 'FIXED',
                        'type': 'bug2',
                        'priority': 'P2',
                        'severity': 'S2',
                        'component_id': None,
                        'hotlist_ids': None,
                        'ccs': []
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
                  'component_id': None,
                  'hotlist_ids': None,
                  'verifier': 'verifier@example.com',
                  'assignee': 'assignee@example.com',
                  'reporter': 'reporter@example.com',
                  'custom_fields': [{
                      'name': 'Due Date',
                      'value': '2018-09-13',
                      'type': 'Date',
                      'display_string': 'Due Date',
                  }],
                  'ccs': []
              },
              't2': {
                  'status': 'FIXED',
                  'type': 'bug2',
                  'priority': 'P2',
                  'severity': 'S2',
                  'component_id': None,
                  'hotlist_ids': None,
                  'verifier': None,
                  'assignee': None,
                  'reporter': None,
                  'custom_fields': [],
                  'ccs': []
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
    self.assertIsNotNone(sync_utils.update_issue(cli_mock, 1, 'params'))
    cli_mock.update_issue.assert_called_once_with(1, 'params')

  def test_update_issue_with_retry(self):
    """Tests updating issue with retry."""
    cli_mock = mock.MagicMock()
    exception = integrations_errors.HttpError('Test', status=429)
    cli_mock.update_issue.side_effect = iter([
        exception,
        exception,
        None,
    ])
    with mock.patch.object(sync_utils.time, 'sleep') as sleep_mock:
      sync_utils.update_issue(cli_mock, 5, 'params')
      self.assertEqual(cli_mock.update_issue.call_args_list, [
          mock.call(5, 'params'),
          mock.call(5, 'params'),
          mock.call(5, 'params'),
      ])
      self.assertEqual(sleep_mock.call_args_list, [
          mock.call(5),
          mock.call(5),
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

  @mock.patch.object(
      assessment_integration.AssessmentTrackerHandler,
      "_get_reporter_on_sync",
      lambda obj, audit_id, reporter_db: "reporter@example.com"
  )
  @mock.patch.object(
      assessment_integration.AssessmentTrackerHandler,
      "_get_assignee_on_sync",
      lambda obj, assessment_id, assignee_db: "assignee@example.com"
  )
  @mock.patch.object(
      assessment_integration.AssessmentTrackerHandler,
      "_get_ccs",
      lambda obj, reporter, assignee, assessment: []
  )
  @mock.patch.object(
      assessment_integration.AssessmentTrackerHandler,
      '_is_tracker_enabled',
      lambda obj, audit: True
  )
  def test_sync_issue_statuses(self):  # pylint: disable=invalid-name
    """Tests issue synchronization flow."""
    assessment_in_review = mock.MagicMock(
        id=1,
        status='In Review',
        start_date=datetime.datetime.utcnow()
    )
    assessment_not_started = mock.MagicMock(
        id=2,
        status='Not Started',
        start_date=datetime.datetime.utcnow()
    )
    assessment_issues = {
        '1': {
            'object_id': 1,
            'object': assessment_in_review,
            'state': {
                'component_id': '1111',
                'status': 'In Review',
                'type': 'BUG1',
                'priority': 'P1',
                'severity': 'S1',
                'due_date': None,
                'reporter': 'reporter@example.com',
                'assignee': 'assignee@example.com'
            },
        },
        '2': {
            'object_id': 2,
            'object': assessment_not_started,
            'state': {
                'component_id': '1111',
                'status': 'Not Started',
                'type': 'BUG2',
                'priority': 'P2',
                'severity': 'S2',
                'due_date': None,
                'reporter': 'reporter@example.com',
                'assignee': 'assignee@example.com'
            },
        },
    }
    batches = [
        {
            1: {
                'component_id': '1111',
                'status': 'FIXED',
                'type': 'BUG1',
                'priority': 'P1',
                'severity': 'S1',
                'custom_fields': [],
                'reporter': 'reporter@example.com',
                'assignee': 'assignee@example.com',
                'ccs': []
            },
        },
        {
            2: {
                'component_id': '1111',
                'status': 'FIXED',
                'type': 'BUG2',
                'priority': 'P2',
                'severity': 'S2',
                'custom_fields': [],
                'reporter': 'reporter@example.com',
                'assignee': 'assignee@example.com',
                'ccs': []
            },
            3: {
                'component_id': '1111',
                'status': 'FIXED',
                'type': 'BUG2',
                'priority': 'P2',
                'severity': 'S2',
                'custom_fields': [],
                'reporter': 'reporter@example.com',
                'assignee': 'assignee@example.com',
                'ccs': []
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
        sync_utils.update_issue.assert_called_with(cli_mock, '2', {
            'status': 'ASSIGNED',
            'type': 'BUG2',
            'priority': 'P2',
            'severity': 'S2',
            'ccs': [],
            'component_id': 1111,
            'reporter': 'reporter@example.com',
            'assignee': 'assignee@example.com',
            'verifier': 'assignee@example.com'
        })

  def test_due_date_equals(self):
    """Due date current and issue tracker equals."""
    custom_fields_payload = [
        {
            "name": constants.CustomFields.DUE_DATE,
            "value": "2018-10-10",
            "type": "DATE",
            "display_string": constants.CustomFields.DUE_DATE
        }
    ]
    custom_fields_issuetracker = [
        {
            constants.CustomFields.DUE_DATE: "2018-10-10"
        },
        {
            "field1": "value1"
        },
        {
            "field2": "value2"
        }
    ]
    due_dates_equals, remove_custom_fields = \
        assessment_sync_job._compare_custom_fields(
            custom_fields_payload,
            custom_fields_issuetracker
        )
    self.assertTrue(due_dates_equals)
    self.assertFalse(remove_custom_fields)

  def test_due_date_not_equals(self):
    """Due date current and issue tracker not equals."""
    custom_fields_payload = [
        {
            "name": constants.CustomFields.DUE_DATE,
            "value": "2018-10-10",
            "type": "DATE",
            "display_string": constants.CustomFields.DUE_DATE
        }
    ]
    custom_fields_issuetracker = [
        {
            constants.CustomFields.DUE_DATE: "2018-11-10"
        },
        {
            "field1": "value1"
        },
        {
            "field2": "value2"
        }
    ]
    due_dates_equals, remove_custom_fields = \
        assessment_sync_job._compare_custom_fields(
            custom_fields_payload,
            custom_fields_issuetracker
        )
    self.assertFalse(due_dates_equals)
    self.assertFalse(remove_custom_fields)

  def test_due_date_is_empty(self):
    """Due date is empty for issue tracker."""
    custom_fields_payload = [
        {
            "name": constants.CustomFields.DUE_DATE,
            "value": "2018-10-10",
            "type": "DATE",
            "display_string": constants.CustomFields.DUE_DATE
        }
    ]
    custom_fields_issuetracker = [
        {
            "field1": "value1"
        },
        {
            "field2": "value2"
        }
    ]
    due_dates_equals, remove_custom_fields = \
        assessment_sync_job._compare_custom_fields(
            custom_fields_payload,
            custom_fields_issuetracker
        )
    self.assertTrue(due_dates_equals)
    self.assertTrue(remove_custom_fields)

  def test_custom_fields_is_empty(self):
    """Custom fields for issue tracker is empty."""
    custom_fields_payload = [
        {
            "name": constants.CustomFields.DUE_DATE,
            "value": "2018-10-10",
            "type": "DATE",
            "display_string": constants.CustomFields.DUE_DATE
        }
    ]
    custom_fields_issuetracker = []
    due_dates_equals, remove_custom_fields = \
        assessment_sync_job._compare_custom_fields(
            custom_fields_payload,
            custom_fields_issuetracker
        )
    self.assertTrue(due_dates_equals)
    self.assertTrue(remove_custom_fields)

  def test_group_ccs(self):
    """Group ccs from system and issutracker."""
    ccs_payload = [
        "test1@test.com",
        "test2@test.com",
        "test3@test.com"
    ]
    ccs_issuetracker = [
        "test1@test.com",
        "test2@test.com",
        "test3@test.com",
        "test4@test.com"
    ]
    ccs_grouped = \
        assessment_sync_job._group_ccs_with_issuetracker(
            ccs_payload,
            ccs_issuetracker
        )
    expected_result = [
        "test1@test.com",
        "test2@test.com",
        "test3@test.com",
        "test4@test.com"
    ]
    self.assertListEqual(ccs_grouped, expected_result)

  def test_group_ccs_wh_system(self):
    """Group ccs w/h ccs from system."""
    ccs_payload = []
    ccs_issuetracker = [
        "test1@test.com",
        "test2@test.com",
        "test3@test.com",
        "test4@test.com"
    ]
    ccs_grouped = \
        assessment_sync_job._group_ccs_with_issuetracker(
            ccs_payload,
            ccs_issuetracker
        )
    self.assertListEqual(ccs_issuetracker, ccs_grouped)

  def test_group_ccs_wh_issuetracker(self):
    """Group ccs w/h ccs from issuetracker."""
    ccs_payload = [
        "test1@test.com",
        "test2@test.com",
        "test3@test.com"
    ]
    ccs_issuetracker = []
    ccs_grouped = \
        assessment_sync_job._group_ccs_with_issuetracker(
            ccs_payload,
            ccs_issuetracker
        )
    self.assertListEqual(ccs_payload, ccs_grouped)
