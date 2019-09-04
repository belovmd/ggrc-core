# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module provide sync job for IssuetrackerIssue object attributes"""

from collections import defaultdict
import logging
import sqlalchemy as sa

from ggrc import db
from ggrc.integrations.synchronization_jobs import sync_utils
from ggrc.models import all_models


logger = logging.getLogger(__name__)


def _collect_issues_from_db():
  """
      Preparing info about IssuetrackerIssue objects those need to be
      synced up.
  Returns:
      Dict() key: issue_id, value: {component_id: int,
                                    hotlist_id: int}
  """
  issuetracker_issue = all_models.IssuetrackerIssue
  date_from = "2019-05-20"
  query = issuetracker_issue.query.filter(
      issuetracker_issue.updated_at > date_from,
      issuetracker_issue.issue_id.isnot(None),
  )
  objects_info = {}
  for obj in query:
    objects_info[int(obj.issue_id)] = {"component_id": int(obj.component_id),
                                       "hotlist_id": int(obj.hotlist_id)}
  return objects_info


def _compare_values_for_issues():
  """
      Compare local and external values for IssuetrackerIssue objects
  Returns:
      Dict() key: issue_id, value: {component_id: int,
                                    hotlist_id: int}
  """
  issues_to_update = defaultdict(dict)
  local_issues = _collect_issues_from_db()
  external_issues = sync_utils.iter_issue_batches(local_issues.keys(),
                                                  batch_size=100)

  logger.info("Collecting issues those need to be updated")
  for info in external_issues:
    for issue_id in info:
      local_component = local_issues[issue_id].get("component_id")
      local_hotlist = local_issues[issue_id].get("hotlist_id")

      if local_component != info[issue_id]["component_id"]:
        issues_to_update[issue_id]["component_id"] = \
            info[issue_id]["component_id"]

      if local_hotlist not in info[issue_id]["hotlist_ids"]:
        issues_to_update[issue_id]["hotlist_id"] = \
            info[issue_id]["hotlist_ids"][0]

  return issues_to_update


# pylint: disable=inconsistent-return-statements
def _add_obj_without_revision(obj_id, obj_type, action="updated"):
  """
      Adding updated objects to service table
  Args:
    obj_id: Int
    obj_type: Str
    action: Str
  Returns:
      None
  """
  from ggrc.utils.user_generator import get_migrator_id
  migrator = get_migrator_id()
  obj_without_revision_table = sa.sql.table(
      "objects_without_revisions",
      sa.sql.column("obj_id", sa.Integer),
      sa.sql.column("obj_type", sa.String),
      sa.sql.column("action", sa.String),
      sa.sql.column("modified_by_id", sa.Integer)
  )
  ins = obj_without_revision_table.insert().values(obj_id=obj_id,
                                                   obj_type=obj_type,
                                                   action=action,
                                                   modified_by_id=migrator)
  db.session.execute(ins)


# pylint: disable=logging-not-lazy
def update_synced_issues():
  """
      Updating IssuetrackerIssue objects
      Create revisions if needed
  Returns:
      Dict() key: str Object/Object.id, value: str Updated values
  """
  issues_to_upd = _compare_values_for_issues()
  if issues_to_upd:
    issuetracker_issues = all_models.IssuetrackerIssue.query.filter(
        all_models.IssuetrackerIssue.issue_id.in_(issues_to_upd.keys())
    )
    for issue in issuetracker_issues:
      data = issues_to_upd[int(issue.issue_id)]
      for key, val in data.items():
        setattr(issue, key, val)
      db.session.add(issue)
      logger.info(
          "%s(id: %s) was updated with new values: %s" % (
              issue.object_type,
              issue.object_id,
              ", ".join("'%s': '%s'" % (k, v) for k, v in data.items())
          )
      )
      _add_obj_without_revision(issue.id, "IssuetrackerIssue")
    db.session.commit()
  else:
    logger.warning("All IssuetrackerIssues are up to date")
