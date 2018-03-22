# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Audit model."""

from sqlalchemy import orm
from werkzeug.exceptions import Forbidden

from ggrc import db
from ggrc.access_control.list import AccessControlList
from ggrc.access_control.roleable import Roleable
from ggrc.builder import simple_property
from ggrc.login import get_current_user
from ggrc.models.deferred import deferred
from ggrc.models import mixins
from ggrc.models.mixins.with_evidence import WithEvidence
from ggrc.rbac import SystemWideRoles

from ggrc.fulltext.mixin import Indexed
from ggrc.models import issuetracker_issue
from ggrc.models import reflection
from ggrc.models.context import HasOwnContext
from ggrc.models.mixins import clonable
from ggrc.models.mixins import WithLastDeprecatedDate
from ggrc.models.object_person import Personable
from ggrc.models.program import Program
from ggrc.models.person import Person
from ggrc.models.relationship import Relatable
from ggrc.models.snapshot import Snapshotable


class Audit(Snapshotable,
            clonable.SingleClonable,
            WithEvidence,
            mixins.CustomAttributable,
            Personable,
            HasOwnContext,
            Relatable,
            Roleable,
            issuetracker_issue.IssueTracked,
            WithLastDeprecatedDate,
            mixins.Timeboxed,
            mixins.BusinessObject,
            mixins.Folderable,
            Indexed,
            db.Model):
  """Audit model."""

  __tablename__ = 'audits'
  _slug_uniqueness = False

  VALID_STATES = (
      u'Planned', u'In Progress', u'Manager Review',
      u'Ready for External Review', u'Completed', u'Deprecated'
  )

  CLONEABLE_CHILDREN = {"AssessmentTemplate"}

  report_start_date = deferred(db.Column(db.Date), 'Audit')
  report_end_date = deferred(db.Column(db.Date), 'Audit')
  audit_firm_id = deferred(
      db.Column(db.Integer, db.ForeignKey('org_groups.id')), 'Audit')
  audit_firm = db.relationship('OrgGroup', uselist=False)
  gdrive_evidence_folder = deferred(db.Column(db.String), 'Audit')
  program_id = deferred(
      db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False),
      'Audit')
  object_type = db.Column(
      db.String(length=250), nullable=False, default='Control')

  assessments = db.relationship('Assessment', backref='audit')
  issues = db.relationship('Issue', backref='audit')
  archived = deferred(db.Column(db.Boolean,
                      nullable=False, default=False), 'Audit')
  assessment_templates = db.relationship('AssessmentTemplate', backref='audit')

  _api_attrs = reflection.ApiAttributes(
      'report_start_date',
      'report_end_date',
      'audit_firm',
      'gdrive_evidence_folder',
      'program',
      'object_type',
      'archived',
      reflection.Attribute('issue_tracker', create=False, update=False),
  )

  _fulltext_attrs = [
      'archived',
      'report_start_date',
      'report_end_date',
      'audit_firm',
      'gdrive_evidence_folder',
  ]

  @classmethod
  def indexed_query(cls):
    return super(Audit, cls).indexed_query().options(
        orm.Load(cls).undefer_group(
            "Audit_complete",
        ),
    )

  _sanitize_html = [
      'gdrive_evidence_folder',
      'description',
  ]

  _include_links = []

  _aliases = {
      "program": {
          "display_name": "Program",
          "filter_by": "_filter_by_program",
          "mandatory": True,
      },
      "start_date": "Planned Start Date",
      "end_date": "Planned End Date",
      "report_start_date": "Planned Report Period from",
      "report_end_date": "Planned Report Period to",
      "notes": None,
      "archived": {
          "display_name": "Archived",
          "mandatory": False
      },
      "status": {
          "display_name": "State",
          "mandatory": True,
          "description": "Options are:\n{}".format('\n'.join(VALID_STATES))
      }
  }

  @simple_property
  def issue_tracker(self):
    """Returns representation of issue tracker related info as a dict."""
    issue_obj = issuetracker_issue.IssuetrackerIssue.get_issue(
        'Audit', self.id)
    return issue_obj.to_dict() if issue_obj is not None else {}

  def _clone(self, source_object):
    """Clone audit and all relevant attributes.

    Keeps the internals of actual audit cloning and everything that is related
    to audit itself (auditors, audit firm, context setting,
    custom attribute values, etc.)
    """
    from ggrc_basic_permissions import create_audit_context

    data = {
        "title": source_object.generate_attribute("title"),
        "description": source_object.description,
        "audit_firm": source_object.audit_firm,
        "start_date": source_object.start_date,
        "end_date": source_object.end_date,
        "last_deprecated_date": source_object.last_deprecated_date,
        "program": source_object.program,
        "status": source_object.VALID_STATES[0],
        "report_start_date": source_object.report_start_date,
        "report_end_date": source_object.report_end_date
    }

    self.update_attrs(data)
    db.session.flush()

    create_audit_context(self)
    self.clone_acls(source_object)
    self.clone_custom_attribute_values(source_object)

  def clone_acls(self, audit):
    """Clone acl roles like auditors and audit captains

    Args:
      audit: Audit instance
    """
    for acl in audit.access_control_list:
      if acl.parent_id:
        continue
      data = {
          "person": acl.person,
          "ac_role": acl.ac_role,
          "object": self,
          "context": acl.context,
      }
      new_acl = AccessControlList(**data)
      db.session.add(new_acl)

  def clone(self, source_id, mapped_objects=None):
    """Clone audit with specified whitelisted children.

    Children that can be cloned should be specified in CLONEABLE_CHILDREN.

    Args:
      mapped_objects: A list of related objects that should also be copied and
      linked to a new audit.
    """
    if not mapped_objects:
      mapped_objects = []

    source_object = Audit.query.get(source_id)
    self._clone(source_object)

    if any(mapped_objects):
      related_children = source_object.related_objects(mapped_objects)

      for obj in related_children:
        obj.clone(self)

  @orm.validates("archived")
  def archived_check(self, _, value):
    """Only Admins and Program Managers are allowed to (un)archive Audit."""
    user = get_current_user()
    if getattr(user, 'system_wide_role', None) in SystemWideRoles.admins:
      return value

    if self.archived is not None and self.archived != value and \
       not any(acl for acl in list(self.full_access_control_list)
               if acl.ac_role.name.startswith("Program Managers*") and
               acl.person.id == user.id):
      # NOTE: the check above should not use full_access_control_list and check
      # for the role should be done as:
      # acl.ac_role.parent.parent.name == "Program Managers"
      # or:
      # acl.parent.parent.ac_role.name == "Program Managers"
      # to ensure the current acl entry was propagated from program managers
      # this check is done with startswith as an optimization to prevent too
      # many queries until we create a link to base propagated role or acl
      # entry.
      raise Forbidden()
    return value

  @classmethod
  def _filter_by_program(cls, predicate):
    """Helper for filtering by program"""
    return Program.query.filter(
        (Program.id == Audit.program_id) &
        (predicate(Program.slug) | predicate(Program.title))
    ).exists()

  @classmethod
  def _filter_by_auditor(cls, predicate):
    """Helper for filtering by auditor"""
    from ggrc_basic_permissions.models import Role, UserRole
    return UserRole.query.join(Role, Person).filter(
        (Role.name == "Auditor") &
        (UserRole.context_id == cls.context_id) &
        (predicate(Person.name) | predicate(Person.email))
    ).exists()

  @classmethod
  def eager_query(cls):
    query = super(Audit, cls).eager_query()
    return query.options(
        orm.joinedload('program'),
        orm.subqueryload('object_people').joinedload('person'),
    )


def build_audit_stub(obj):
  """Returns a stub of audit model to which assessment is related to."""
  audit_id = obj.audit_id
  if audit_id is None:
    return None
  issue_obj = issuetracker_issue.IssuetrackerIssue.get_issue(
      'Audit', audit_id)
  return {
      'type': 'Audit',
      'id': audit_id,
      'context_id': obj.context_id,
      'href': '/api/audits/%d' % audit_id,
      'issue_tracker': issue_obj.to_dict() if issue_obj is not None else {},
  }
