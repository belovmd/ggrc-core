# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module for tests for back_sync job"""

import mock

from ggrc import db
from ggrc.models import all_models
from integration.ggrc import TestCase
from integration.ggrc.models import factories


class TestOnetimeBackSync(TestCase):
  """Class for tests back_sync job"""
  def setUp(self):
    super(TestOnetimeBackSync, self).setUp()
    self.client.get('/login')

  @mock.patch('ggrc.integrations.synchronization_jobs.sync_utils.'
              'iter_issue_batches')
  def test_update_issuetrackerissues(self, sync_result_mock):
    """Test onetime_back_sync_job"""
    correct_hotlist_id = 999
    correct_component_id = 888

    with factories.single_commit():
      # Invalid hotlist_id
      issue_1 = factories.IssueTrackerIssueFactory(
          hotlist_id='123',
          component_id=456,
          issue_id=111
      )
      # Invalid component_id
      issue_2 = factories.IssueTrackerIssueFactory(
          hotlist_id='123',
          component_id=456,
          issue_id=222
      )
      # Valid issue
      issue_3 = factories.IssueTrackerIssueFactory(
          hotlist_id=correct_hotlist_id,
          component_id=correct_component_id,
          issue_id=333
      )

    sync_result_mock.return_value = [{
        int(issue_1.issue_id): {
            "status": "NEW",
            "type": "PROCESS",
            "priority": "P2",
            "severity": "S2",
            "component_id": int(issue_1.component_id),
            "hotlist_ids": [correct_hotlist_id]

        },
        int(issue_2.issue_id): {
            "status": "NEW",
            "type": "PROCESS",
            "priority": "P2",
            "severity": "S2",
            "component_id": correct_component_id,
            "hotlist_ids": [int(issue_2.hotlist_id)]

        },
        int(issue_3.issue_id): {
            "status": "NEW",
            "type": "PROCESS",
            "priority": "P2",
            "severity": "S2",
            "component_id": correct_component_id,
            "hotlist_ids": [correct_hotlist_id]

        }

    }]

    response = self.client.post('/admin/onetime_back_sync')
    bg_task = all_models.BackgroundTask.query.first()

    self.assert200(response)
    self.assertIn('onetime_back_sync', bg_task.name)
    self.assertEqual(bg_task.status, 'Success')

    query = (
        """
            SELECT * FROM objects_without_revisions
            WHERE obj_type = 'IssuetrackerIssue' AND obj_id in (%s, %s)
        """ % (issue_1.id, issue_2.id)
    )
    objects_without_revisions = db.session.execute(query)
    self.assertEqual(objects_without_revisions.rowcount, 2)
    for item in objects_without_revisions:
      self.assertEqual(item.action, 'updated')

    issue_1 = all_models.IssuetrackerIssue.query.get(issue_1.id)
    issue_2 = all_models.IssuetrackerIssue.query.get(issue_2.id)
    issue_3 = all_models.IssuetrackerIssue.query.get(issue_3.id)

    self.assertEqual(int(issue_1.hotlist_id), correct_hotlist_id)
    self.assertEqual(int(issue_2.component_id), correct_component_id)
    self.assertEqual(int(issue_3.component_id), correct_component_id)
    self.assertEqual(int(issue_3.hotlist_id), correct_hotlist_id)
