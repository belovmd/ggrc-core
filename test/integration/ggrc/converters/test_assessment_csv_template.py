# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
# pylint: disable=invalid-name

"""Tests attributes order in csv file for assessments."""

from integration.ggrc import TestCase
from integration.ggrc.models import factories


class TestAssessmentCSVTemplate(TestCase):
  """Tests order of the attributes in assessment csv.

  Test suite for checking attributes order both in the
  the exported assessment csv (will be the same for
  assessment csv template).
  """

  def setUp(self):
    """Set up for test cases."""
    super(TestAssessmentCSVTemplate, self).setUp()
    self.client.get("/login")

  def test_exported_csv(self):
    """Tests attributes order in exported assessment csv."""
    factories.CustomAttributeDefinitionFactory(
        definition_type="assessment", title="GCA 1", )
    data = [{
        "object_name": "Assessment",
        "filters": {
            "expression": {},
        },
        "fields": "all",
    }]

    response = self.export_csv(data)
    self.assertEqual(response.status_code, 200)
    self.assertIn("Verifiers,Comments,Last Comment,GCA 1", response.data)

  def test_exclude_evidence_file(self):
    """Test exclude evidence file field from csv template"""
    objects = [{"object_name": "Assessment"}]
    response = self.export_csv_template(objects)
    self.assertNotIn("Evidence File", response.data)

  def test_generation_with_template_ids_given_0(self):
    """
      Test generation of csv file with filtered IDs
      ids of related assessment templates.

      0 - test that only assessment templates with given
      ids are used while gathering local custom attribute
      definitions
    """

    included_template_ids = []

    with factories.single_commit():
      included_template = factories.AssessmentTemplateFactory()
      excluded_template = factories.AssessmentTemplateFactory()

      assessment = factories.AssessmentFactory()
      assessment.audit = included_template.audit

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment_template",
          title="Included LCAD",
          definition_id=included_template.id,
      )

      included_template_ids.append(included_template.id)

      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 0",
      )

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment_template",
          title="Excluded LCAD",
          definition_id=excluded_template.id
      )

      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 1",
      )

    objects = [{
        "object_name": "Assessment",
        "template_ids": included_template_ids,
    }]

    response = self.export_csv_template(objects)

    self.assertIn('Included LCAD', response.data)
    self.assertNotIn("Excluded LCAD", response.data)

  def test_generation_with_template_ids_given_1(self):
    """
      Test that GCA are not filtered out by template_ids.

      1 - test that global custom attribute definitions
      are not filtered out by template_ids related filter.
    """

    included_template_ids = []

    with factories.single_commit():
      included_template = factories.AssessmentTemplateFactory()

      assessment = factories.AssessmentFactory()
      assessment.audit = included_template.audit

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment_template",
          title="Included LCAD",
          definition_id=included_template.id,
      )

      included_template_ids.append(included_template.id)

      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 0",
      )

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment",
          title="Included GCAD",
          definition_id=None
      )

      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 1",
      )

    objects = [{
        "object_name": "Assessment",
        "template_ids": included_template_ids,
    }]

    response = self.export_csv_template(objects)

    self.assertIn('Included LCAD', response.data)
    self.assertIn("Included GCAD", response.data)

  def test_generation_with_template_ids_given_2(self):
    """
      Test multiple assessment templates ids filter

      2 - test that multiple assessment templates ids are
      processed properly.
    """

    included_template_ids = []

    with factories.single_commit():
      included_template_0 = factories.AssessmentTemplateFactory()
      included_template_1 = factories.AssessmentTemplateFactory()

      excluded_template = factories.AssessmentTemplateFactory()

      assessment = factories.AssessmentFactory()
      assessment.audit = included_template_0.audit

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment_template",
          title="Included LCAD 0",
          definition_id=included_template_0.id,
      )
      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 0",
      )

      included_template_ids.append(included_template_0.id)

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment_template",
          title="Included LCAD 1",
          definition_id=included_template_1.id,
      )
      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 1",
      )

      included_template_ids.append(included_template_1.id)

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment_template",
          title="Excluded LCAD",
          definition_id=excluded_template.id
      )

      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 2",
      )

    objects = [{
        "object_name": "Assessment",
        "template_ids": included_template_ids,
    }]

    response = self.export_csv_template(objects)

    self.assertIn('Included LCAD 0', response.data)
    self.assertIn('Included LCAD 1', response.data)
    self.assertNotIn("Excluded LCAD", response.data)

  def test_generation_without_template_ids_given(self):
    """
      Test generation of csv file without filtering by ids
    """

    with factories.single_commit():
      included_template_0 = factories.AssessmentTemplateFactory()
      included_template_1 = factories.AssessmentTemplateFactory()

      assessment = factories.AssessmentFactory()
      assessment.audit = included_template_0.audit

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment_template",
          title="Excluded LCAD 0",
          definition_id=included_template_0.id,
      )

      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 0",
      )

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment_template",
          title="Excluded LCAD 1",
          definition_id=included_template_1.id
      )

      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 1",
      )

      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment",
          title="Included GCAD",
          definition_id=None
      )

      factories.CustomAttributeValueFactory(
          custom_attribute=cad,
          attributable=assessment,
          attribute_value="Test CAD 1",
      )

    objects = [{"object_name": "Assessment"}]

    response = self.export_csv_template(objects)

    self.assertIn("Included GCAD", response.data)
    self.assertNotIn("Excluded LCAD 0", response.data)
    self.assertNotIn("Excluded LCAD 1", response.data)
