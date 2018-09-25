# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Lists of ggrc contributions."""

from ggrc.integrations import synchronization_jobs
from ggrc.models import import_export
from ggrc.notifications import common
from ggrc.notifications import fast_digest
from ggrc.notifications import notification_handlers
from ggrc.notifications import data_handlers


NIGHTLY_CRON_JOBS = [
    common.generate_cycle_tasks_notifs,
    common.send_daily_digest_notifications,
    import_export.clear_overtimed_tasks,
]

HOURLY_CRON_JOBS = [
    synchronization_jobs.sync_assessment_attributes,
    synchronization_jobs.sync_issue_attributes,
]

HALF_HOUR_CRON_JOBS = [
    fast_digest.send_notification,
]

NOTIFICATION_LISTENERS = [
    notification_handlers.register_handlers
]


def contributed_notifications():
  """Get handler functions for ggrc notification file types."""
  return {
      "Assessment": data_handlers.get_assignable_data,
      "Comment": data_handlers.get_comment_data,
      "Review": lambda x: {}
  }
