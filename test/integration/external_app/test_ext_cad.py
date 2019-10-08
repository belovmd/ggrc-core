# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Tests external CAD actions (create, update, etc.)"""

import json

import ddt

from ggrc import models
from ggrc.models import all_models
from ggrc.models import custom_attribute_definition as cad
from integration import ggrc
from integration.external_app import external_api_helper
from integration.ggrc import query_helper
from integration.ggrc.models import factories
from integration.ggrc.services.test_custom_attributes import ProductTestCase


@ddt.ddt
class TestExternalGlobalCustomAttributes(ProductTestCase):
  """Test case for external cads."""

  @classmethod
  def setUpClass(cls):
    cls.api = external_api_helper.ExternalApiClient()

  @staticmethod
  def _get_text_payload():
    """Gets payload for text GCA.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "id": 1,
        "title": "GCA Text",
        "attribute_type": "Text",
        "definition_type": "control",
        "mandatory": False,
        "helptext": "GCA Text attribute",
        "placeholder": "Input text",
        "context": None,
        "external_id": 1,
    }

  @staticmethod
  def _get_rich_text_payload():
    """Gets payload for rich text GCA.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "id": 1,
        "title": "GCA Rich Text",
        "attribute_type": "Rich Text",
        "definition_type": "control",
        "mandatory": False,
        "helptext": "GCA Text attribute",
        "placeholder": "Input text",
        "context": None,
        "external_id": 1,
    }

  @staticmethod
  def _get_date_payload():
    """Gets payload for date GCA.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "id": 1,
        "title": "GCA Date",
        "attribute_type": "Date",
        "definition_type": "control",
        "mandatory": False,
        "helptext": "GCA Date attribute",
        "context": None,
        "external_id": 1,
    }

  @staticmethod
  def _get_dropdown_payload():
    """Gets payload for dropdown GCA.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "id": 1,
        "title": "GCA Dropdown",
        "attribute_type": "Dropdown",
        "definition_type": "control",
        "mandatory": False,
        "helptext": "GCA Dropdown attribute",
        "context": None,
        "external_id": 1,
        "multi_choice_options": "1,3,2",
    }

  @staticmethod
  def _get_multiselect_payload():
    """Gets payload for multiselect GCA.

    Returns:
      Dictionary with attribute configuration.
    """
    return {
        "id": 1,
        "title": "GCA Multiselect",
        "attribute_type": "Multiselect",
        "definition_type": "control",
        "mandatory": False,
        "helptext": "GCA Multiselect attribute",
        "context": None,
        "external_id": 1,
        "multi_choice_options": "1,3,2",
    }

  @classmethod
  def _get_payload(cls, attribute_type):
    """Gets payload for GCA by attribute type.

    Args:
      attribute_type: String representation of attribute type.
    Returns:
      Dictionary with attribute configuration.
    """
    payload_handlers = {
        "Text": cls._get_text_payload,
        "Rich Text": cls._get_rich_text_payload,
        "Date": cls._get_date_payload,
        "Dropdown": cls._get_dropdown_payload,
        "Multiselect": cls._get_multiselect_payload,
    }

    return payload_handlers[attribute_type]()

  def _run_text_asserts(self, external_cad, attribute_payload):
    """Runs CAD text/rich asserts.

    Args:
      external_cad: CAD for validation.
      attribute_payload: Dictionary with attribute configuration.
    """
    self.assertEqual(
        external_cad.title,
        attribute_payload["title"]
    )
    self.assertEqual(
        external_cad.definition_type,
        attribute_payload["definition_type"]
    )
    self.assertEqual(
        external_cad.attribute_type,
        attribute_payload["attribute_type"]
    )
    self.assertEqual(
        external_cad.mandatory,
        attribute_payload["mandatory"]
    )
    self.assertEqual(
        external_cad.helptext,
        attribute_payload["helptext"]
    )
    self.assertEqual(
        external_cad.placeholder,
        attribute_payload["placeholder"]
    )

  def _run_date_asserts(self, external_cad, attribute_payload):
    """Runs CAD date asserts.

    Args:
      external_cad: CAD for validation.
      attribute_payload: Dictionary with attribute configuration.
    """
    self.assertEqual(
        external_cad.title,
        attribute_payload["title"]
    )
    self.assertEqual(
        external_cad.definition_type,
        attribute_payload["definition_type"]
    )
    self.assertEqual(
        external_cad.attribute_type,
        attribute_payload["attribute_type"]
    )
    self.assertEqual(
        external_cad.mandatory,
        attribute_payload["mandatory"]
    )
    self.assertEqual(
        external_cad.helptext,
        attribute_payload["helptext"]
    )

  def _run_select_asserts(self, external_cad, attribute_payload):
    """Runs CAD dropdown/multiselect asserts.

    Args:
      external_cad: CAD for validation.
      attribute_payload: Dictionary with attribute configuration.
    """
    self.assertEqual(
        external_cad.title,
        attribute_payload["title"]
    )
    self.assertEqual(
        external_cad.definition_type,
        attribute_payload["definition_type"]
    )
    self.assertEqual(
        external_cad.attribute_type,
        attribute_payload["attribute_type"]
    )
    self.assertEqual(
        external_cad.mandatory,
        attribute_payload["mandatory"]
    )
    self.assertEqual(
        external_cad.helptext,
        attribute_payload["helptext"]
    )
    self.assertEqual(
        external_cad.multi_choice_options,
        attribute_payload["multi_choice_options"]
    )

  def _run_cad_asserts(self, attribute_type, external_cad, attribute_payload):
    """Runs CAD asserts by attribute type.

    Args:
      external_cad: CAD for validation.
      attribute_type: String representation of attribute type.
      attribute_payload: Dictionary with attribute configuration.
    """
    asserts = {
        "Text": self._run_text_asserts,
        "Rich Text": self._run_text_asserts,
        "Date": self._run_date_asserts,
        "Dropdown": self._run_select_asserts,
        "Multiselect": self._run_select_asserts,
    }
    asserts[attribute_type](external_cad, attribute_payload)

  @ddt.data("Text", "Rich Text", "Date", "Dropdown", "Multiselect")
  def test_create_custom_attribute(self, attribute_type):
    """Test for create external CAD validation."""
    attribute_payload = self._get_payload(attribute_type)
    payload = [
        {
            "external_custom_attribute_definition": attribute_payload,
        }
    ]

    response = self.api.post(
        all_models.ExternalCustomAttributeDefinition,
        data=payload
    )

    self.assertEqual(response.status_code, 200)
    ex_cad = all_models.ExternalCustomAttributeDefinition.eager_query().first()
    self._run_cad_asserts(attribute_type, ex_cad, attribute_payload)

  @ddt.data("Text", "Rich Text", "Date", "Dropdown", "Multiselect")
  def test_create_cad_wh_id(self, attribute_type):
    """Test create CAD without id."""
    attribute_payload = self._get_payload(attribute_type)
    attribute_payload.pop("id")

    payload = [
        {
            "external_custom_attribute_definition": attribute_payload,
        }
    ]

    response = self.api.post(
        all_models.ExternalCustomAttributeDefinition,
        data=payload
    )

    self.assertEqual(response.status_code, 400)
    self.assertIn("id for the CAD is not specified.", response.data)

  @ddt.data("Text", "Rich Text", "Date", "Dropdown", "Multiselect")
  def test_update_custom_attribute(self, attribute_type):
    """Test for update external CAD validation."""
    external_cad = factories.ExternalCustomAttributeDefinitionFactory(
        title="GCA example",
        definition_type="control",
    )
    attribute_payload = self._get_payload(attribute_type)
    attribute_payload['id'] = external_cad.id
    payload = {
        "external_custom_attribute_definition": attribute_payload,
    }

    response = self.api.put(
        all_models.ExternalCustomAttributeDefinition,
        obj_id=external_cad.id,
        data=payload
    )

    self.assertEqual(response.status_code, 200)
    ex_cad = all_models.ExternalCustomAttributeDefinition.eager_query().first()
    self._run_cad_asserts(attribute_type, ex_cad, attribute_payload)

  @ddt.data("Text", "Rich Text", "Date", "Dropdown", "Multiselect")
  def test_update_cad_wh_id(self, attribute_type):
    """Test update CAD without id."""
    external_cad = factories.ExternalCustomAttributeDefinitionFactory(
        title="GCA example",
        definition_type="control",
    )
    attribute_payload = self._get_payload(attribute_type)
    attribute_payload.pop("id")

    payload = {
        "external_custom_attribute_definition": attribute_payload,
    }

    response = self.api.put(
        all_models.ExternalCustomAttributeDefinition,
        obj_id=external_cad.id,
        data=payload
    )

    self.assertEqual(response.status_code, 400)
    self.assertIn("id for the CAD is not specified.", response.data)

  @ddt.data("Text", "Rich Text", "Date", "Dropdown", "Multiselect")
  def test_get_custom_attribute(self, attribute_type):
    """Test for get external CAD validation."""
    attribute_payload = self._get_payload(attribute_type)
    external_cad = factories.ExternalCustomAttributeDefinitionFactory(
        **attribute_payload
    )

    response = self.api.get(
        all_models.ExternalCustomAttributeDefinition,
        external_cad.id
    )

    self.assertEqual(response.status_code, 200)
    response_json = json.loads(response.data)
    self._run_cad_asserts(
        attribute_type,
        external_cad,
        response_json["external_custom_attribute_definition"]
    )


@ddt.ddt
class TestECADReindex(query_helper.WithQueryApi, ggrc.TestCase):
  """Tests reindex after CustomAttributeDefinition changes"""
  def setUp(self):
    super(TestECADReindex, self).setUp()
    self.client.get("/login")
    self.ext_api = external_api_helper.ExternalApiClient()

  @staticmethod
  def _create_cad_body(title, attribute_type, definition_type, model_name):
    """Create body for eCAD POST request"""
    body = {
        "external_custom_attribute_definition": {
            "id": 1,
            "external_id": 2,
            "title": title,
            "attribute_type": attribute_type,
            "definition_type": definition_type,
            "modal_title": "Add Attribute to type %s" % model_name,
            "mandatory": False,
            "helptext": "",
            "placeholder": "",
            "context": {
                "id": None
            }
        }
    }
    if attribute_type == "Multiselect":
      body["external_custom_attribute_definition"][
          "multi_choice_options"] = "yes,no"
    return body

  @ddt.data(
      ("control", "Multiselect", ""),
      ("control", "Dropdown", ""),
      ("risk", "Rich Text", ""),
      ("risk", "Text", ""),
      ("risk", "Date", ""),
  )
  @ddt.unpack
  def test_reindex_cad_create(self, definition_type, attribute_type, value):
    """Test reindex after CAD creating"""
    model_name = cad.get_inflector_model_name_dict()[definition_type]
    model_id = factories.get_model_factory(model_name)().id
    expected = [model_id]
    title = "test_title %s %s" % (definition_type, attribute_type)
    cad_model = models.all_models.ExternalCustomAttributeDefinition
    response = self.ext_api.post(
        cad_model,
        data=[
            self._create_cad_body(
                title, attribute_type, definition_type, model_name
            )
        ]
    )
    self.assert200(response)
    ids = self.simple_query(
        model_name,
        expression=[title, "=", value],
        type_="ids",
        field="ids"
    )
    self.assertItemsEqual(ids, expected)

  @ddt.data(
      ("Date", None, "2019-08-01"),
      ("Multiselect", "yes,no", "no,yes"),
      ("Rich Text", None, "sample text"),
      ("Text", None, "sample text"),
      ("Dropdown", "one,two,three,four,five", "four"),
  )
  @ddt.unpack
  def test_control_reindex(self, attribute_type, multi_choice_options,
                           attribute_value):
    """Test reindex of control after edit of eCAV"""
    with factories.single_commit():
      ecad = factories.ExternalCustomAttributeDefinitionFactory(
          definition_type="control",
          attribute_type=attribute_type,
          multi_choice_options=multi_choice_options,
      )
      control = factories.ControlFactory(slug="Control 1")
    response = self.ext_api.put(control, control.id, data={
        "custom_attribute_values": [{
            "attributable_id": control.id,
            "attributable_type": "Control",
            "custom_attribute_id": ecad.id,
            "attribute_value": attribute_value,
        }]
    })
    self.assert200(response)
    ids = self.simple_query(
        "Control",
        expression=[ecad.title, "=", attribute_value],
        type_="ids",
        field="ids"
    )
    self.assertItemsEqual(ids, [control.id])


@ddt.ddt
class TestExtSnapshotting(query_helper.WithQueryApi, ggrc.TestCase):
  """Test snapshotting of objects with external CADs."""

  def setUp(self):
    super(TestExtSnapshotting, self).setUp()
    self.ext_api = external_api_helper.ExternalApiClient()
    self.client.get("/login")

  @ddt.data(
      ("Date", None, "2019-08-01"),
      ("Multiselect", "yes,no", "no,yes"),
      ("Rich Text", None, "sample text"),
      ("Text", None, "sample text"),
      ("Dropdown", "one,two,three,four,five", "four"),
  )
  @ddt.unpack
  def test_control_snapshotting(self, attribute_type, multi_choice_options,
                                attribute_value):
    """Test revisions and snapshots content contains
    external custom attributes."""
    with factories.single_commit():
      control = factories.ControlFactory(slug="Control 1")
      ecad = factories.ExternalCustomAttributeDefinitionFactory(
          definition_type="control",
          attribute_type=attribute_type,
          multi_choice_options=multi_choice_options,
      )
      factories.ExternalCustomAttributeValueFactory(
          custom_attribute=ecad,
          attributable=control,
          attribute_value=attribute_value,
      )
      audit = factories.AuditFactory()
    snapshots = self._create_snapshots(audit, [control])
    content = snapshots[0].revision.content
    self.assertEqual(content["custom_attribute_definitions"][0]["title"],
                     ecad.title)
    self.assertEqual(content["custom_attribute_values"][0]["attribute_value"],
                     attribute_value)


class TestECADResponse(ggrc.TestCase):
  """Check response from API of eCAD content"""

  def setUp(self):
    super(TestECADResponse, self).setUp()
    self.ext_api = external_api_helper.ExternalApiClient()
    self.client.get("/login")

  def test_cad_response(self):
    """Test response after creation of eCAD"""
    cad_body = {
        "external_custom_attribute_definition": {
            "id": 1,
            "external_id": 2,
            "title": "ECAD TiTle",
            "attribute_type": "Dropdown",
            "definition_type": "risk",
            "mandatory": True,
            "helptext": "Help Text",
            "placeholder": "Some Placeholder",
            "multi_choice_options": "opt1,opt2",
        }
    }
    ecad_model = models.all_models.ExternalCustomAttributeDefinition
    response = self.ext_api.post(ecad_model, data=cad_body)
    self.assert201(response)
    check_attrs = cad_body["external_custom_attribute_definition"].keys()
    for attr in check_attrs:
      self.assertIn(attr,
                    response.json["external_custom_attribute_definition"])
      self.assertEqual(
          response.json["external_custom_attribute_definition"][attr],
          cad_body["external_custom_attribute_definition"][attr])

  def test_cav_response(self):
    """Test response after creation of eCAD"""
    cad_body = {
        "external_custom_attribute_definition": {
            "id": 1,
            "external_id": 2,
            "title": "ECAD TiTle",
            "attribute_type": "Dropdown",
            "definition_type": "control",
            "mandatory": True,
            "helptext": "Help Text",
            "placeholder": "Some Placeholder",
            "multi_choice_options": "opt1,opt2",
        }
    }
    ecad_model = models.all_models.ExternalCustomAttributeDefinition
    cad_response = self.ext_api.post(ecad_model, data=cad_body)
    self.assert201(cad_response)
    control = factories.ControlFactory(slug="Control 1")
    cav_body = {
        "custom_attribute_values": [{
            "id": 1,
            "external_id": 2,
            "attributable_id": control.id,
            "attributable_type": "Control",
            "custom_attribute_id": 1,
            "attribute_value": "opt2",
        }]
    }
    response = self.ext_api.put(control, control.id, data=cav_body)
    self.assert200(response)
    cav_response = self.ext_api.get(control, control.id)
    json_cav = cav_response.json["control"]["custom_attribute_values"]
    check_attrs = cav_body["custom_attribute_values"][0].keys()
    for attr in check_attrs:
      self.assertIn(attr, json_cav[0])
      self.assertEqual(json_cav[0][attr],
                       cav_body["custom_attribute_values"][0][attr])
