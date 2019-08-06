# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for bulk updates with CSV import."""

import collections

from ggrc import models
from integration.ggrc import TestCase
from integration.ggrc.models import factories


class TestImportUpdates(TestCase):

  """ Test importing of already existing objects """

  def setUp(self):
    super(TestImportUpdates, self).setUp()
    self.client.get("/login")

  def test_policy_basic_update(self):
    """ Test simple policy title update """
    with factories.single_commit():
      person = factories.PersonFactory(name="User-1",
                                       email="user1@example.com")
      policy = factories.PolicyFactory()
      policy_slug = policy.slug

    revision_count = models.Revision.query.filter(
        models.Revision.resource_type == "Policy",
        models.Revision.resource_id == policy.id
    ).count()
    self.assertEqual(revision_count, 1)

    updated_policy_data = [
        collections.OrderedDict([
            ("object_type", "Policy"),
            ("Code*", policy_slug),
            ("Title*", "Updated Policy"),
            ("Admin*", person.email),
        ]),
    ]

    self.import_data(*updated_policy_data)

    policy = models.Policy.query.filter_by(slug=policy_slug).first()
    person = models.Person.query.filter_by(email="user1@example.com").first()

    self.assertEqual(policy.title, "Updated Policy")
    self.assert_roles(policy, Admin=person)
    revision_count = models.Revision.query.filter(
        models.Revision.resource_type == "Policy",
        models.Revision.resource_id == policy.id
    ).count()
    self.assertEqual(revision_count, 2)
