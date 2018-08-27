# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration tests for assessments with IssueTracker integration."""

from collections import OrderedDict

import mock
import ddt

import sqlalchemy as sa

from ggrc import db
from ggrc import models
from ggrc.models import all_models
from ggrc.models.hooks.issue_tracker import assessment_integration
from ggrc.integrations.synchronization_jobs import sync_utils
from ggrc.integrations import synchronization_jobs
from ggrc.access_control.role import AccessControlRole

from integration.ggrc.models import factories
from integration.ggrc import generator
from integration.ggrc.access_control import acl_helper
from integration.ggrc.snapshotter import SnapshotterBaseTestCase


@ddt.ddt
class TestIssueTrackerIntegration(SnapshotterBaseTestCase):
  """Test set for IssueTracker integration functionality."""

  # pylint: disable=invalid-name

  def setUp(self):
    # pylint: disable=super-on-old-class
    # pylint seems to get confused, mro chain successfully resolves and returns
    # <type 'object'> as last entry.
    super(TestIssueTrackerIntegration, self).setUp()

    self.client.get('/login')

  @mock.patch('ggrc.integrations.issues.Client.create_issue')
  def test_complete_assessment_create_issue(self, mock_create_issue):
    """Test the creation of issue for completed assessment."""
    audit = factories.AuditFactory()

    self.api.post(all_models.Assessment, {
        'assessment': {
            'title': 'Assessment1',
            'context': None,
            'audit': {
                'id': audit.id,
                'type': audit.type,
            },
            'status': 'Completed',
        }
    })
    asmt = all_models.Assessment.query.filter_by(title='Assessment1').one()

    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      issue_params = {
          'enabled': True,
          'component_id': hash('Default Component id'),
          'hotlist_id': hash('Default Hotlist id'),
          'issue_type': 'Default Issue type',
          'issue_priority': 'Default Issue priority',
          'issue_severity': 'Default Issue severity',
      }
      self.api.put(asmt, {'issue_tracker': issue_params})
      mock_create_issue.assert_called_once()
      # pylint: disable=W0212
      self.assertEqual(mock_create_issue._mock_call_args[0][0]['status'],
                       'VERIFIED')

  def test_update_issuetracker_info(self):
    """Test that Issue Tracker issues are updated by the utility."""
    cli_patch = mock.patch.object(sync_utils.issues, 'Client')
    hook_patch = mock.patch.object(assessment_integration,
                                   '_is_issue_tracker_enabled',
                                   return_value=True)
    with cli_patch, hook_patch:
      iti_issue_id = []
      for _ in xrange(2):
        iti = factories.IssueTrackerIssueFactory()
        iti_issue_id.append(iti.issue_id)
        asmt = iti.issue_tracked_obj
        asmt_id = asmt.id
        audit = asmt.audit
        self.api.modify_object(audit, {
            'issue_tracker': {
                'enabled': True,
                'component_id': '11111',
                'hotlist_id': '222222',
            },
        })
        asmt = db.session.query(models.Assessment).get(asmt_id)
        self.api.modify_object(asmt, {
            'issue_tracker': {
                'enabled': True,
                'component_id': '11111',
                'hotlist_id': '222222',
            },
        })
        asmt = db.session.query(models.Assessment).get(asmt_id)
        self.api.modify_object(asmt, {
            'issue_tracker': {
                'enabled': True,
                'component_id': '11111',
                'hotlist_id': '222222',
                'issue_priority': 'P4',
                'issue_severity': 'S3',
            },
        })
      self.api.delete(asmt)

    cli_mock = mock.MagicMock()
    cli_mock.update_issue.return_value = None
    cli_mock.search.return_value = {
        'issues': [
            {
                'issueId': iti_issue_id[0],
                'issueState': {
                    'status': 'FIXED', 'type': 'bug2',
                    'priority': 'P2', 'severity': 'S2',
                },
            },
        ],
        'next_page_token': None,
    }

    with mock.patch.object(sync_utils.issues, 'Client', return_value=cli_mock):
      synchronization_jobs.sync_assessment_attributes()
      cli_mock.update_issue.assert_called_once_with(
          iti_issue_id[0], {
              'status': 'ASSIGNED',
              'priority': u'P4',
              'type': None,
              'severity': u'S3',
              'ccs': []
          })

  # pylint: disable=unused-argument
  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  def test_update_issuetracker_assignee(self, mocked_update_issue):
    """Test assignee sync in case it has been updated."""
    email1 = "email1@example.com"
    email2 = "email2@example.com"
    assignee_role_id = AccessControlRole.query.filter_by(
        object_type="Assessment",
        name="Assignees"
    ).first().id
    assignees = [factories.PersonFactory(email=email2),
                 factories.PersonFactory(email=email1)]
    iti_issue_id = []
    iti = factories.IssueTrackerIssueFactory(enabled=True)
    iti_issue_id.append(iti.issue_id)
    asmt = iti.issue_tracked_obj
    asmt_title = asmt.title
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      acl = [acl_helper.get_acl_json(assignee_role_id, assignee.id)
             for assignee in assignees]
      self.api.put(asmt, {
          "access_control_list": acl
      })
      kwargs = {'status': 'ASSIGNED',
                'component_id': None,
                'severity': None,
                'title': asmt_title,
                'hotlist_ids': [],
                'priority': None,
                'assignee': email1,
                'verifier': email1,
                'ccs': [email2]}
      mocked_update_issue.assert_called_once_with(iti_issue_id[0], kwargs)

  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  def test_update_issuetracker_title(self, mocked_update_issue):
    """Test title sync in case it has been updated."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      iti_issue_id = []
      iti = factories.IssueTrackerIssueFactory(enabled=True)
      iti_issue_id.append(iti.issue_id)
      asmt = iti.issue_tracked_obj
      new_title = "New Title"
      self.api.put(asmt, {"title": new_title})
      kwargs = {'status': 'ASSIGNED',
                'component_id': None,
                'severity': None,
                'title': new_title,
                'hotlist_ids': [],
                'priority': None}
      mocked_update_issue.assert_called_once_with(iti_issue_id[0], kwargs)

      issue = db.session.query(models.IssuetrackerIssue).get(iti.id)
      self.assertEqual(issue.title, new_title)

  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  def test_update_issuetracker_due_date(self, mocked_update_issue):
    """Test title sync in case it has been updated."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      iti_issue_id = []
      iti = factories.IssueTrackerIssueFactory(enabled=True)
      iti_issue_id.append(iti.issue_id)
      asmt = iti.issue_tracked_obj
      new_due_date = '2018-09-25'
      custom_fields = [{
          'name': 'Due Date',
          'value': new_due_date,
          'type': 'DATE',
          'display_string': 'Due Date',
      }]
      self.api.put(asmt, {
          'start_date': new_due_date,
          'title': 'title'
      })
      kwargs = {'status': 'ASSIGNED',
                'component_id': None,
                'severity': None,
                'title': 'title',
                'hotlist_ids': [],
                'priority': None,
                'custom_fields': custom_fields}
      mocked_update_issue.assert_called_once_with(iti_issue_id[0], kwargs)

      issue = db.session.query(models.IssuetrackerIssue).get(iti.id)
      self.assertEqual(issue.due_date.strftime("%Y-%m-%d"), new_due_date)

  # pylint: disable=protected-access
  # pylint: disable=too-many-locals
  @ddt.data(
      ('Not Started', {'status': 'ASSIGNED'}),
      ('In Progress', {'status': 'ASSIGNED'}),
      ('In Review', {'status': 'FIXED'}),
      ('Rework Needed', {'status': 'ASSIGNED'}),
      ('Completed', {
          'status': 'VERIFIED',
          'comment': assessment_integration._STATUS_CHANGE_COMMENT_TMPL
      }),
      ('Deprecated', {
          'status': 'OBSOLETE',
          'comment': assessment_integration._STATUS_CHANGE_COMMENT_TMPL
      }),
  )
  @ddt.unpack
  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  def test_change_assessment_status(self, status,
                                    additional_kwargs,
                                    mocked_update_issue):
    """Issue status should be changed for assessment
    with {status} status."""
    email1 = "email1@example.com"
    assignee_role_id = AccessControlRole.query.filter_by(
        object_type="Assessment",
        name="Assignees"
    ).first().id
    assignees = [factories.PersonFactory(email=email1)]
    iti_issue_id = []
    iti = factories.IssueTrackerIssueFactory(enabled=True)
    iti_issue_id.append(iti.issue_id)
    asmt = iti.issue_tracked_obj
    asmt_title = asmt.title
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      acl = [acl_helper.get_acl_json(assignee_role_id, assignee.id)
             for assignee in assignees]
      self.api.put(asmt, {
          "access_control_list": acl,
          "status": status,
      })
      kwargs = {'component_id': None,
                'severity': None,
                'title': asmt_title,
                'hotlist_ids': [],
                'priority': None,
                'assignee': email1,
                'verifier': email1,
                'ccs': []}
      asmt_link = assessment_integration._get_assessment_url(asmt)
      if 'comment' in additional_kwargs:
        additional_kwargs['comment'] = \
            additional_kwargs['comment'] % (status, asmt_link)
      kwargs.update(additional_kwargs)
      mocked_update_issue.assert_called_once_with(iti_issue_id[0], kwargs)

      issue = db.session.query(models.IssuetrackerIssue).get(iti.id)
      self.assertEqual(issue.assignee, email1)
      self.assertEqual(issue.cc_list, "")

  @mock.patch('ggrc.integrations.issues.Client.create_issue')
  @mock.patch('ggrc.integrations.issues.Client.update_issue')
  def test_basic_import(self, mock_create_issue, mock_update_issue):
    """Test basic import functionality."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      # update existing object
      iti = factories.IssueTrackerIssueFactory(enabled=True)
      asmt = iti.issue_tracked_obj
      audit = asmt.audit
      response = self.import_data(OrderedDict([
          ('object_type', 'Assessment'),
          ('Code*', asmt.slug),
          ('Audit', audit.slug),
      ]))
      self._check_csv_response(response, {})

      # import new object
      response = self.import_data(OrderedDict([
          ('object_type', 'Assessment'),
          ('Code*', 'Test Code'),
          ('Audit', audit.slug),
          ('Creators', 'user@example.com'),
          ('Assignees*', 'user@example.com'),
          ('Title', 'Some Title'),
      ]))
      self._check_csv_response(response, {})

  @mock.patch('ggrc.integrations.issues.Client.create_issue')
  def test_audit_delete(self, mock_create_issue):
    """Test deletion of an audit."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          issue_tracked_obj=audit,
          component_id="some id",
          hotlist_id="some host id",
      )
      result = self.api.delete(audit)
      self.assert200(result)

      audit = factories.AuditFactory()
      factories.IssueTrackerIssueFactory(
          issue_tracked_obj=audit,
          component_id="some id",
          hotlist_id="some host id",
      )
      result = self.api.delete(audit)
      self.assert200(result)

  @mock.patch("ggrc.integrations.issues.Client.update_issue")
  def test_update_ccs_many_audit_captains(self, mock_update_issue):
    """CCS of assessment should include secondary audit captains."""
    with mock.patch.object(assessment_integration, '_is_issue_tracker_enabled',
                           return_value=True):
      audit = factories.AuditFactory()
      audit_captains = factories.PersonFactory.create_batch(2)
      audit_captain_role = all_models.AccessControlRole.query.filter_by(
          name="Audit Captains",
          object_type="Audit"
      ).one()
      response_audit = self.api.put(
          audit,
          {
              "access_control_list": [
                  {
                      "ac_role_id": audit_captain_role.id,
                      "person": {
                          "id": audit_captain.id,
                          "type": "Person"
                      }
                  } for audit_captain in audit_captains]
          }
      )
      self.assert200(response_audit)
      issue_tracker_audit = all_models.IssuetrackerIssue.query.filter_by(
          object_id=audit.id,
          object_type=audit.type
      ).one()
      audit_cc = issue_tracker_audit.cc_list
      self.assertEqual(
          audit_cc,
          audit_captains[1].email
      )

      assessment = factories.AssessmentFactory(
          audit=audit
      )
      assessment_issue = factories.IssueTrackerIssueFactory(
          enabled=True,
          issue_tracked_obj=assessment,
          component_id="11111",
          hotlist_id="222222",
      )
      assessment_persons = factories.PersonFactory.create_batch(3)
      assignee_role = all_models.AccessControlRole.query.filter_by(
          name="Assignees",
          object_type="Assessment"
      ).one()
      creator_role = all_models.AccessControlRole.query.filter_by(
          name="Creators",
          object_type="Assessment"
      ).one()
      response_assessment = self.api.put(
          assessment,
          {
              "issue_tracker": {
                  "component_id": "11111",
                  "enabled": True,
                  "hotlist_id": "222222",
                  "issue_priority": "P2",
                  "issue_severity": "S2",
                  "issue_type": "PROCESS",
                  "issue_id": assessment_issue.issue_id
              },
              "access_control_list": [
                  {
                      "ac_role_id": creator_role.id
                      if not index else assignee_role.id,
                      "id": index + 1,
                      "person": {
                          "context_id": None,
                          "href": "/api/people/{}".format(
                              person.id
                          ),
                          "id": person.id,
                          "type": "Person"
                      },
                      "person_email": person.email,
                      "person_id": person.id,
                      "person_name": person.name,
                      "type": "AccessControlList"
                  }
                  for index, person in enumerate(assessment_persons)]
          }
      )
      self.assert200(response_assessment)
      issue_tracker_assessment = all_models.IssuetrackerIssue.query.filter_by(
          object_id=assessment.id,
          object_type=assessment.type
      ).one()
      issue_tracker_cc = issue_tracker_assessment.cc_list.split(',')[0]
      assessment_emails = [person.email for person in assessment_persons]
      self.assertIn(issue_tracker_cc, assessment_emails)
      self.assertItemsEqual(
          mock_update_issue.call_args[0][1]["ccs"],
          [issue_tracker_cc, audit_cc]
      )


@mock.patch('ggrc.models.hooks.issue_tracker.'
            'assessment_integration._is_issue_tracker_enabled',
            return_value=True)
@mock.patch('ggrc.integrations.issues.Client')
class TestIssueTrackerIntegrationPeople(SnapshotterBaseTestCase):
  """Test people used in IssueTracker Issues."""

  EMAILS = {
      ("Audit", "Audit Captains"): {
          "audit_captain_1@example.com",
          "audit_captain_2@example.com"
      },
      ("Audit", "Auditors"): {
          "auditor_1@example.com",
          "auditor_2@example.com"
      },
      ("Assessment", "Creators"): {
          "creator_1@example.com",
          "creator_2@example.com"
      },
      ("Assessment", "Assignees"): {
          "assignee_1@example.com",
          "assignee_2@example.com"
      },
      ("Assessment", "Verifiers"): {
          "verifier_1@example.com",
          "verifier_2@example.com"
      },
      ("Assessment", "Custom Role"): {
          "curom_role_1@example.com"
      },
      ("Assessment", "Primary Contacts"): {
          "primary_contact_1@example.com",
          "primary_contact_2@example.com"
      },
      ("Assessment", "Secondary Contacts"): {
          "secondary_contact_1@example.com",
          "secondary_contact_2@example.com"
      },
  }

  ROLE_NAMES = (
      'Creators',
      'Assignees',
      'Verifiers',
      'Primary Contacts',
      'Secondary Contacts',
      'Custom Role'
  )

  def setUp(self):
    super(TestIssueTrackerIntegrationPeople, self).setUp()
    self.generator = generator.ObjectGenerator()

    factories.AccessControlRoleFactory(
        name='Custom Role',
        internal=False,
        object_type='Assessment',
    )

    # fetch all roles mentioned in self.EMAILS
    self.roles = {
        role.name: role
        for role in all_models.AccessControlRole.query.filter(
            sa.tuple_(
                all_models.AccessControlRole.object_type,
                all_models.AccessControlRole.name,
            ).in_(
                self.EMAILS.keys(),
            ),
        )
    }

    with factories.single_commit():
      self.audit = factories.AuditFactory()

      self.people = {
          role_name: [factories.PersonFactory(email=email)
                      for email in emails]
          for (_, role_name), emails in self.EMAILS.iteritems()
      }

  def setup_audit_people(self, role_name_to_people):
    """Assign roles to people provided."""
    with factories.single_commit():
      for role_name, people in role_name_to_people.iteritems():
        role = self.roles[role_name]
        for person in people:
          factories.AccessControlListFactory(person=person,
                                             ac_role=role,
                                             object=self.audit)

  def create_asmt_with_issue_tracker(self, role_name_to_people,
                                     issue_tracker=None):
    """Create Assessment with issue_tracker parameters and ACL."""
    access_control_list = acl_helper.get_acl_list({
        person.id: self.roles[role_name].id
        for role_name, people in role_name_to_people.iteritems()
        for person in people
    })
    issue_tracker_with_defaults = {
        'enabled': True,
        'component_id': hash('Default Component id'),
        'hotlist_id': hash('Default Hotlist id'),
        'issue_type': 'Default Issue type',
        'issue_priority': 'Default Issue priority',
        'issue_severity': 'Default Issue severity',
    }
    issue_tracker_with_defaults.update(issue_tracker or {})

    _, asmt = self.generator.generate_object(
        all_models.Assessment,
        data={
            'audit': {'id': self.audit.id, 'type': self.audit.type},
            'issue_tracker': issue_tracker_with_defaults,
            'access_control_list': access_control_list,
        }
    )

    return asmt

  def test_new_assessment_people(self, client_mock, _):
    """External Issue for Assessment contains correct people."""
    client_instance = client_mock.return_value
    client_instance.create_issue.return_value = {'issueId': 42}

    self.setup_audit_people({
        role_name: people for role_name, people in self.people.items()
        if role_name in ('Audit Captains', 'Auditors')
    })

    component_id = hash('Component id')
    hotlist_id = hash('Hotlist id')
    issue_type = 'Issue type'
    issue_priority = 'Issue priority'
    issue_severity = 'Issue severity'

    asmt = self.create_asmt_with_issue_tracker(
        role_name_to_people={
            role_name: people for role_name, people in self.people.items()
            if role_name in self.ROLE_NAMES
        },
        issue_tracker={
            'component_id': component_id,
            'hotlist_id': hotlist_id,
            'issue_type': issue_type,
            'issue_priority': issue_priority,
            'issue_severity': issue_severity,
        },
    )

    expected_cc_list = list(
        self.EMAILS["Assessment", "Assignees"] -
        {min(self.EMAILS["Assessment", "Assignees"])}
    )

    # pylint: disable=protected-access; we assert by non-exported constants
    client_instance.create_issue.assert_called_once_with({
        # common fields
        'comment': (assessment_integration._INITIAL_COMMENT_TMPL %
                    assessment_integration._get_assessment_url(asmt)),
        'component_id': component_id,
        'hotlist_ids': [hotlist_id],
        'priority': issue_priority,
        'severity': issue_severity,
        'status': 'ASSIGNED',
        'title': asmt.title,
        'type': issue_type,

        # person-related fields
        'reporter': min(self.EMAILS["Audit", "Audit Captains"]),
        'assignee': min(self.EMAILS["Assessment", "Assignees"]),
        'verifier': min(self.EMAILS["Assessment", "Assignees"]),
        'ccs': expected_cc_list,
    })

  def test_missing_audit_captains(self, client_mock, _):
    """Reporter email is None is no Audit Captains present."""
    client_instance = client_mock.return_value
    client_instance.create_issue.return_value = {'issueId': 42}

    self.setup_audit_people({
        'Audit Captains': [],
        'Auditors': self.people['Auditors'],
    })

    self.create_asmt_with_issue_tracker(
        role_name_to_people={
            role_name: people for role_name, people in self.people.items()
            if role_name in ('Creators', 'Assignees', 'Verifiers')
        },
    )

    client_instance.create_issue.assert_called_once()
    self.assertIs(client_instance.create_issue.call_args[0][0]['reporter'],
                  None)
