# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test to check assessment import with mapped regulation."""

from collections import OrderedDict
from mock import patch

from integration.ggrc import TestCase, read_imported_file
from integration.ggrc.api_helper import Api
from integration.ggrc.query_helper import WithQueryApi
from integration.ggrc.models import factories


class TestImportAssessmentWithMap(TestCase, WithQueryApi):
  """Test import with mapped regulation."""

  def setUp(self):
    """Setup for import with mapped regulation testcase."""

    super(TestImportAssessmentWithMap, self).setUp()

    self.client.get("/login")
    self.api = Api()

    with factories.single_commit():
      program = factories.ProgramFactory()
      self.program_id = program.id
      audit = factories.AuditFactory(program=program)
      factories.RelationshipFactory(
          source=audit,
          destination=program,
      )
      self.audit_id = audit.id
      assessment = factories.AssessmentFactory(audit=audit)
      self.assessment_id = assessment.id
      factories.RelationshipFactory(
          source=audit, destination=assessment
      )
      factories.IssueTrackerIssueFactory(
          component_id=12345,
          hotlist_id=12345,
          title="tickettitle",
          issue_type="PROCESS",
          issue_severity="S0",
          issue_priority="P0",
          issue_tracked_obj=assessment,
      )
      regulation = factories.RegulationFactory()
      self.regulation_id = regulation.id
      self.regulation_slug = regulation.slug
      snapshot = self._create_snapshots(audit, [regulation])[0]
      factories.RelationshipFactory(
          source=audit,
          destination=snapshot,
      )
      factories.RelationshipFactory(
          source=snapshot,
          destination=audit,
      )

    data = [{
        "object_name": "Assessment",
        "filters": {
            "expression": {},
        },
        "fields": "all",
    }]
    response = self.export_parsed_csv(data)
    self.asmt = response["Assessment"][0]
    self.asmt["map:regulation versions"] = self.regulation_slug

  @patch("ggrc.gdrive.file_actions.get_gdrive_file",
         new=read_imported_file)
  def test_import_assessment_with_map(self):
    """Import/Check Assessment with mapped Regulation."""

    imp_data = OrderedDict([{"object_type", "Assessment"}])
    imp_data.update(self.asmt)
    response = self.import_data(imp_data)
    self.assertEqual(
        response[0]["updated"],
        1,
        msg="1 assessment should be updated"
    )

    relevant = {
        "object_name": "Assessment",
        "op": {"name": "relevant"},
        "ids": [self.assessment_id]
    }
    child = self.make_filter_expression(
        expression=["child_type", "=", "Regulation"])
    filters = {
        "expression":
        self.make_filter_expression(expression=[child, "AND", relevant])}
    response = self._get_all_result_sets({
        "object_name": "Snapshot",
        "filters": filters,
        "limit": [0, 1]},
        "Snapshot"
    )

    self.assertEqual(
        response[0]["Snapshot"]["count"],
        1,
        msg="1 regulation should be relevant to our assessment")

    self.assertEqual(
        response[0]["Snapshot"]["values"][0]["revision"]["content"]["slug"],
        self.regulation_slug,
        msg="Regulation doesn't match with created")
