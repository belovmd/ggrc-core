# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration tests for IssueTracker updates via import cases."""


import mock

from ggrc import settings
from ggrc.models import all_models
from ggrc.models.hooks.issue_tracker import assessment_integration
from ggrc.converters import errors
from ggrc.integrations.constants import DEFAULT_ISSUETRACKER_VALUES as \
    default_values

from integration import ggrc
from integration.ggrc.api_helper import Api


class TestIssueTrackedImport(ggrc.TestCase):
  """Test cases for IssueTracker integration via import."""

  def setUp(self):
    # pylint: disable=super-on-old-class
    super(TestIssueTrackedImport, self).setUp()
    self.api = Api()
    self.client.get("/login")

  @mock.patch('ggrc.integrations.issues.Client.create_issue')
  def test_asmt_creation_detached(self, mock_create_issue):
    """Test assessment creation via import detached from IssueTracker hooks."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      self.import_file("assessment_full_no_warnings.csv")
    mock_create_issue.assert_not_called()

  @mock.patch('ggrc.integrations.issues.Client.create_issue')
  @mock.patch.object(settings, "ISSUE_TRACKER_ENABLED", True)
  def test_issue_creation_detached(self, mock_create_issue):
    """Test issue creation via import detached from IssueTracker hooks."""
    self.import_file("issue_for_import.csv")
    mock_create_issue.assert_not_called()

  def test_attr_import_succeed(self):
    """Test import success for all issuetracked models."""
    response = self.import_file("issuetracker_no_warnings.csv")
    expected_messages = {
        "Audit": {
            "rows": 1,
            "updated": 0,
            "created": 1,
        },
        "Assessment Template": {
            "rows": 1,
            "updated": 0,
            "created": 1,
        },
        "Assessment": {
            "rows": 1,
            "updated": 0,
            "created": 1,
        },
        "Issue": {
            "rows": 1,
            "updated": 0,
            "created": 1,
        },
    }
    self._check_csv_response(response, expected_messages)

    audit = all_models.Audit.query.first()
    self.assertEqual(int(audit.issue_tracker["component_id"]), 1)
    self.assertEqual(int(audit.issue_tracker["hotlist_id"]), 2)
    self.assertEqual(audit.issue_tracker["issue_priority"], "P0")
    self.assertEqual(audit.issue_tracker["issue_severity"], "S0")
    self.assertEqual(audit.issue_tracker["issue_type"], "PROCESS")

    asmt_tmpl = all_models.AssessmentTemplate.query.first()
    self.assertEqual(int(asmt_tmpl.issue_tracker["component_id"]), 3)
    self.assertEqual(int(asmt_tmpl.issue_tracker["hotlist_id"]), 4)
    self.assertEqual(asmt_tmpl.issue_tracker["issue_priority"], "P1")
    self.assertEqual(asmt_tmpl.issue_tracker["issue_severity"], "S1")
    self.assertEqual(asmt_tmpl.issue_tracker["issue_type"], "PROCESS")

    asmt = all_models.Assessment.query.first()
    self.assertEqual(int(asmt.issue_tracker["component_id"]), 5)
    self.assertEqual(int(asmt.issue_tracker["hotlist_id"]), 6)
    self.assertEqual(asmt.issue_tracker["issue_priority"], "P2")
    self.assertEqual(asmt.issue_tracker["issue_severity"], "S2")
    self.assertEqual(asmt.issue_tracker["issue_type"], "PROCESS")
    self.assertEqual(asmt.issue_tracker["title"], "assessment ticket title")

    issue = all_models.Issue.query.first()
    self.assertEqual(int(issue.issue_tracker["component_id"]), 7)
    self.assertEqual(int(issue.issue_tracker["hotlist_id"]), 8)
    self.assertEqual(issue.issue_tracker["issue_priority"], "P3")
    self.assertEqual(issue.issue_tracker["issue_severity"], "S3")
    self.assertEqual(issue.issue_tracker["issue_type"], "PROCESS")
    self.assertEqual(issue.issue_tracker["title"], "issue ticket title")

  def test_attr_import_warnings(self):
    """Test import with warnings and default values."""
    response = self.import_file("issuetracker_warnings.csv", safe=False)
    expected_warnings = {
        errors.WRONG_VALUE_DEFAULT.format(line=3, column_name="Component ID"),
        errors.WRONG_VALUE_DEFAULT.format(line=3, column_name="Hotlist ID"),
        errors.WRONG_VALUE_DEFAULT.format(line=3, column_name="Priority"),
        errors.WRONG_VALUE_DEFAULT.format(line=3, column_name="Severity"),
        errors.WRONG_VALUE_DEFAULT.format(line=3, column_name="Issue Type"),
        errors.WRONG_VALUE_DEFAULT.format(line=3, column_name="Issue Title"),
    }
    expected_messages = {
        "Issue": {
            "row_warnings": expected_warnings,
        }
    }
    self._check_csv_response(response, expected_messages)

    issue = all_models.Issue.query.first()
    self.assertEqual(int(issue.issue_tracker["component_id"]),
                     default_values["component_id"])
    self.assertEqual(int(issue.issue_tracker["hotlist_id"]),
                     default_values["hotlist_id"])
    self.assertEqual(issue.issue_tracker["issue_priority"],
                     default_values["issue_priority"])
    self.assertEqual(issue.issue_tracker["issue_severity"],
                     default_values["issue_severity"])
    self.assertEqual(issue.issue_tracker["issue_type"],
                     default_values["issue_type"])
    self.assertEqual(issue.issue_tracker["title"], "testissue")
