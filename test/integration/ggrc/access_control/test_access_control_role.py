# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test Access Control Role"""
from collections import OrderedDict, defaultdict

import ddt

from ggrc.access_control.role import AccessControlRole
from ggrc.converters import errors
from ggrc.models import all_models
from integration.ggrc import TestCase
from integration.ggrc.api_helper import Api
from integration.ggrc.models.factories import random_str
from integration.ggrc.models import factories
from integration.ggrc.generator import ObjectGenerator

ROLE_NAME = "ACR for mandatory test"
MANDATORY_ROLE_RESPONSE = {
    "Control": {"row_warnings": {errors.OWNER_MISSING.format(
        line=3, column_name=ROLE_NAME)}}}
NON_MANDATORY_ROLE_RESPONSE = {}


@ddt.ddt
class TestAccessControlRole(TestCase):
  """TestAccessControlRole"""

  def setUp(self):
    self.clear_data()
    super(TestAccessControlRole, self).setUp()
    self.api = Api()
    self.object_generator = ObjectGenerator()
    self.people = {}
    for name in ["Creator", "Reader", "Editor"]:
      _, user = self.object_generator.generate_person(
          data={"name": name}, user_role=name)
      self.people[name] = user

  def _post_role(self):
    """Helper function for POSTing roles"""
    name = random_str(prefix="Access Control Role - ")
    return self.api.post(AccessControlRole, {
        "access_control_role": {
            "name": name,
            "object_type": "Control",
            "context": None,
            "read": True
        },
    })

  def test_create(self):
    """Test Access Control Role creation"""
    response = self._post_role()
    assert response.status_code == 201, \
        "Failed to create a new access control role, response was {}".format(
            response.status)

    id_ = response.json['access_control_role']['id']
    role = AccessControlRole.query.filter(AccessControlRole.id == id_).first()
    assert role.read == 1, \
        "Read permission not correctly saved {}".format(role.read)
    assert role.update == 1, \
        "Update permission not correctly saved {}".format(role.update)
    assert role.delete == 1, \
        "Update permission not correctly saved {}".format(role.delete)

  @ddt.data({"mandatory": True, "exp_response": MANDATORY_ROLE_RESPONSE},
            {"mandatory": False, "exp_response": NON_MANDATORY_ROLE_RESPONSE})
  @ddt.unpack
  def test_mandatory_delete(self, mandatory, exp_response):
    """Test set empty field via import if acr mandatory is {mandatory}"""
    with factories.single_commit():
      user = factories.PersonFactory()
      control = factories.ControlFactory()
      role = factories.AccessControlRoleFactory(name=ROLE_NAME,
                                                object_type="Control",
                                                mandatory=mandatory)
      role_id = role.id
      factories.AccessControlListFactory(person=user,
                                         ac_role_id=role.id,
                                         object=control)
    response = self.import_data(OrderedDict([
        ("object_type", "Control"),
        ("Code*", control.slug),
        (ROLE_NAME, "--"),
    ]))
    self._check_csv_response(response, exp_response)
    db_data = defaultdict(set)
    for acl in all_models.Control.query.get(control.id).access_control_list:
      db_data[acl.ac_role_id].add(acl.person_id)
    if mandatory:
      cur_user = all_models.Person.query.filter_by(
          email="user@example.com").first()
      self.assertEqual(set([cur_user.id]), db_data[role_id])
    else:
      self.assertFalse(db_data[role_id])

  def test_only_admin_can_post(self):
    """Only admin users should be able to POST access control roles"""
    for name in ("Creator", "Reader", "Editor"):
      person = self.people.get(name)
      self.api.set_user(person)
      response = self._post_role()
      assert response.status_code == 403, \
          "Non admins should get forbidden error when POSTing role. {}".format(
              response.status)

  @ddt.data(
      ("name", "New ACR"),
      ("read", False),
      ("mandatory", False),
      ("non_editable", False),
  )
  @ddt.unpack
  def test_modify_non_editable_role(self, field_name, field_value):
    """Test if user can modify non-editable role"""
    # Primary Contacts role of Control is non-editable
    ac_role = AccessControlRole.query.filter_by(
        object_type="Control",
        name="Primary Contacts",
    ).first()

    response = self.api.put(ac_role, {field_name: field_value})
    assert response.status_code == 403, \
        "Forbidden error should be thrown when non-editable " \
        "role {} updated.".format(ac_role.name)

  def test_delete_non_editable_role(self):
    """Test if user can delete non-editable role"""
    # Primary Contacts role of Control is non-editable
    ac_role = AccessControlRole.query.filter_by(
        object_type="Control",
        name="Primary Contacts",
    ).first()

    response = self.api.delete(ac_role)
    assert response.status_code == 403, \
        "Forbidden error should be thrown when non-editable " \
        "role {} deleted.".format(ac_role.name)
