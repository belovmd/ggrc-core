# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Assessment integration functionality via cron job."""

import logging
import datetime

from ggrc.models.hooks.issue_tracker import assessment_integration
from ggrc.integrations import integrations_errors, constants
from ggrc.integrations.synchronization_jobs import sync_utils

logger = logging.getLogger(__name__)


# A list of field to watch for changes in.
FIELDS_TO_CHECK = ('status', 'type', 'priority', 'severity')

# Status values maps from GGRC to IssueTracker.
ASSESSMENT_STATUSES_MAPPING = {
    'Not Started': 'ASSIGNED',
    'In Progress': 'ASSIGNED',
    'In Review': 'FIXED',
    'Rework Needed': 'ASSIGNED',
    'Completed': 'VERIFIED',
    'Deprecated': 'OBSOLETE',
}


def _get_status(assessment_state):
  """Get assessment's status"""
  status_value = ASSESSMENT_STATUSES_MAPPING[
      assessment_state["status"]
  ]
  return status_value


def _get_due_date(assessment_state):
  """Get assessment's due_date"""
  due_date = assessment_state["due_date"]
  if due_date is not None:
    return {
        "name": constants.CustomFields.DUE_DATE,
        "value": due_date.strftime("%Y-%m-%d"),
        "type": "DATE",
        "display_string": constants.CustomFields.DUE_DATE,
    }
  return None


def _get_issue_info_by_issue_id(issue_id, assessment_issues):
  """Get Issue information by issue id.

  Args:
    - issue_id: id of Issue object
    - assessment_issues: Dictionary with Issue information

  Returns:
      - issue_id: id of Issue object convert to string.
      - issue_info: information by current issue_id
  """
  issue_id = str(issue_id)
  issue_info = assessment_issues.get(issue_id)

  return issue_id, issue_info


def _prepare_issue_payload(issue_info):
  """Prepare issue payload,

  Args:
    - issue_info: Dictionary with Issue Information.

  Returns:
    - issue_payload: Dictionary with information
    for Issue payload.
  """
  assessment_state = issue_info["state"]

  issue_payload = {
      field: assessment_state[field]
      for field in FIELDS_TO_CHECK if field in assessment_state
  }
  issue_payload.update({
      "status": _get_status(assessment_state),
      "component_id": int(issue_info["component_id"])
      if issue_info.get("component_id") else None,
      "ccs": assessment_state.get("ccs", [])
  })

  due_date = _get_due_date(assessment_state)
  if due_date is not None:
    issue_payload["custom_fields"] = [due_date]
  else:
    issue_payload["custom_fields"] = []

  return issue_payload


def _extract_date(date_in_string):
  """Extract date from string."""
  try:
    current_date = datetime.datetime.strptime(
        date_in_string,
        "%Y-%m-%d"
    )
  except ValueError:
    current_date = None

  return current_date


def _compare_custom_fields(custom_fields_payload, custom_fields_issuetracker):
  """Validate custom fields on payload and from third party server.

  Args:
    - custom_fields_payload: custom_fields on Issue Tracker Payload
    - custom_fields_issuetracker: custom_fields from Issue Tracker

  Returns:
    tuple with bool objects (due_dates_equals, remove_custom_fields)

    due_dates_equals: bool object with validate or not indicator (True/False)

    remove_custom_fields: bool object that indicate to remove "custom_fields"
    from payload
  """
  if any(custom_fields_payload):
    due_date_payload = _extract_date(
        custom_fields_payload[0]["value"].strip()
    )
  else:
    due_date_payload = None

  if any(custom_fields_issuetracker):
    due_date_raw = sync_utils.parse_due_date(
        custom_fields_issuetracker
    )
    if due_date_raw is None:
      # due date is empty after processing,
      # in that case we shouldn't synchronize custom fields
      return True, True
    else:
      due_date_issuetracker = _extract_date(due_date_raw)
  else:
    # custom fields is empty from issue tracker,
    # in that case we shouldn't synchronize custom fields
    return True, True

  return due_date_payload == due_date_issuetracker, False


def _compare_ccs(ccs_payload, ccs_issuetracker):
  """Validate CCs on payload and from third party server.

  Args:
    - ccs_payload: CCs on Issue Tracker Payload
    - ccs_issuetracker: CCs from Issue Tracker

  Returns:
    bool object with validate or not indicator (True/False)
  """
  ccs_payload = set(cc.strip() for cc in ccs_payload)
  ccs_issuetracker = set(cc.strip() for cc in ccs_issuetracker)

  return ccs_payload.issubset(ccs_issuetracker)


def _group_ccs_with_issuetracker(ccs_payload, ccs_issuetracker):
  """Group ccs from ggrc system and issuetracker.

  Args:
    - ccs_system: CCs on Issue Tracker Payload
    - ccs_tracker: CCs from Issue Tracker

  Returns:
      list of grouped ccs from ggrc and issuetracker.
  """
  ccs_system = set(cc.strip() for cc in ccs_payload)
  ccs_tracker = set(cc.strip() for cc in ccs_issuetracker)

  return list(ccs_system.union(ccs_tracker))


def _is_need_synchronize_issue(object_id, issue_payload, issuetracker_state):
  """Function that check necessity of issue synchronization.

  Args:
    - issue_payload: Dictionary with information
    for Issue payload.

    - object_id: Id of related object for IssueTracker
    - issuetracker_state: Current state of IssueTracker

  Returns:
    bool object with validate or not indicator (True/False)
  """
  if not issue_payload.get("status"):
    logger.error(
        "Inexistent Issue Tracker status for assessment ID=%d "
        "with status: %s.", object_id, issue_payload.get("status")
    )
    return False

  due_dates_equals, remove_custom_fields = _compare_custom_fields(
      issue_payload.get("custom_fields", []),
      issuetracker_state.get("custom_fields", [])
  )
  if remove_custom_fields:
    issue_payload.pop("custom_fields", [])

  ccs_equals = _compare_ccs(
      issue_payload.get("ccs", []),
      issuetracker_state.get("ccs", [])
  )

  if not ccs_equals:
    # union ccs from system and issuetracker
    # if not equals (or not subset)
    issue_payload["ccs"] = _group_ccs_with_issuetracker(
        issue_payload.get("ccs", []),
        issuetracker_state.get("ccs", [])
    )
  else:
    # restore ccs from issuetracker
    # (ccs from system is subset)
    issue_payload["ccs"] = issuetracker_state.get("ccs", [])

  if all(
      issue_payload.get(field) == issuetracker_state.get(field)
      for field in FIELDS_TO_CHECK
  ) and due_dates_equals and ccs_equals:
    return False
  return True


def _update_issue(cli, issue_id, object_id, issue_payload):
  """Update issue tracker with logging state.

  Args:
    - cli: object of Issue Tracker Client
    - issue_id: Id of IssueTracker
    - object_id: Id of related object for IssueTracker
    - issue_payload: Dictionary with information for Issue payload.

  Returns:
    -
  """
  try:
    sync_utils.update_issue(cli, issue_id, issue_payload)
  except integrations_errors.Error as error:
    logger.error(
        "Unable to update status of Issue Tracker issue ID=%s for "
        "assessment ID=%d: %r",
        issue_id, object_id, error)


def _check_missing_ids(assessment_issues, processed_ids):
  """Check issue tracker objects that hadn't process.

  Args:
    - assessment_issues: Dictionary with Issue information
    - processed_ids: Issue Tracker ids that was processed

  Returns:
    -
  """
  missing_ids = set(assessment_issues) - processed_ids
  if missing_ids:
    logger.warning(
        "Some issues are linked to Assessments "
        "but were not found in Issue Tracker: %s",
        ", ".join(str(missing_id) for missing_id in missing_ids))


def sync_assessment_attributes():  # noqa
  """Synchronizes issue tracker ticket statuses with the Assessment statuses.

  Checks for Assessments which are in sync with Issue Tracker issues and
  updates their statuses in accordance to the corresponding Assessments
  if differ.
  """
  logger.info(
      "Assessment synchronization start: %s",
      datetime.datetime.utcnow()
  )
  assessment_issues = sync_utils.collect_issue_tracker_info(
      "Assessment"
  )
  if not assessment_issues:
    return
  logger.info("Syncing state of %d issues.", len(assessment_issues))

  processed_ids = set()
  tracker_handler = assessment_integration.AssessmentTrackerHandler()
  for batch in sync_utils.iter_issue_batches(assessment_issues.keys()):
    for issue_id, issuetracker_state in batch.iteritems():
      issue_id, issue_info = _get_issue_info_by_issue_id(
          issue_id,
          assessment_issues
      )
      if not issue_info:
        logger.warning(
            "Got an unexpected issue from Issue Tracker: %s", issue_id
        )
        continue

      processed_ids.add(issue_id)

      try:
        tracker_handler.handle_assessment_sync(
            issue_info,
            issue_id,
            issuetracker_state
        )
      except Exception as ex:  # pylint: disable=broad-except
        logger.error(
            "Unhandled synchronization error: %s %s %s",
            issue_id,
            issue_info,
            ex
        )
        continue

  logger.info("Sync is done, %d issue(s) were processed.", len(processed_ids))
  _check_missing_ids(assessment_issues, processed_ids)
