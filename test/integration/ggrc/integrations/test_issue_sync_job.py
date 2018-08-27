# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration test for Issu object sync cron job."""

# pylint: disable=protected-access
# pylint: disable=invalid-name


import ddt
import mock
import flask

from ggrc.models import all_models
from ggrc.integrations.synchronization_jobs import issue_sync_job
from ggrc.integrations.synchronization_jobs import sync_utils
from integration import ggrc
from integration.ggrc.models import factories


@ddt.ddt
class TestIssueIntegration(ggrc.TestCase):
  """Test crom job for sync Issue object attributes."""

  def setUp(self):
    super(TestIssueIntegration, self).setUp()
    self.verifier = factories.PersonFactory(name="a")
    self.assignee = factories.PersonFactory(name="b")
    self.admin_role = all_models.AccessControlRole.query.filter_by(
        object_type=all_models.Issue.__name__, name="Admin"
    ).first()
    self.primary_contact_role = all_models.AccessControlRole.query.filter_by(
        object_type=all_models.Issue.__name__, name="Primary Contacts"
    ).first()

  @ddt.data(
      ("new", "Draft"),
      ("assigned", "Draft"),
      ("accepted", "Active"),
      ("fixed", "Fixed"),
      ("verified", "Fixed and Verified"),
      ("not_reproducible", "Deprecated"),
      ("intended_behavior", "Deprecated"),
      ("obsolete", "Deprecated"),
      ("infeasible", "Deprecated"),
      ("duplicate", "Deprecated",)
  )
  @ddt.unpack
  def test_sync_issue_statuses(self, issuetracker_status, issue_status):
    """Test updating issue statuses in GGRC."""
    # Arrange test data.
    issue_tracker_issue_id = "1"
    iti = factories.IssueTrackerIssueFactory(
        enabled=True,
        issue_id=issue_tracker_issue_id,
        issue_tracked_obj=factories.IssueFactory(status="Draft")
    )

    batches = [
        {
            issue_tracker_issue_id: {
                "status": issuetracker_status,
                "type": "BUG",
                "priority": "P2",
                "severity": "S2",
            }
        }
    ]

    # Perform action.
    with mock.patch.object(sync_utils, "iter_issue_batches",
                           return_value=batches):
      issue_sync_job.sync_issue_attributes()

    # Assert results.
    issue = all_models.Issue.query.get(iti.issue_tracked_obj.id)
    self.assertEquals(issue.status, issue_status)

  def initialize_test_issuetracker_info(self):
    """Create Issue with admin and primary contact"""
    iti = factories.IssueTrackerIssueFactory(
        enabled=True,
        issue_id="1",
        issue_tracked_obj=factories.IssueFactory(status="Draft")
    )

    # Add Admin into issue.
    factories.AccessControlListFactory(
        ac_role=self.admin_role,
        object=iti.issue_tracked_obj,
        person=self.verifier
    )

    # Add primary contact into issue.
    factories.AccessControlListFactory(
        ac_role=self.primary_contact_role,
        object=iti.issue_tracked_obj,
        person=self.assignee,
    )

    return iti

  def test_sync_verifier_email(self):
    """Test adding new verifier email into Issue ACL."""
    # Arrange test data.
    new_verifier = factories.PersonFactory(name="c")
    iti = self.initialize_test_issuetracker_info()

    batches = [
        {
            "1": {
                "status": "NEW",
                "type": "BUG",
                "priority": "P2",
                "severity": "S2",
                "verifier": new_verifier.email,
                "assignee": self.assignee.email,
            }
        }
    ]

    # Perform action.
    with mock.patch.object(flask.g, "global_role_names", None):
      with mock.patch.object(sync_utils, "iter_issue_batches",
                             return_value=batches):
        issue_sync_job.sync_issue_attributes()

      # Assert results.
      issue = all_models.Issue.query.get(iti.issue_tracked_obj.id)
      admin_emails = [
          person.email for person in issue.get_persons_for_rolename("Admin")
      ]
      self.assertListEqual(
          admin_emails,
          [new_verifier.email, ]
      )

      primary_contacts_emails = [
          person.email
          for person in issue.get_persons_for_rolename("Primary Contacts")
      ]
      self.assertListEqual(primary_contacts_emails, [self.assignee.email])

  def test_sync_assignee_email(self):
    """Test adding new assignee email into Issue ACL."""
    # Arrange test data.
    new_assignee = factories.PersonFactory(name="d")
    iti = self.initialize_test_issuetracker_info()

    batches = [
        {
            "1": {
                "status": "NEW",
                "type": "BUG",
                "priority": "P2",
                "severity": "S2",
                "verifier": self.verifier.email,
                "assignee": new_assignee.email,
            }
        }
    ]

    # Perform action.
    with mock.patch.object(flask.g, "global_role_names", None):
      with mock.patch.object(sync_utils, "iter_issue_batches",
                             return_value=batches):
        issue_sync_job.sync_issue_attributes()

      issue = all_models.Issue.query.get(iti.issue_tracked_obj.id)

      # Check unchanged admins
      admin_emails = [
          person.email for person in issue.get_persons_for_rolename("Admin")
      ]
      self.assertListEqual(admin_emails, [self.verifier.email, ])

      # Check changed primary contacts
      primary_contacts_emails = [
          person.email
          for person in issue.get_persons_for_rolename("Primary Contacts")
      ]
      self.assertListEqual(
          primary_contacts_emails,
          [new_assignee.email, ]
      )

  def test_sync_due_date(self):
    """Test adding due_date in Issue"""

    due_date = "2018-09-13"
    date_format = "%Y-%m-%d"
    iti1 = factories.IssueTrackerIssueFactory(
        enabled=True,
        issue_id="1",
        issue_tracked_obj=factories.IssueFactory(status="Draft")
    )
    iti2 = factories.IssueTrackerIssueFactory(
        enabled=True,
        issue_id="2",
        issue_tracked_obj=factories.IssueFactory(status="Draft")
    )

    batches = [
        {
            "1": {
                "status": "new",
                "type": "BUG",
                "priority": "P2",
                "severity": "S2",
                "custom_fields": [{
                    "name": "Due Date",
                    "value": due_date,
                    "type": "Date",
                    "display_string": "Due Date",
                }],
            },
            "2": {
                "status": "new",
                "type": "BUG",
                "priority": "P2",
                "severity": "S2",
                "custom_fields": [],
            }
        }
    ]

    # Perform action.
    with mock.patch.object(sync_utils, "iter_issue_batches",
                           return_value=batches):
      issue_sync_job.sync_issue_attributes()

    # Assert results.
    issue1 = all_models.Issue.query.get(iti1.issue_tracked_obj.id)
    self.assertEquals(issue1.due_date.strftime(date_format), due_date)

    issue2 = all_models.Issue.query.get(iti2.issue_tracked_obj.id)
    self.assertIsNone(issue2.due_date)

  def test_sync_issue_tracker_emails(self):
    """Test sync issue tracker emails.

    Current verifier should be replaced by new verifier from Issue Tracker.
    Current assignee should be replaced by new assignee from Issue Tracker.
    CCs list shouldn't be changed.

    Other Admins and Primary Contacts shouldn't be removed.
    """
    # Arrange test data.
    new_assignee = factories.PersonFactory(name="e")
    new_verifier = factories.PersonFactory(name="f")
    iti = self.initialize_test_issuetracker_info()

    # Add more admins into issue.
    second_verifier = factories.PersonFactory(name="g")
    # Change names to be sure that names in alphabetical order.
    self.verifier.name = "A" + self.verifier.name
    second_verifier.name = "B" + second_verifier.name

    factories.AccessControlListFactory(
        ac_role=self.admin_role,
        object=iti.issue_tracked_obj,
        person=second_verifier
    )

    # Add more primary contacts into issue.
    second_assignee = factories.PersonFactory(name="h")
    # Change names to be sure that names in alphabetical order.
    self.assignee.name = "A" + self.assignee.name
    second_assignee.name = "B" + second_assignee.name

    factories.AccessControlListFactory(
        ac_role=self.primary_contact_role,
        object=iti.issue_tracked_obj,
        person=second_assignee
    )

    batches = [
        {
            "1": {
                "status": "NEW",
                "type": "BUG",
                "priority": "P2",
                "severity": "S2",
                "verifier": new_verifier.email,
                "assignee": new_assignee.email,
            }
        }
    ]

    # Perform action.
    with mock.patch.object(flask.g, "global_role_names", None):
      with mock.patch.object(sync_utils, "iter_issue_batches",
                             return_value=batches):
        issue_sync_job.sync_issue_attributes()

      issue = all_models.Issue.query.get(iti.issue_tracked_obj.id)

      # Check changed admins.
      admin_emails = [
          person.email for person in issue.get_persons_for_rolename("Admin")
      ]
      self.assertListEqual(
          admin_emails,
          [second_verifier.email, new_verifier.email, ]
      )

      # Check changed primary contacts.
      primary_contacts_emails = [
          person.email
          for person in issue.get_persons_for_rolename("Primary Contacts")
      ]
      self.assertListEqual(
          primary_contacts_emails,
          [second_assignee.email, new_assignee.email, ]
      )
