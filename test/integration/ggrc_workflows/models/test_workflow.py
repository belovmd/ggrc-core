# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for Workflow model."""

import datetime
import ddt
import freezegun

from ggrc import db
from ggrc.models import all_models
from ggrc_workflows.models import Workflow
from integration.ggrc import TestCase
from integration.ggrc.models import factories as glob_factories
from integration.ggrc_workflows.models import factories
from integration.ggrc import api_helper
from integration.ggrc_workflows import generator as wf_generator
from integration.ggrc_workflows.helpers import rbac_helper
from integration.ggrc_workflows.helpers import workflow_test_case


@ddt.ddt
class TestWorkflow(TestCase):
  """Tests for Workflow model inner logic"""

  def setUp(self):
    super(TestWorkflow, self).setUp()

    self.api = api_helper.Api()
    self.generator = wf_generator.WorkflowsGenerator()

  def test_basic_workflow_creation(self):
    """Test basic WF creation."""
    workflow = factories.WorkflowFactory(title="This is a test WF")
    workflow = db.session.query(Workflow).get(workflow.id)
    self.assertEqual(workflow.title, "This is a test WF")

  @ddt.data(
      # (today, start_date, update_date, expected_date)
      (
          "2017-08-10",
          datetime.date(2017, 8, 10),
          datetime.date(2017, 8, 9),
          datetime.date(2017, 8, 16)
      ),
      (
          "2017-08-10",
          datetime.date(2017, 8, 10),
          datetime.date(2017, 8, 11),
          datetime.date(2017, 8, 11)
      ),
      (
          "2017-08-10",
          datetime.date(2017, 8, 10),
          datetime.date(2017, 8, 10),
          datetime.date(2017, 8, 17)
      ),
  )
  @ddt.unpack
  def test_recalculate_start_date(self,
                                  today,
                                  start_date,
                                  update_date,
                                  expected_date):
    """Test recalculate start_date update={2} expected={3}."""
    with freezegun.freeze_time(today):
      with glob_factories.single_commit():
        workflow = factories.WorkflowFactory(
            title="This is a test WF",
            unit=all_models.Workflow.WEEK_UNIT,
            repeat_every=1)
        task_group = factories.TaskGroupFactory(workflow=workflow)
        task = factories.TaskGroupTaskFactory(
            task_group=task_group,
            start_date=start_date,
            end_date=start_date + datetime.timedelta(1))
      wf_id = workflow.id
      task_id = task.id
      self.generator.activate_workflow(workflow)
      task = all_models.TaskGroupTask.query.get(task_id)
      self.api.put(task, {"start_date": update_date})
    workflow = all_models.Workflow.query.get(wf_id)
    self.assertEqual(expected_date, workflow.next_cycle_start_date)

  @ddt.data(
      # (delete_task_idx, expected_date)
      ([0], datetime.date(2017, 8, 11)),
      ([1], datetime.date(2017, 8, 17)),
      ([0, 1], None),
  )
  @ddt.unpack  # pylint: disable=invalid-name
  def test_recalculate_start_date_on_delete(self, idxs, expected_date):
    """Test recalculate start_date on delete expected={1}."""
    start_date_1 = datetime.date(2017, 8, 10)
    start_date_2 = datetime.date(2017, 8, 11)
    with freezegun.freeze_time("2017-08-10"):
      with glob_factories.single_commit():
        workflow = factories.WorkflowFactory(
            title="This is a test WF",
            unit=all_models.Workflow.WEEK_UNIT,
            repeat_every=1)
        tasks = (
            factories.TaskGroupTaskFactory(
                task_group=factories.TaskGroupFactory(workflow=workflow),
                start_date=start_date_1,
                end_date=start_date_1 + datetime.timedelta(1),
            ),
            factories.TaskGroupTaskFactory(
                task_group=factories.TaskGroupFactory(workflow=workflow),
                start_date=start_date_2,
                end_date=start_date_2 + datetime.timedelta(1),
            ),
        )
      wf_id = workflow.id
      task_ids = [t.id for t in tasks]
      self.generator.activate_workflow(workflow)
      workflow = all_models.Workflow.query.get(wf_id)
      self.assertEqual(datetime.date(2017, 8, 17),
                       workflow.next_cycle_start_date)
      for idx in idxs:
        task = all_models.TaskGroupTask.query.get(task_ids[idx])
        self.api.delete(task)
    workflow = all_models.Workflow.query.get(wf_id)
    self.assertEqual(expected_date, workflow.next_cycle_start_date)

  @ddt.data(
      # NOTE: today is datetime.date(2017, 8, 10)
      # (new_start_date, expected_date)
      (datetime.date(2017, 8, 10), datetime.date(2017, 8, 17)),
      (datetime.date(2017, 8, 3), datetime.date(2017, 8, 17)),
      (datetime.date(2017, 8, 17), datetime.date(2017, 8, 17)),
      (datetime.date(2017, 8, 9), datetime.date(2017, 8, 16)),
      (datetime.date(2017, 8, 8), datetime.date(2017, 8, 15)),
      (datetime.date(2017, 8, 7), datetime.date(2017, 8, 14)),
      (datetime.date(2017, 8, 6), datetime.date(2017, 8, 11)),
      (datetime.date(2017, 8, 5), datetime.date(2017, 8, 11)),
  )
  @ddt.unpack  # pylint: disable=invalid-name
  def test_recalculate_start_date_on_create(self,
                                            new_start_date,
                                            expected_date):
    """Test recalculate start_date on create update={} expected={}."""
    with freezegun.freeze_time("2017-08-10"):
      with glob_factories.single_commit():
        workflow = factories.WorkflowFactory(
            title="This is a test WF",
            unit=all_models.Workflow.WEEK_UNIT,
            repeat_every=1)
        task = factories.TaskGroupTaskFactory(
            task_group=factories.TaskGroupFactory(
                workflow=workflow,
                context=glob_factories.ContextFactory(),
            ),
            start_date=datetime.date(2017, 8, 10),
            end_date=datetime.date(2017, 8, 11),
        )
      wf_id = workflow.id
      task_id = task.id
      self.generator.activate_workflow(workflow)
      workflow = all_models.Workflow.query.get(wf_id)
      task = all_models.TaskGroupTask.query.get(task_id)
      self.assertEqual(datetime.date(2017, 8, 17),
                       workflow.next_cycle_start_date)
      self.generator.generate_task_group_task(
          task.task_group,
          {
              'start_date': new_start_date,
              'end_date': new_start_date + datetime.timedelta(1),
          })
    workflow = all_models.Workflow.query.get(wf_id)
    self.assertEqual(expected_date, workflow.next_cycle_start_date)

  @ddt.data(
      (
          # One cycle should be created
          datetime.date(2017, 8, 10),
          datetime.date(2017, 8, 14),
          all_models.Workflow.ACTIVE
      ),
      (
          # No cycles should be created
          datetime.date(2017, 8, 11),
          datetime.date(2017, 8, 14),
          all_models.Workflow.INACTIVE
      ),
  )
  @ddt.unpack
  def test_archive_workflow(self, tgt_start_date, tgt_end_date, wf_status):
    """Test archive workflow with status={2}"""
    with freezegun.freeze_time("2017-08-10"):
      with glob_factories.single_commit():
        workflow = factories.WorkflowFactory(
            title="This is a test WF",
            unit=all_models.Workflow.WEEK_UNIT,
            repeat_every=1)
        factories.TaskGroupTaskFactory(
            task_group=factories.TaskGroupFactory(
                workflow=workflow,
                context=glob_factories.ContextFactory(),
            ),
            start_date=tgt_start_date,
            end_date=tgt_end_date,
        )
      wf_id = workflow.id
      self.generator.activate_workflow(workflow)
      workflow = all_models.Workflow.query.get(wf_id)
      self.assertEqual(all_models.Workflow.ACTIVE, workflow.status)
      self.assertIs(workflow.recurrences, True)
      # Archive workflow
      self.generator.modify_workflow(workflow, {'recurrences': False})
      workflow = all_models.Workflow.query.get(wf_id)
      self.assertIs(workflow.recurrences, False)
      self.assertEqual(wf_status, workflow.status)

  def test_ending_archived_workflow_cycles(self):  # noqa pylint: disable=invalid-name
    """Archived workflow should be INACTIVE if current cycles are ended."""
    with freezegun.freeze_time("2017-08-10"):
      with glob_factories.single_commit():
        workflow = factories.WorkflowFactory(
            title="This is a test WF",
            unit=all_models.Workflow.WEEK_UNIT,
            repeat_every=1)
        factories.TaskGroupTaskFactory(
            task_group=factories.TaskGroupFactory(
                workflow=workflow,
                context=glob_factories.ContextFactory(),
            ),
            # Two cycles should be created
            start_date=datetime.date(2017, 8, 3),
            end_date=datetime.date(2017, 8, 7),
        )
      wf_id = workflow.id
      self.generator.activate_workflow(workflow)
      workflow = all_models.Workflow.query.get(wf_id)
      self.assertEqual(all_models.Workflow.ACTIVE, workflow.status)
      self.assertIs(workflow.recurrences, True)
      self.assertEqual(2, len(workflow.cycles))
      # Archive workflow
      self.generator.modify_workflow(workflow, {'recurrences': False})
      workflow = all_models.Workflow.query.get(wf_id)
      self.assertIs(workflow.recurrences, False)
      self.assertEqual(all_models.Workflow.ACTIVE, workflow.status)
      # End all current cycles
      for cycle in workflow.cycles:
        self.generator.modify_object(cycle, {'is_current': False})
      # Archived workflow should be inactive
      workflow = all_models.Workflow.query.get(wf_id)
      self.assertEqual(all_models.Workflow.INACTIVE, workflow.status)

  @ddt.data(
      ('One time workflow', None, None),
      ('Daily workflow', all_models.Workflow.DAY_UNIT, 1),
      ('Weekly workflow', all_models.Workflow.WEEK_UNIT, 1),
      ('Monthly workflow', all_models.Workflow.MONTH_UNIT, 1),
  )
  @ddt.unpack  # pylint: disable=invalid-name
  def test_change_verification_flag_positive(self, title, unit, repeat_every):
    """Test change verification_flag positive title={}."""
    with freezegun.freeze_time("2017-08-10"):
      with glob_factories.single_commit():
        workflow = factories.WorkflowFactory(title=title, unit=unit,
                                             repeat_every=repeat_every)
        factories.TaskGroupTaskFactory(
            task_group=factories.TaskGroupFactory(
                workflow=workflow,
                context=glob_factories.ContextFactory()
            ),
            start_date=datetime.date(2017, 8, 3),
            end_date=datetime.date(2017, 8, 7))
      wf_id = workflow.id
      workflow = all_models.Workflow.query.get(wf_id)
      verif_default = all_models.Workflow.IS_VERIFICATION_NEEDED_DEFAULT
      self.assertIs(workflow.is_verification_needed, verif_default)
      self.generator.modify_object(
          workflow,
          {
              'is_verification_needed': not verif_default
          })
      workflow = all_models.Workflow.query.get(wf_id)
      self.assertIs(workflow.is_verification_needed, not verif_default)

  @ddt.data(
      ('One time workflow', None, None),
      ('Daily workflow', all_models.Workflow.DAY_UNIT, 1),
      ('Weekly workflow', all_models.Workflow.WEEK_UNIT, 1),
      ('Monthly workflow', all_models.Workflow.MONTH_UNIT, 1),
  )
  @ddt.unpack  # pylint: disable=invalid-name
  def test_change_verification_flag_negative(self, title, unit, repeat_every):
    """Test change verification_flag negative title={}."""
    with freezegun.freeze_time("2017-08-10"):
      with glob_factories.single_commit():
        workflow = factories.WorkflowFactory(title=title, unit=unit,
                                             repeat_every=repeat_every)
        factories.TaskGroupTaskFactory(
            task_group=factories.TaskGroupFactory(
                workflow=workflow,
                context=glob_factories.ContextFactory()
            ),
            start_date=datetime.date(2017, 8, 3),
            end_date=datetime.date(2017, 8, 7))
      wf_id = workflow.id
      self.generator.activate_workflow(workflow)
      workflow = all_models.Workflow.query.get(wf_id)
      verif_default = all_models.Workflow.IS_VERIFICATION_NEEDED_DEFAULT
      self.assertIs(workflow.is_verification_needed, verif_default)
      resp = self.api.put(
          workflow,
          {
              'is_verification_needed': not verif_default
          })
      self.assert400(resp)
      workflow = all_models.Workflow.query.get(wf_id)
      self.assertIs(workflow.is_verification_needed, verif_default)

  @ddt.data(
      ("off", None, None),
      ("off", None, 42),
      ("every weekday", all_models.Workflow.DAY_UNIT, None),
      ("every weekday", all_models.Workflow.DAY_UNIT, 1),
      ("every 30 weekdays", all_models.Workflow.DAY_UNIT, 30),
      ("every week", all_models.Workflow.WEEK_UNIT, None),
      ("every week", all_models.Workflow.WEEK_UNIT, 1),
      ("every 30 weeks", all_models.Workflow.WEEK_UNIT, 30),
      ("every month", all_models.Workflow.MONTH_UNIT, None),
      ("every month", all_models.Workflow.MONTH_UNIT, 1),
      ("every 30 months", all_models.Workflow.MONTH_UNIT, 30)
  )
  @ddt.unpack
  def test_filtering_by_repeat(self, title, unit, repeat_every):
    """Test filtering by repeat field. title={0}"""
    with glob_factories.single_commit():
      workflow = factories.WorkflowFactory(title=title,
                                           unit=unit,
                                           repeat_every=repeat_every)

    for operator, expected_count in zip(["~", "!~", "=", "!="], [1, 0, 1, 0]):
      response = self.api.send_request(self.api.client.post, workflow, data=[{
          "object_name": "Workflow",
          "filters": {
              "expression": {
                  "left": "repeat",
                  "op": {"name": operator},
                  "right": title
              }
          }
      }], api_link='/query')
      self.assert200(response)
      count = response.json[0]["Workflow"]["count"]
      self.assertEqual(count, expected_count)

  def test_ordering_by_repeat(self):
    """Test ordering by repeat field."""
    workflows_data = [("Off", None, None),
                      ("Off 1", None, 1),
                      ("Every weekday", all_models.Workflow.DAY_UNIT, 1),
                      ("Every 2 weekdays", all_models.Workflow.DAY_UNIT, 2),
                      ("Every 30 weekdays", all_models.Workflow.DAY_UNIT, 30),
                      ("Every week", all_models.Workflow.WEEK_UNIT, 1),
                      ("Every 2 weeks", all_models.Workflow.WEEK_UNIT, 2),
                      ("Every 30 weeks", all_models.Workflow.WEEK_UNIT, 30),
                      ("Every month", all_models.Workflow.MONTH_UNIT, 1),
                      ("Every 2 months", all_models.Workflow.MONTH_UNIT, 2),
                      ("Every 30 months", all_models.Workflow.MONTH_UNIT, 30)]
    for title, unit, repeat_every in workflows_data:
      factories.WorkflowFactory(title=title, unit=unit,
                                repeat_every=repeat_every)

    response = self.api.send_request(self.api.client.post, None, data=[{
        "object_name": "Workflow",
        "filters": {
            "expression": {},
        },
        "order_by": [{
            "name": "repeat",
            "desc": True
        }]
    }], api_link='/query')
    self.assert200(response)
    values = response.json[0]["Workflow"]["values"]
    observed_result = [item["title"] for item in values]
    expected_result = [title for title, _, _ in workflows_data[::-1]]
    self.assertEqual(observed_result, expected_result)


@ddt.ddt
class TestWorkflowApiCalls(workflow_test_case.WorkflowTestCase):
  """Tests related to Workflow REST API calls."""

  def test_get_wf_g_reader_no_role(self):
    """GET Workflow collection logged in as GlobalReader & No Role."""
    with glob_factories.single_commit():
      factories.WorkflowFactory()
      self.setup_helper.setup_person(rbac_helper.GR_RNAME, "No Role")

    g_reader = self.setup_helper.get_person(rbac_helper.GR_RNAME, "No Role")
    self.api_helper.set_user(g_reader)

    workflow = all_models.Workflow.query.one()
    response = self.api_helper.get_collection(workflow, (workflow.id, ))
    self.assertTrue(response.json["workflows_collection"]["workflows"])

  @ddt.data(True, False)
  def test_obj_approval_not_updatable(self, flag):
    """Tests object_approval property is not updatable via REST API"""
    attr_name = "object_approval"
    wf_obj = factories.WorkflowFactory(object_approval=flag)
    wf_id = wf_obj.id
    wf_obj_approval = flag

    response = self.api_helper.get(Workflow, wf_id)
    self.assert200(response)
    obj_approval = response.json.get("workflow", {}).get(attr_name)
    self.assertEqual(wf_obj_approval, obj_approval)

    response = self.api_helper.put(wf_obj, {attr_name: not flag})
    self.assert200(response)
    db_obj_approval = Workflow.query.filter_by(id=wf_id).one().object_approval
    self.assertEqual(wf_obj_approval, db_obj_approval)

    response = self.api_helper.get(Workflow, wf_id)
    self.assert200(response)
    new_obj_approval = response.json.get("workflow", {}).get(attr_name)
    self.assertEqual(wf_obj_approval, new_obj_approval)
