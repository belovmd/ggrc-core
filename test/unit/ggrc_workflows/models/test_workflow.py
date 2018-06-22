# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Unit Tests for Workflow model and WorkflowState mixin
"""

import unittest
from datetime import date

import ddt
from freezegun import freeze_time

import ggrc.builder.json
from ggrc_workflows.models import cycle_task_group_object_task as cycle_task
from ggrc_workflows.models import cycle
from ggrc_workflows.models import workflow

from integration.ggrc_workflows.models import factories as wf_factories


@ddt.ddt
class TestWorkflowState(unittest.TestCase):

  @ddt.data(
      (["Assigned", "Assigned", "Assigned"], "Assigned"),
      ([None, None, None], "Assigned"),
      (["In Progress", "Assigned", "Assigned"], "In Progress"),
      (["Finished", "Assigned", "Assigned"], "In Progress"),
      (["Verified", "Assigned", "Assigned"], "In Progress"),
      (["In Progress", "In Progress", "In Progress"], "In Progress"),
      (["Finished", "In Progress", "Assigned"], "In Progress"),
      (["Finished", "Declined", "Assigned"], "In Progress"),
      (["Finished", "Finished", "Finished"], "Finished"),
      (["Verified", "Finished", "Finished"], "Finished"),
      (["Verified", "Verified", "Verified"], "Verified"),
      (["Declined", "Declined", "Declined"], "In Progress"),
      ([], None),
  )
  @ddt.unpack
  def test_get_state(self, task_states, result):
    """Test get state for {0}."""
    # pylint: disable=protected-access
    self.assertEqual(
        result,
        workflow.WorkflowState._get_state([
            cycle_task.CycleTaskGroupObjectTask(status=s) for s in task_states
        ])
    )

  def test_get_object_state(self):

    tasks_on_object = [
        cycle_task.CycleTaskGroupObjectTask(
            end_date=date(2015, 2, 1),
            cycle=cycle.Cycle(is_current=True)
        ),
        cycle_task.CycleTaskGroupObjectTask(
            end_date=date(2015, 1, 10),
            cycle=cycle.Cycle(is_current=True)
        ),
    ]
    with freeze_time("2015-02-01 13:39:20"):
      self.assertEqual(
          "Overdue", workflow.WorkflowState.get_object_state(tasks_on_object)
      )

  @ddt.data(
      # (expected, setup_date, repeat_every, unit),
      (date(2017, 3, 31), date(2017, 2, 28), 1, workflow.Workflow.MONTH_UNIT),
      (date(2017, 2, 28), date(2017, 1, 31), 1, workflow.Workflow.MONTH_UNIT),
      (date(2017, 4, 28), date(2017, 1, 31), 3, workflow.Workflow.MONTH_UNIT),
      (date(2017, 2, 28), date(2016, 2, 29), 12, workflow.Workflow.MONTH_UNIT),
      (date(2017, 3, 17), date(2017, 3, 10), 1, workflow.Workflow.WEEK_UNIT),
      # -------------------
      # custom day unit logic
      (date(2017, 8, 11), date(2017, 8, 10), 1, workflow.Workflow.DAY_UNIT),
      (date(2017, 8, 14), date(2017, 8, 10), 2, workflow.Workflow.DAY_UNIT),
      (date(2017, 8, 15), date(2017, 8, 10), 3, workflow.Workflow.DAY_UNIT),
      (date(2017, 8, 16), date(2017, 8, 10), 4, workflow.Workflow.DAY_UNIT),
      (date(2017, 8, 17), date(2017, 8, 10), 5, workflow.Workflow.DAY_UNIT),
      (date(2017, 8, 18), date(2017, 8, 10), 6, workflow.Workflow.DAY_UNIT),
      (date(2017, 8, 21), date(2017, 8, 10), 7, workflow.Workflow.DAY_UNIT),
      (date(2017, 8, 14), date(2017, 8, 11), 1, workflow.Workflow.DAY_UNIT),
      (date(2017, 8, 25), date(2017, 8, 11), 10, workflow.Workflow.DAY_UNIT),
      # -------------------
      # holidays don't matter
      (date(2017, 1, 2), date(2016, 12, 30), 1, workflow.Workflow.DAY_UNIT),
      (date(2017, 1, 3), date(2016, 12, 30), 2, workflow.Workflow.DAY_UNIT),
      (date(2017, 1, 4), date(2016, 12, 30), 3, workflow.Workflow.DAY_UNIT),
      # ------------------
  )
  @ddt.unpack
  def test_calc_repeated_dates(self, expected, setup_date, repeat_every, unit):
    """Test calculate repeated dates for repeat every {2} {3}."""
    self.assertEqual(
        expected,
        workflow.Workflow(
            repeat_every=repeat_every,
            unit=unit,
            repeat_multiplier=1
        ).calc_next_adjusted_date(
            setup_date
        )
    )

  @ddt.data(
      # (expected, setup_date),
      (date(2016, 12, 30), date(2016, 12, 31)),
      (date(2016, 12, 30), date(2017, 1, 2)),
      (date(2017, 8, 4), date(2017, 8, 5)),
      (date(2017, 8, 4), date(2017, 8, 6)),
      (date(2017, 8, 7), date(2017, 8, 7)),
  )
  @ddt.unpack
  def test_calc_one_time_dates(self, expected, setup_date):
    """Calculate one time dates for {1}."""
    self.assertEqual(
        expected,
        workflow.Workflow().calc_next_adjusted_date(setup_date)
    )

  @ddt.data(True, False)
  def test_obj_approval_not_updatable(self, flag):
    """Tests object_approval property is not updatable"""
    wf_obj = wf_factories.WorkflowFactory(object_approval=flag)
    builder = ggrc.builder.json.get_json_builder(wf_obj)
    # pylint: disable=protected-access
    self.assertNotIn("object_approval", builder._update_attrs)
