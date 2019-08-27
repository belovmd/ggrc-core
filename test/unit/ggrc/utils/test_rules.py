# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Unit test for checking fields in mapping and unmapping."""

import unittest

from ddt import data, ddt, unpack

import ggrc.utils.rules


class BaseTestMappingRules(unittest.TestCase):
  """Base TestCase for mapping and unmapping check."""

  rules = {}

  def assertRules(self, model, *rules):  # pylint: disable=C0103
    """Assert to check rules for current model in mapping rules."""
    self.assertIn(model, self.rules)
    self.assertEqual(set(rules), self.rules[model])


@ddt
class TestMappingRules(BaseTestMappingRules):
  """Test case for mapping rules."""

  rules = ggrc.utils.rules.get_mapping_rules()

  all_rules = ['AccessGroup', 'Contract', 'Control',
               'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
               'Market', 'Objective', 'OrgGroup', 'Policy',
               'Process', 'Product', 'Program', 'Project', 'Regulation',
               'Risk', 'Requirement', 'Standard', 'System', 'Threat', 'Vendor',
               'Metric', 'ProductGroup', 'TechnologyEnvironment', 'KeyReport',
               'AccountBalance']
  assessment_rules = ['Issue']
  audit_rules = ['Assessment', 'Issue']
  accessgroup_rules = ['Contract', 'Control',
                       'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                       'Issue', 'Market', 'Objective', 'OrgGroup',
                       'Policy', 'Process', 'Product', 'Program', 'Project',
                       'Regulation', 'Risk', 'Requirement', 'Standard',
                       'System', 'Threat', 'Vendor', 'Metric', 'ProductGroup',
                       'TechnologyEnvironment', 'KeyReport', 'AccountBalance']
  contract_rules = ['AccessGroup', 'Control',
                    'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                    'Issue', 'Market', 'Objective', 'OrgGroup',
                    'Process', 'Product', 'Program', 'Project', 'Risk',
                    'Requirement', 'System', 'Threat', 'Vendor', 'Metric',
                    'ProductGroup', 'TechnologyEnvironment', 'Standard',
                    'Policy', 'Regulation', 'KeyReport', 'AccountBalance']
  cycletaskgroupobjecttask_rules = ['AccessGroup', 'Audit', 'Contract',
                                    'Control', 'DataAsset', 'Facility',
                                    'Issue', 'Market', 'Objective', 'OrgGroup',
                                    'Policy', 'Process', 'Product',
                                    'Program', 'Project', 'Regulation', 'Risk',
                                    'Requirement', 'Standard', 'System',
                                    'Threat', 'Vendor', 'Metric', 'KeyReport',
                                    'ProductGroup', 'TechnologyEnvironment',
                                    'AccountBalance']
  issue_rules = ['AccessGroup', 'Assessment', 'Audit',
                 'Contract', 'Control', 'CycleTaskGroupObjectTask',
                 'DataAsset', 'Facility', 'Issue', 'Market',
                 'Objective', 'OrgGroup', 'Policy',
                 'Process', 'Product', 'Program', 'Project',
                 'Regulation', 'Risk', 'Requirement',
                 'Standard', 'System', 'Threat', 'Vendor', 'Metric',
                 'ProductGroup', 'TechnologyEnvironment', 'KeyReport',
                 'AccountBalance']
  person_rules = ['AccessGroup', 'Contract', 'Control',
                  'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
                  'Market', 'Objective', 'OrgGroup', 'Policy', 'Process',
                  'Product', 'Program', 'Project', 'Regulation', 'Risk',
                  'Requirement', 'Standard', 'System', 'Threat', 'Vendor',
                  'Metric', 'ProductGroup', 'TechnologyEnvironment',
                  'KeyReport', 'AccountBalance']
  policy_rules = ['AccessGroup', 'Control',
                  'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
                  'Market', 'Objective', 'OrgGroup', 'Process',
                  'Product', 'Program', 'Project', 'Risk', 'Requirement',
                  'System', 'Threat', 'Vendor', 'Metric', 'ProductGroup',
                  'TechnologyEnvironment', 'Standard', 'Regulation',
                  'Contract', 'KeyReport', 'AccountBalance']
  program_rules = ['AccessGroup', 'Contract', 'Control',
                   'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                   'Issue', 'Market', 'Objective', 'OrgGroup',
                   'Policy', 'Process', 'Product', 'Project', 'Regulation',
                   'Risk', 'Requirement', 'Standard', 'System', 'Threat',
                   'Vendor', 'Metric', 'ProductGroup', 'TechnologyEnvironment',
                   'KeyReport', 'AccountBalance']
  regulation_rules = ['AccessGroup', 'Control',
                      'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                      'Issue', 'Market', 'Objective', 'OrgGroup',
                      'Process', 'Product', 'Program', 'Project', 'Risk',
                      'Requirement', 'System', 'Threat', 'Vendor', 'Metric',
                      'ProductGroup', 'TechnologyEnvironment', 'Standard',
                      'Policy', 'Contract', 'KeyReport', 'AccountBalance']
  risk_rules = ['AccessGroup', 'Contract', 'Control',
                'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
                'Market', 'Objective', 'OrgGroup', 'Policy',
                'Process', 'Product', 'Program', 'Project', 'Regulation',
                'Requirement', 'Standard', 'System', 'Threat', 'Vendor',
                'Metric', 'ProductGroup', 'TechnologyEnvironment', 'KeyReport',
                'AccountBalance']
  standard_rules = ['AccessGroup', 'Control',
                    'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                    'Issue', 'Market', 'Objective', 'OrgGroup',
                    'Process', 'Product', 'Program', 'Project', 'Risk',
                    'Requirement', 'System', 'Threat', 'Vendor', 'Metric',
                    'ProductGroup', 'TechnologyEnvironment', 'Policy',
                    'Regulation', 'Contract', 'KeyReport', 'AccountBalance']
  threat_rules = ['AccessGroup', 'Contract', 'Control',
                  'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
                  'Market', 'Objective', 'OrgGroup', 'Policy',
                  'Process', 'Product', 'Program', 'Project', 'Regulation',
                  'Risk', 'Requirement', 'Standard', 'System', 'Vendor',
                  'Metric', 'ProductGroup', 'TechnologyEnvironment',
                  'KeyReport', 'AccountBalance']

  @data(("AccessGroup", accessgroup_rules),
        ("AccountBalance", all_rules),
        ("Assessment", assessment_rules),
        ("Audit", audit_rules),
        ("Contract", contract_rules),
        ("Control", all_rules),
        ("CycleTaskGroupObjectTask", cycletaskgroupobjecttask_rules),
        ("DataAsset", all_rules),
        ("Facility", all_rules),
        ("Issue", issue_rules),
        ("Market", all_rules),
        ("Objective", all_rules),
        ("OrgGroup", all_rules),
        ("Person", person_rules),
        ("Policy", policy_rules),
        ("Process", all_rules),
        ("Product", all_rules),
        ("Program", program_rules),
        ("Project", all_rules),
        ("Regulation", regulation_rules),
        ("Risk", risk_rules),
        ("Requirement", all_rules),
        ("Standard", standard_rules),
        ("System", all_rules),
        ("Threat", threat_rules),
        ("Vendor", all_rules),
        ("Metric", all_rules),
        ("ProductGroup", all_rules),
        ("TechnologyEnvironment", all_rules),
        ("KeyReport", all_rules))
  @unpack
  def test_field(self, field, rules):
    """Test mapping rules for {0}."""
    self.assertRules(field, *rules)


@ddt
class TestUnMappingRules(BaseTestMappingRules):
  """Test case for unmapping rules."""

  rules = ggrc.utils.rules.get_unmapping_rules()

  all_rules = ['AccessGroup', 'Contract', 'Control',
               'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
               'Market', 'Objective', 'OrgGroup', 'Policy',
               'Process', 'Product', 'Program', 'Project', 'Regulation',
               'Risk', 'Requirement', 'Standard', 'System', 'Threat', 'Vendor',
               'Metric', 'ProductGroup', 'TechnologyEnvironment', 'KeyReport',
               'AccountBalance']
  assessment_rules = ['Issue']
  audit_rules = ['Issue']
  accessgroup_rules = ['Contract', 'Control',
                       'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                       'Issue', 'Market', 'Objective', 'OrgGroup',
                       'Policy', 'Process', 'Product', 'Program', 'Project',
                       'Regulation', 'Risk', 'Requirement', 'Standard',
                       'System', 'Threat', 'Vendor', 'Metric', 'ProductGroup',
                       'TechnologyEnvironment', 'KeyReport', 'AccountBalance']
  contract_rules = ['AccessGroup', 'Control',
                    'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                    'Issue', 'Market', 'Objective', 'OrgGroup',
                    'Process', 'Product', 'Program', 'Project', 'Risk',
                    'Requirement', 'System', 'Threat', 'Vendor', 'Metric',
                    'ProductGroup', 'TechnologyEnvironment', 'Standard',
                    'Policy', 'Regulation', 'KeyReport', 'AccountBalance']
  cycletaskgroupobjecttask_rules = ['AccessGroup', 'Audit', 'Contract',
                                    'Control', 'DataAsset', 'Facility',
                                    'Issue', 'Market', 'Objective', 'OrgGroup',
                                    'Policy', 'Process', 'Product',
                                    'Program', 'Project', 'Regulation', 'Risk',
                                    'Requirement', 'Standard', 'System',
                                    'Threat', 'Vendor', 'Metric', 'KeyReport',
                                    'ProductGroup', 'TechnologyEnvironment',
                                    'AccountBalance']
  issue_rules = ['AccessGroup', 'Assessment', 'Audit',
                 'Contract', 'Control', 'CycleTaskGroupObjectTask',
                 'DataAsset', 'Facility', 'Issue', 'Market',
                 'Objective', 'OrgGroup', 'Policy',
                 'Process', 'Product', 'Program', 'Project',
                 'Regulation', 'Risk', 'Requirement',
                 'Standard', 'System', 'Threat', 'Vendor', 'Metric',
                 'ProductGroup', 'TechnologyEnvironment', 'KeyReport',
                 'AccountBalance']
  person_rules = ['AccessGroup', 'Contract', 'Control',
                  'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
                  'Market', 'Objective', 'OrgGroup', 'Policy', 'Process',
                  'Product', 'Program', 'Project', 'Regulation', 'Risk',
                  'Requirement', 'Standard', 'System', 'Threat', 'Vendor',
                  'Metric', 'ProductGroup', 'TechnologyEnvironment',
                  'KeyReport', 'AccountBalance']
  policy_rules = ['AccessGroup', 'Control',
                  'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
                  'Market', 'Objective', 'OrgGroup', 'Process',
                  'Product', 'Program', 'Project', 'Risk', 'Requirement',
                  'System', 'Threat', 'Vendor', 'Metric', 'ProductGroup',
                  'TechnologyEnvironment', 'Standard', 'Regulation',
                  'Contract', 'KeyReport', 'AccountBalance']
  program_rules = ['AccessGroup', 'Contract', 'Control',
                   'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                   'Issue', 'Market', 'Objective', 'OrgGroup',
                   'Policy', 'Process', 'Product', 'Project', 'Regulation',
                   'Risk', 'Requirement', 'Standard', 'System', 'Threat',
                   'Vendor', 'Metric', 'ProductGroup', 'TechnologyEnvironment',
                   'KeyReport', 'AccountBalance']
  regulation_rules = ['AccessGroup', 'Control',
                      'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                      'Issue', 'Market', 'Objective', 'OrgGroup',
                      'Process', 'Product', 'Program', 'Project', 'Risk',
                      'Requirement', 'System', 'Threat', 'Vendor', 'Metric',
                      'ProductGroup', 'TechnologyEnvironment', 'Standard',
                      'Policy', 'Contract', 'KeyReport', 'AccountBalance']
  risk_rules = ['AccessGroup', 'Contract', 'Control',
                'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
                'Market', 'Objective', 'OrgGroup', 'Policy',
                'Process', 'Product', 'Program', 'Project', 'Regulation',
                'Requirement', 'Standard', 'System', 'Threat', 'Vendor',
                'Metric', 'ProductGroup', 'TechnologyEnvironment', 'KeyReport',
                'AccountBalance']
  standard_rules = ['AccessGroup', 'Control',
                    'CycleTaskGroupObjectTask', 'DataAsset', 'Facility',
                    'Issue', 'Market', 'Objective', 'OrgGroup',
                    'Process', 'Product', 'Program', 'Project', 'Risk',
                    'Requirement', 'System', 'Threat', 'Vendor', 'Metric',
                    'ProductGroup', 'TechnologyEnvironment', 'Policy',
                    'Regulation', 'Contract', 'KeyReport', 'AccountBalance']
  threat_rules = ['AccessGroup', 'Contract', 'Control',
                  'CycleTaskGroupObjectTask', 'DataAsset', 'Facility', 'Issue',
                  'Market', 'Objective', 'OrgGroup', 'Policy',
                  'Process', 'Product', 'Program', 'Project', 'Regulation',
                  'Risk', 'Requirement', 'Standard', 'System', 'Vendor',
                  'Metric', 'ProductGroup', 'TechnologyEnvironment',
                  'KeyReport', 'AccountBalance']

  @data(("AccessGroup", accessgroup_rules),
        ("AccountBalance", all_rules),
        ("Assessment", assessment_rules),
        ("Audit", audit_rules),
        ("Contract", contract_rules),
        ("Control", all_rules),
        ("CycleTaskGroupObjectTask", cycletaskgroupobjecttask_rules),
        ("DataAsset", all_rules),
        ("Facility", all_rules),
        ("Issue", issue_rules),
        ("Market", all_rules),
        ("Objective", all_rules),
        ("OrgGroup", all_rules),
        ("Person", person_rules),
        ("Policy", policy_rules),
        ("Process", all_rules),
        ("Product", all_rules),
        ("Program", program_rules),
        ("Project", all_rules),
        ("Regulation", regulation_rules),
        ("Risk", risk_rules),
        ("Requirement", all_rules),
        ("Standard", standard_rules),
        ("System", all_rules),
        ("Threat", threat_rules),
        ("Vendor", all_rules),
        ("Metric", all_rules),
        ("ProductGroup", all_rules),
        ("TechnologyEnvironment", all_rules),
        ("KeyReport", all_rules))
  @unpack
  def test_field(self, field, rules):
    """Test unmapping rules for {0}."""
    self.assertRules(field, *rules)


@ddt
class TestSnapshotMappingRules(BaseTestMappingRules):
  """Test case for snapshot mapping rules."""

  rules = ggrc.utils.rules.get_snapshot_mapping_rules()

  all_rules = []
  assessment_rules = ["AccessGroup", "Contract", "Control",
                      "DataAsset", "Facility", "Market", "Objective",
                      "OrgGroup", "Policy", "Process", "Product", "Project",
                      "Regulation", "Requirement", "Standard", "System",
                      "Vendor", "Risk", "Threat", "Metric", "ProductGroup",
                      "TechnologyEnvironment", 'KeyReport', 'AccountBalance']
  audit_rules = ["AccessGroup", "Contract", "Control",
                 "DataAsset", "Facility", "Market", "Objective",
                 "OrgGroup", "Policy", "Process", "Product", "Project",
                 "Regulation", "Requirement", "Standard", "System",
                 "Vendor", "Risk", "Threat", "Metric", "ProductGroup",
                 "TechnologyEnvironment", 'KeyReport', 'AccountBalance']
  issue_rules = ["AccessGroup", "Contract", "Control",
                 "DataAsset", "Facility", "Market", "Objective",
                 "OrgGroup", "Policy", "Process", "Product", "Project",
                 "Regulation", "Requirement", "Standard", "System",
                 "Vendor", "Risk", "Threat", "Metric", "ProductGroup",
                 "TechnologyEnvironment", 'KeyReport', 'AccountBalance']

  @data(("AccessGroup", all_rules),
        ("AccountBalance", all_rules),
        ("Assessment", assessment_rules),
        ("Audit", audit_rules),
        ("Contract", all_rules),
        ("Control", all_rules),
        ("CycleTaskGroupObjectTask", all_rules),
        ("DataAsset", all_rules),
        ("Facility", all_rules),
        ("Issue", issue_rules),
        ("Market", all_rules),
        ("Objective", all_rules),
        ("OrgGroup", all_rules),
        ("Person", all_rules),
        ("Policy", all_rules),
        ("Process", all_rules),
        ("Product", all_rules),
        ("Program", all_rules),
        ("Project", all_rules),
        ("Regulation", all_rules),
        ("Risk", all_rules),
        ("Requirement", all_rules),
        ("Standard", all_rules),
        ("System", all_rules),
        ("Threat", all_rules),
        ("Vendor", all_rules),
        ("Metric", all_rules),
        ("ProductGroup", all_rules),
        ("TechnologyEnvironment", all_rules),
        ("KeyReport", all_rules))
  @unpack
  def test_field(self, field, rules):
    """Test snapshot mapping rules for {0}."""
    self.assertRules(field, *rules)
