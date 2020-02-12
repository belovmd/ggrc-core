# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for notifications for models with assignable mixin."""

from collections import OrderedDict

from sqlalchemy import and_

from ggrc import db
from ggrc import contributions
from ggrc.models import Notification
from ggrc.models import NotificationType
from ggrc.models import Assessment
from ggrc.models import Revision
from integration.ggrc import api_helper
from integration.ggrc import TestCase
from integration.ggrc import generator
from integration.ggrc.models import factories


class TestAssessmentDataHandlers(TestCase):
  """Test data handlers for various Assessment notifications."""

  def setUp(self):
    super(TestAssessmentDataHandlers, self).setUp()
    self.client.get("/login")
    self.api_helper = api_helper.Api()
    self.generator = generator.ObjectGenerator()
    self.handlers = contributions.contributed_notifications()
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.PersonFactory(email="user1@example.com")
      factories.PersonFactory(email="user2@example.com")
      factories.PersonFactory(email="user3@example.com")
    self.import_data(
        OrderedDict([
            ("object_type", "Assessment"),
            ("Code*", ""),
            ("Audit*", audit.slug),
            ("State", "In Progress"),
            ("title", "No template Assessment 1"),
            ("Assignees", "user1@example.com"),
            ("Creators", "user2@example.com"),
            ("Verifiers", "user3@example.com"),
            ("Conclusion: Design", "Effective"),
            ("Conclusion: Operation", "Effective")
        ]),
        OrderedDict([
            ("object_type", "Assessment"),
            ("Code*", ""),
            ("Audit*", audit.slug),
            ("State", "In Progress"),
            ("title", "No template Assessment 2"),
            ("Assignees", "user1@example.com"),
            ("Creators", "user2@example.com"),
            ("Conclusion: Design", "Ineffective"),
            ("Conclusion: Operation", "Needs improvement")
        ]),
    )

  def _call_notif_handler(self, notif):
    """Call the default data handler for the notification object.

    Args:
      notif (Notification): notification for which we want te get data

    Returns:
      Result of the data handler for the given object.
    """
    return self.handlers[notif.object_type](notif)

  @classmethod
  def _get_notification(cls, obj, notif_type):
    return db.session.query(Notification).join(NotificationType).filter(and_(
        Notification.object_id == obj.id,
        Notification.object_type == obj.type,
        NotificationType.name == notif_type,
    ))

  def test_open_assessment(self):
    """Test data handlers for opened requests."""
    asmt1 = Assessment.query.filter_by(
        title="No template Assessment 1"
    ).first()
    asmt2 = Assessment.query.filter_by(
        title="No template Assessment 2"
    ).first()

    notifs = self._get_notification(asmt1, "assessment_open").all()
    self.assertEqual(1, len(notifs))

    notif = notifs[0]
    count_revisions = Revision.query.filter_by(resource_type='Notification',
                                               resource_id=notif.id).count()
    self.assertEqual(count_revisions, 1)

    asmt_1_expected_keys = {
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
    }
    open_data = self._call_notif_handler(notif)
    self.assertEqual(set(open_data.keys()), asmt_1_expected_keys)

    notifs = self._get_notification(asmt2, "assessment_open").all()
    self.assertEqual(1, len(notifs))

    notif = notifs[0]
    revisions = Revision.query.filter_by(resource_type='Notification',
                                         resource_id=notif.id).count()
    self.assertEqual(revisions, 1)

    open_data = self._call_notif_handler(notif)
    asmt_2_expected_keys = {"user1@example.com", "user2@example.com"}
    self.assertEqual(set(open_data.keys()), asmt_2_expected_keys)

  def test_declined_assessment(self):
    """Test data handlers for declined assessments"""
    # decline assessment 1
    asmt1 = Assessment.query.filter_by(
        title="No template Assessment 1"
    ).first()

    self.api_helper.modify_object(asmt1, {"status": Assessment.DONE_STATE})
    self.api_helper.modify_object(asmt1, {"status": Assessment.PROGRESS_STATE})

    notifs = self._get_notification(asmt1, "assessment_declined").all()
    self.assertEqual(1, len(notifs))

    notif = notifs[0]
    count_revisions = Revision.query.filter_by(resource_type='Notification',
                                               resource_id=notif.id).count()
    self.assertEqual(count_revisions, 1)

    expected_emails = {  # literally everybody assigned to an Assessment
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
    }
    declined_data = self._call_notif_handler(notif)
    self.assertEqual(set(declined_data.keys()), expected_emails)

  def test_assessment_comments(self):
    """Test data handlers for comment to assessment"""
    asmt1 = Assessment.query.filter_by(
        title="No template Assessment 1"
    ).first()

    _, comment = self.generator.generate_comment(asmt1, "Verifiers",
                                                 "some comment",
                                                 send_notification="true")
    notifs = self._get_notification(comment, "comment_created").all()
    self.assertEqual(1, len(notifs))

    notif = notifs[0]
    count_revisions = Revision.query.filter_by(resource_type='Notification',
                                               resource_id=notif.id).count()
    self.assertEqual(count_revisions, 1)

    requester_emails = {
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
    }
    declined_data = self._call_notif_handler(notif)
    self.assertEqual(set(declined_data.keys()), requester_emails)

  def test_assessment_updated(self):
    """Test data handlers for update assessment"""
    # decline assessment 1
    asmt1 = Assessment.query.filter_by(
        title="No template Assessment 1"
    ).first()

    count_notifs = self._get_notification(asmt1, "assessment_updated").count()
    self.assertFalse(count_notifs)

    self.api_helper.modify_object(asmt1, {"title": "update_assessment",
                                          "status": asmt1.DONE_STATE})
    count_notifs = self._get_notification(asmt1, "assessment_updated").count()
    self.assertEqual(1, count_notifs)

    self.api_helper.modify_object(asmt1, {"title": "title_update_again"})
    count_notifs = self._get_notification(asmt1, "assessment_updated").count()
    self.assertEqual(1, count_notifs)
