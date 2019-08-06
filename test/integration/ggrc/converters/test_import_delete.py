# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests import delete test cases"""

import collections
from ggrc import models
from integration.ggrc import TestCase
from integration.ggrc.models import factories


class TestUnmappingViaImport(TestCase):
  """Tests unmapping via import"""

  def setUp(self):
    super(TestUnmappingViaImport, self).setUp()
    self.client.get("/login")

  def test_unmapping_not_mapped_object(self):  # pylint: disable=invalid-name
    """Test unmapping of regulations that wasn't mapped to program"""
    factories.ProgramFactory()
    factories.ProgramFactory()

    programs = models.Program.query.all()
    regulation_data = [
        collections.OrderedDict([
            ("object_type", "Regulation"),
            ("Code*", programs[0].slug),
            ("Delete", "yes")
        ]),
        collections.OrderedDict([
            ("object_type", "Regulation"),
            ("Code*", programs[1].slug),
            ("Delete", "force")
        ]),
    ]
    response_data = self.import_data(*regulation_data)

    self.assertEqual(response_data[0]["deleted"], 0)
    self.assertEqual(response_data[0]["ignored"], 2)
    self.assertEqual(
        models.Program.query.count(),
        2,
    )
