# coding: utf-8

# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for /query api search"""

import ddt

from ggrc.models import all_models

from integration.ggrc import TestCase
from integration.ggrc import api_helper
from integration.ggrc.models import factories
from integration.ggrc_basic_permissions.models \
    import factories as rbac_factories


@ddt.ddt
class TestPeopleSearch(TestCase):
  """Tests for /query api for Search."""

  def setUp(self):
    super(TestPeopleSearch, self).setUp()
    self.api = api_helper.Api()
    self.client.get("/login")
    self.client.post("/admin/full_reindex")

  @ddt.data("", "Creator", "Editor", "Reader", "Administrator")
  def test_search_people_by_auth(self, search_role):
    """Test people search by authorization {}."""
    with factories.single_commit():
      roles = ["Creator", "Editor", "Reader", "Administrator"]
      for role in roles:
        person = factories.PersonFactory()
        creator_role = all_models.Role.query.filter(
            all_models.Role.name == role
        ).one()
        rbac_factories.UserRoleFactory(role=creator_role, person=person)

    query_request_data = [{
        "object_name": "Person",
        "filters": {
            "expression": {
                "left": "System Authorizations",
                "op": {"name": "~"},
                "right": search_role,
            },
        },
        "type": "values",
    }]

    response = self.api.send_request(self.api.client.post,
                                     data=query_request_data,
                                     api_link="/query")
    self.assertStatus(response, 200)
    actual_users = []
    for user in response.json[0]["Person"]["values"]:
      actual_users.append(user["email"])

    all_users = all_models.Person.query
    expected_users = [user.email for user in all_users if not search_role or
                      user.system_wide_role == search_role]

    self.assertItemsEqual(actual_users, expected_users)
