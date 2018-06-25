# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module for integration tests for CycleTaskGroupObjectTask specifics."""
import unittest

import ddt

from ggrc import db
from ggrc.models import all_models

from integration.ggrc import TestCase as BaseTestCase
from integration.ggrc import api_helper
from integration.ggrc import query_helper
from integration.ggrc.models import factories
from integration.ggrc_basic_permissions.models import factories as bp_factories
from integration.ggrc_workflows import generator as wf_generator
from integration.ggrc_workflows.helpers import rbac_helper
from integration.ggrc_workflows.helpers import workflow_test_case
from integration.ggrc_workflows.models import factories as wf_factories


@ddt.ddt
class TestCTGOT(BaseTestCase):
  """Test suite for CycleTaskGroupObjectTask specific logic."""

  NOBODY = "nobody@example.com"
  WORKFLOW_ADMIN = "wfa@example.com"
  TASK_ASSIGNEE_1 = "assignee_1@example.com"
  TASK_ASSIGNEE_2 = "assignee_2@example.com"
  TASK_SEC_ASSIGNEE = "sec_assignee@example.com"

  def setUp(self):
    super(TestCTGOT, self).setUp()

    self.api = api_helper.Api()

    with factories.single_commit():
      assignee_1 = factories.PersonFactory(email=self.TASK_ASSIGNEE_1)
      assignee_2 = factories.PersonFactory(email=self.TASK_ASSIGNEE_2)
      workflow_admin = factories.PersonFactory(email=self.WORKFLOW_ADMIN)
      nobody = factories.PersonFactory(email=self.NOBODY)

      reader_role = all_models.Role.query.filter_by(name="Reader").one()
      for person in [assignee_1, assignee_2, workflow_admin, nobody]:
        bp_factories.UserRoleFactory(person=person,
                                     role=reader_role,
                                     context=None)

      workflow = wf_factories.WorkflowFactory()
      taskgroup = wf_factories.TaskGroupFactory(workflow=workflow)
      task_1 = wf_factories.TaskGroupTaskFactory(task_group=taskgroup)
      task_2 = wf_factories.TaskGroupTaskFactory(task_group=taskgroup)
      task_role = all_models.AccessControlRole.query.filter(
          all_models.AccessControlRole.name == "Task Assignees",
          all_models.AccessControlRole.object_type == task_1.type,
      ).one()
      factories.AccessControlListFactory(ac_role=task_role,
                                         object=task_1,
                                         person=assignee_1)
      factories.AccessControlListFactory(ac_role=task_role,
                                         object=task_2,
                                         person=assignee_2)
      sec_assignee = factories.PersonFactory(email=self.TASK_SEC_ASSIGNEE)
      task_role = all_models.AccessControlRole.query.filter(
          all_models.AccessControlRole.name == "Task Secondary Assignees",
          all_models.AccessControlRole.object_type == task_1.type,
      ).one()
      factories.AccessControlListFactory(ac_role=task_role,
                                         object=task_1,
                                         person=sec_assignee)
      wf_admin_role = all_models.AccessControlRole.query.filter(
          all_models.AccessControlRole.name == "Admin",
          all_models.AccessControlRole.object_type == workflow.type,
      ).one()
      factories.AccessControlListFactory(ac_role=wf_admin_role,
                                         object=workflow,
                                         person=workflow_admin)

    generator = wf_generator.WorkflowsGenerator()
    self.cycle_id = generator.generate_cycle(workflow)[1].id
    generator.activate_workflow(workflow)

  @ddt.data((NOBODY, [False, False]),
            (WORKFLOW_ADMIN, [True, True]),
            (TASK_ASSIGNEE_1, [True, False]),
            (TASK_ASSIGNEE_2, [False, True]))
  @ddt.unpack
  def test_change_state_by_user(self, user, expected_values):
    """Test cycle task allow_change_state value by {0}."""
    all_models.Cycle.query.filter(
        all_models.Cycle.id == self.cycle_id
    ).update({
        all_models.Cycle.is_current: True,
    })
    db.session.commit()
    user = all_models.Person.query.filter_by(email=user).one()
    self.api.set_user(user)
    response = self.api.get_query(all_models.CycleTaskGroupObjectTask,
                                  "__sort=id")
    self.assert200(response)

    cycle_tasks = (response.json
                           .get("cycle_task_group_object_tasks_collection", {})
                           .get("cycle_task_group_object_tasks", []))
    # relies on same order of ids of TGT and CTGOT
    self.assertListEqual(
        [cycle_task["allow_change_state"] for cycle_task in cycle_tasks],
        expected_values,
    )

  @ddt.data(True, False)
  def test_change_state_by_is_current(self, cycle_is_current):
    """Test cycle task allow_change_state if Cycle is_current value is {0}."""
    all_models.Cycle.query.filter(
        all_models.Cycle.id == self.cycle_id
    ).update({
        all_models.Cycle.is_current: cycle_is_current,
    })
    db.session.commit()
    user_mail = self.WORKFLOW_ADMIN
    user = all_models.Person.query.filter_by(email=user_mail).one()
    self.api.set_user(user)
    response = self.api.get_query(all_models.CycleTaskGroupObjectTask,
                                  "__sort=id")
    self.assert200(response)

    cycle_tasks = (response.json
                           .get("cycle_task_group_object_tasks_collection", {})
                           .get("cycle_task_group_object_tasks", []))
    # relies on same order of ids of TGT and CTGOT
    states = [ct["allow_change_state"] for ct in cycle_tasks]
    if cycle_is_current:
      self.assertTrue(all(states))
    else:
      self.assertFalse(any(states))

  def test_context_after_task_delete(self):
    """Test UserRoles context keeping after cycle task deletion."""
    ctask = all_models.CycleTaskGroupObjectTask.query.first()
    ctask_context_id = ctask.context_id
    self.assertTrue(ctask_context_id)

    user = all_models.Person.query.filter_by(email=self.WORKFLOW_ADMIN).one()
    self.api.set_user(user)

    response = self.api.delete(ctask)
    self.assert200(response)

    for ctask in all_models.CycleTaskGroupObjectTask.query.all():
      self.assertEqual(ctask.context_id, ctask_context_id)

  def test_comment_cascade_deletion_on_cycle_task_delete(self):  # noqa pylint: disable=invalid-name
    """Test comment cascade deletion on CycleTask delete."""
    ctask = all_models.CycleTaskGroupObjectTask.query.first()
    ctask_id = ctask.id
    wf_factories.CycleTaskEntryFactory(
        cycle=ctask.cycle,
        cycle_task_group_object_task=ctask,
        description="Cycle task comment",
    )
    self.assertEqual(all_models.CycleTaskEntry.query.count(), 1)

    user = all_models.Person.query.filter_by(email=self.WORKFLOW_ADMIN).one()
    self.api.set_user(user)

    response = self.api.delete(
        all_models.CycleTaskGroupObjectTask.query.get(ctask_id))
    self.assert200(response)

    self.assertEqual(all_models.CycleTaskGroupObjectTask.query.filter_by(
        id=ctask_id).count(), 0)
    self.assertEqual(all_models.CycleTaskEntry.query.count(), 0)


class CycleTaskSecondaryAssigneeQuery(query_helper.WithQueryApi, TestCTGOT):
  """CycleTask's QueryAPI secondary assignee related tests."""

  def setUp(self):
    super(CycleTaskSecondaryAssigneeQuery, self).setUp()
    self.client.get("/login")

  def test_query_by_task_secondary_assignee_on_mytasks_page(self):  # noqa pylint: disable=invalid-name
    """Test QueryAPI request for CycleTasks on MyTasks page."""
    sec_assignee = all_models.Person.query.filter_by(
        email=self.TASK_SEC_ASSIGNEE).one()
    data = [
        {
            "object_name": "CycleTaskGroupObjectTask",
            "filters": {
                "expression": {
                    "left": {
                        "object_name": "Person",
                        "op": {
                            "name": "owned"
                        },
                        "ids": [
                            sec_assignee.id
                        ]
                    },
                    "op": {
                        "name": "AND"
                    },
                    "right": {
                        "left": "task secondary assignees",
                        "op": {
                            "name": "~"
                        },
                        "right": self.TASK_SEC_ASSIGNEE
                    }
                },
                "keys": [
                    "task secondary assignees"
                ],
                "order_by": {
                    "keys": [],
                    "order": "",
                    "compare": None
                }
            },
            "limit": [0, 10]
        }
    ]
    result = self._get_first_result_set(data, "CycleTaskGroupObjectTask",
                                        "total")
    self.assertEqual(result, 1)

  @unittest.skip("Skip cause feature cut.")
  def test_query_by_task_secondary_assignee_on_active_cycles_tab(self):  # noqa pylint: disable=invalid-name
    """Test QueryAPI request for CycleTasks on Active Cycles tab."""
    data = [
        {
            "object_name": "Cycle",
            "filters": {
                "expression": {
                    "left": {
                        "object_name": "Workflow",
                        "op": {
                            "name": "relevant"
                        },
                        "ids": [all_models.Workflow.query.one().id],
                    },
                    "op": {
                        "name": "AND"
                    },
                    "right": {
                        "left": {
                            "left": "is_current",
                            "op": {
                                "name": "="
                            },
                            "right": "1"
                        },
                        "op": {
                            "name": "AND"
                        },
                        "right": {
                            "left": "task secondary assignees",
                            "op": {
                                "name": "~"
                            },
                            "right": self.TASK_SEC_ASSIGNEE
                        }
                    }
                },
                "keys": [
                    "is_current",
                    "task secondary assignees"
                ],
                "order_by": {
                    "keys": [],
                    "order": "",
                    "compare": None
                }
            },
            "limit": [0, 10]
        }
    ]
    result = self._get_first_result_set(data, "Cycle", "total")
    self.assertEqual(result, 1)


@ddt.ddt
class CycleTaskObjectApprovalQuery(query_helper.WithQueryApi,
                                   workflow_test_case.WorkflowTestCase):
  """CycleTask's QueryAPI for object_approval attribute."""

  def setUp(self):
    super(CycleTaskObjectApprovalQuery, self).setUp()
    self.client.get("/login")

  @staticmethod
  def _generate_workflows(approved, obj_num):
    """Generate workflows with appropriate data for tests"""
    generator = wf_generator.WorkflowsGenerator()
    with factories.single_commit():
      workflows = [wf_factories.WorkflowFactory(object_approval=approved[i])
                   for i in range(obj_num)]
      taskgroups = [wf_factories.TaskGroupFactory(workflow=workflows[i])
                    for i in range(obj_num)]
      # flake8: noqa pylint: disable=unused-variable
      tasks = [wf_factories.TaskGroupTaskFactory(task_group=taskgroups[i])
               for i in range(obj_num)]

    cycles = [generator.generate_cycle(workflows[i])[1].id
              for i in range(obj_num)]
    for workflow in workflows:
      generator.activate_workflow(workflow)

    return cycles

  @ddt.data(
      [False, False, False],
      [False, False, True],
      [False, True, True],
      [True, True, True],
  )
  def test_query_object_approval(self, approved):
    """Test QueryAPI request for object approval"""
    obj_num = len(approved)
    cycles_ids = self._generate_workflows(approved, obj_num)
    approved_ids = self.simple_query(
        "CycleTaskGroupObjectTask",
        expression=["object approval", "=", "true"],
        type_="ids",
        field="ids"
    )
    not_approved_ids = self.simple_query(
        "CycleTaskGroupObjectTask",
        expression=["object approval", "=", "false"],
        type_="ids",
        field="ids"
    )

    cycle_tasks = all_models.CycleTaskGroupObjectTask.query.all()
    expected_approved = [task.id for task in cycle_tasks if
                         approved[cycles_ids.index(task.cycle_id)]]
    expected_not_approved = [task.id for task in cycle_tasks if not
                             approved[cycles_ids.index(task.cycle_id)]]
    self.assertEqual(approved_ids, expected_approved)
    self.assertEqual(not_approved_ids, expected_not_approved)


@ddt.ddt
class TestCycleTaskApiCalls(workflow_test_case.WorkflowTestCase):
  """Tests related to CycleTask REST API calls."""

  def test_get_ct_g_reader_no_role(self):
    """GET CycleTask collection logged in as GlobalReader & No Role."""
    with factories.single_commit():
      wf_factories.CycleTaskFactory()
      self.setup_helper.setup_person(rbac_helper.GR_RNAME, "No Role")

    g_reader = self.setup_helper.get_person(rbac_helper.GR_RNAME, "No Role")
    self.api_helper.set_user(g_reader)

    cycle_task = all_models.CycleTaskGroupObjectTask.query.one()
    response = self.api_helper.get_collection(cycle_task, (cycle_task.id, ))
    self.assertTrue(
        response.json["cycle_task_group_object_tasks_collection"][
            "cycle_task_group_object_tasks"
        ]
    )

  @ddt.data(True, False)
  def test_filter_by_object_approval(self, filter_flag):
    """Test filter CTGOT by object_approval flag if value is {0}."""
    with factories.single_commit():
      ctgts = {}
      for flag in [True, False]:
        workflow = wf_factories.WorkflowFactory(object_approval=flag)
        task_group = wf_factories.TaskGroupFactory(workflow=workflow)
        tgt = wf_factories.TaskGroupTaskFactory(task_group=task_group)
        cycle = wf_factories.CycleFactory(workflow=workflow)
        ctgts[flag] = wf_factories.CycleTaskFactory(cycle=cycle,
                                                    task_group_task=tgt)

    filter_params = "ids={}&object_approval={}".format(
        ",".join([str(c.id) for c in ctgts.values()]),
        "true" if filter_flag else "false"
    )
    response = self.api_helper.get_query(all_models.CycleTaskGroupObjectTask,
                                         filter_params)
    self.assert200(response)
    colections = response.json["cycle_task_group_object_tasks_collection"]
    items = colections["cycle_task_group_object_tasks"]
    self.assertEqual(1, len(items))
    self.assertEqual(ctgts[filter_flag].id, items[0]["id"])
