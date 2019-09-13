# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

# pylint: disable=maybe-no-member

"""Test Assessment Template import."""

import collections

from ggrc import models
from ggrc.converters import errors
from ggrc.utils import errors as common_errors
from integration.ggrc import TestCase
from integration.ggrc.models import factories


class TestAssessmentTemplatesImport(TestCase):
  """Assessment Template import tests."""

  def setUp(self):
    """Set up for Assessment Template test cases."""
    super(TestAssessmentTemplatesImport, self).setUp()
    self.client.get("/login")

  def test_valid_import(self):
    """Test valid import."""
    with factories.single_commit():
      audit_slug = factories.AuditFactory().slug
    asmt_tmpl_data = [
        collections.OrderedDict([
            ("object_type", "Assessment Template"),
            ("Code*", ""),
            ("Audit*", audit_slug),
            ("Default Assignees*", "Auditors"),
            ("Default Assessment Type", "Control"),
            ("Title", "Template 1-Created"),
        ])
    ]

    expected_messages = {
        "Assessment Template": {
            "rows": 1,
            "created": 1,
            "updated": 0,
        },
    }

    response = self.import_data(*asmt_tmpl_data)
    self._check_csv_response(response, expected_messages)

    tmpl = models.AssessmentTemplate.query.first()
    self.assertEqual(tmpl.default_people["assignees"], "Auditors")
    self.assertEqual(tmpl.template_object_type, "Control")
    self.assertEqual(tmpl.title, "Template 1-Created")

  def test_modify_over_import(self):
    """Test import modifies Assessment Template and does not fail."""
    asmt_tmpl = factories.AssessmentTemplateFactory(
        title="template new",
        template_object_type="Objective",
    )
    slug = asmt_tmpl.slug
    asmt_tmpl_data = [
        collections.OrderedDict([
            ("object_type", "Assessment Template"),
            ("Code*", slug),
            ("Default Assessment Type", "Control"),
            ("Title", "template upd"),
        ])
    ]
    response = self.import_data(*asmt_tmpl_data)
    self._check_csv_response(response, {})
    template = models.AssessmentTemplate.query.filter(
        models.AssessmentTemplate.slug == slug).first()

    self.assertEqual(template.title, 'template upd')
    self.assertEqual(template.template_object_type, 'Control')

  def test_modify_persons_over_import(self):
    """Test import modifies Assessment Template and does not fail."""
    assessment_template = factories.AssessmentTemplateFactory(
        default_people={"assignees": "Admin", "verifiers": "Admin"}
    )
    slug = assessment_template.slug
    asmt_tmpl_data = [
        collections.OrderedDict([
            ("object_type", "Assessment Template"),
            ("Code*", slug),
            ("Default Assignees*", "Auditors"),
            ("Default Assessment Type", "Control"),
            ("Title", "Template 1"),
            ("Default Verifiers", "Secondary Contacts"),
        ])
    ]
    response = self.import_data(*asmt_tmpl_data)
    template = models.AssessmentTemplate.query \
        .filter(models.AssessmentTemplate.slug == slug) \
        .first()
    self._check_csv_response(response, {})
    self.assertEqual(template.default_people["verifiers"],
                     "Secondary Contacts")
    self.assertEqual(template.default_people["assignees"], "Auditors")

  def test_invalid_import(self):
    """Test invalid import."""
    audit = factories.AuditFactory()
    assessment_data_template = [
        collections.OrderedDict([
            ("object_type", "Assessment Template"),
            ("Code*", ""),
            ("Audit*", audit.slug),
            ("Default Assignees*", "Auditors"),
            ("Default Verifiers", "user4@a.com"),
            ("Default Assessment Type", "Control"),
            ("Title", "Template 1"),
        ])
    ]
    response = self.import_data(*assessment_data_template)

    expected_messages = {
        "Assessment Template": {
            "rows": 1,
            "updated": 0,
            "created": 1,
            "row_warnings": {
                errors.UNKNOWN_USER_WARNING.format(
                    line=3,
                    column_name="Default Verifiers",
                    email="user4@a.com",
                ),
            },
        }
    }
    self._check_csv_response(response, expected_messages)

  def test_duplicated_gcad_import(self):
    """Test import of LCAD with same name as GCAD."""
    cad_title = "Test GCA"
    with factories.single_commit():
      factories.CustomAttributeDefinitionFactory(
          definition_type="assessment",
          title=cad_title,
      )
      audit = factories.AuditFactory()

    response = self.import_data(collections.OrderedDict([
        ("object_type", "Assessment_Template"),
        ("Code*", ""),
        ("Audit*", audit.slug),
        ("Default Assignees", "user@example.com"),
        ("Default Verifiers", "user@example.com"),
        ("Title", "Title"),
        ("Default Assessment Type", "Control"),
        ("Custom Attributes", "Text, {}".format(cad_title)),
    ]))

    expected_messages = {
        "Assessment Template": {
            "rows": 1,
            "updated": 0,
            "created": 0,
            "row_warnings": set(),
            "row_errors": {
                errors.ERROR_TEMPLATE.format(
                    line=3,
                    message=common_errors.DUPLICATE_GCAD_NAME.format(
                        attr_name=cad_title
                    ),
                )
            },
        }
    }
    self._check_csv_response(response, expected_messages)

  def test_duplicated_acr_import(self):
    """Test import of LCAD with same name as GCAD."""
    acr_name = "Test ACR"
    with factories.single_commit():
      factories.AccessControlRoleFactory(
          object_type="Assessment",
          name=acr_name,
      )
      audit = factories.AuditFactory()

    response = self.import_data(collections.OrderedDict([
        ("object_type", "Assessment_Template"),
        ("Code*", ""),
        ("Audit*", audit.slug),
        ("Default Assignees", "user@example.com"),
        ("Default Verifiers", "user@example.com"),
        ("Title", "Title"),
        ("Default Assessment Type", "Control"),
        ("Custom Attributes", "Text, {}".format(acr_name)),
    ]))

    expected_messages = {
        "Assessment Template": {
            "rows": 1,
            "updated": 0,
            "created": 0,
            "row_warnings": set(),
            "row_errors": {
                errors.ERROR_TEMPLATE.format(
                    line=3,
                    message=common_errors.DUPLICATE_CUSTOM_ROLE.format(
                        role_name=acr_name
                    ),
                )
            },
        }
    }
    self._check_csv_response(response, expected_messages)
