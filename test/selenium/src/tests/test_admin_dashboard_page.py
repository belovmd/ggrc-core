# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Admin dashboard page smoke tests."""
# pylint: disable=no-self-use
# pylint: disable=invalid-name
# pylint: disable=too-few-public-methods
# pylint: disable=protected-access
# pylint: disable=unused-argument

import random
from datetime import timedelta

import pytest

from lib import base, constants, url, users
from lib.constants import messages, objects, roles
from lib.constants.element import AdminWidgetCustomAttributes
from lib.entities import entities_factory
from lib.page import dashboard
from lib.service import admin_webui_service, rest_facade
from lib.utils import date_utils, selenium_utils, string_utils


class TestAdminDashboardPage(base.Test):
  """Tests for admin dashboard page."""

  _role_el = constants.element.AdminWidgetRoles
  _event_el = constants.element.AdminWidgetEvents

  @pytest.fixture(scope="function")
  def admin_dashboard(self, selenium):
    """Open Admin Dashboard URL and
    return AdminDashboard page objects model."""
    selenium_utils.open_url(url.Urls().admin_dashboard)
    return dashboard.AdminDashboard(selenium)

  @pytest.mark.smoke_tests
  def test_roles_widget(self, admin_dashboard):
    """Check count and content of role scopes."""
    admin_roles_tab = admin_dashboard.select_roles()
    expected_dict = self._role_el.ROLE_SCOPES_DICT
    actual_dict = admin_roles_tab.get_role_scopes_text_as_dict()
    assert admin_dashboard.tab_roles.member_count == len(expected_dict)
    assert expected_dict == actual_dict, (
        messages.AssertionMessages.
        format_err_msg_equal(expected_dict, expected_dict))

  @pytest.mark.smoke_tests
  def test_events_widget_tree_view_has_data(self, admin_dashboard):
    """Confirms tree view has at least one data row in valid format."""
    admin_events_tab = admin_dashboard.select_events()
    list_items = admin_events_tab.events
    assert list_items
    items_with_incorrect_format = [
        item
        for item in list_items
        if any(value in ["", []] for value in item.itervalues())]
    assert len(items_with_incorrect_format) in [0, 1]
    if len(items_with_incorrect_format) == 1:
      # A line with incorrect format is created during DB migration.
      # We decided it's OK.
      assert (items_with_incorrect_format[0]["user_email"] ==
              users.MIGRATOR_USER_EMAIL)
    expected_header_text = self._event_el.WIDGET_HEADER
    actual_header_text = admin_events_tab.widget_header.text
    assert expected_header_text == actual_header_text

  @pytest.mark.smoke_tests
  def test_check_ca_groups(self, admin_dashboard):
    """Check that full list of Custom Attributes groups is displayed
    on Admin Dashboard panel.
    """
    ca_tab = admin_dashboard.select_custom_attributes()
    expected_ca_groups_set = set(
        [objects.get_normal_form(item) for item in objects.ALL_CA_OBJS])
    actual_ca_groups_set = set(
        [item.text for item in ca_tab.get_items_list()])
    assert expected_ca_groups_set == actual_ca_groups_set

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      "ca_type",
      AdminWidgetCustomAttributes.ALL_GCA_TYPES
  )
  def test_add_global_ca(self, admin_dashboard, ca_type):
    """Create different types of Custom Attribute on Admin Dashboard."""
    def_type = objects.get_normal_form(random.choice(objects.ALL_CA_OBJS))
    expected_ca = entities_factory.CustomAttributeDefinitionsFactory().create(
        attribute_type=ca_type, definition_type=def_type)
    ca_tab = admin_dashboard.select_custom_attributes()
    ca_tab.add_custom_attribute(ca_obj=expected_ca)
    actual_cas = ca_tab.get_custom_attributes_list(ca_group=expected_ca)
    # 'actual_ca': multi_choice_options (None)
    self.general_contain_assert(expected_ca, actual_cas,
                                "multi_choice_options")

  @pytest.mark.smoke_tests
  def test_custom_roles_widget(self, admin_dashboard):
    """Check count and content of roles scopes."""
    expected_set = set(
        [objects.get_normal_form(item) for
         item in objects.ALL_OBJS_W_CUSTOM_ROLES]
    )
    actual_set = \
        admin_dashboard.select_custom_roles().get_objects_text_as_set()
    assert admin_dashboard.tab_custom_roles.member_count == len(expected_set)
    assert expected_set == actual_set, (
        messages.AssertionMessages.
        format_err_msg_equal(expected_set, actual_set))


class TestEventLogTabDestructive(base.Test):
  """Tests for Event log."""
  _data = None

  @classmethod
  def get_event_tab(cls):
    """Return Event tab page object."""
    selenium_utils.open_url(url.Urls().admin_dashboard)
    return dashboard.AdminDashboard().select_events()

  @pytest.fixture()
  def tested_events(self, selenium):
    """Create events to verify events functionality:
    0. Save event log count before test data creation,
    1. Create objective editor role, create 2 users with global creator role
    under admin
    2. Create objective#1 under global creator#1 and set global creator#2 to
    newly created objective editor role
    3. Create objective#2 under global objective#2 and map it objective#1
    """
    if not self.__class__._data:
      # generate enough data, so test can be executed independently
      for _ in xrange(6):
        rest_facade.create_user_with_role(roles.READER)

      initial_count = self.get_event_tab().tab_events.count
      objctv1_creator = rest_facade.create_user_with_role(roles.CREATOR)
      objctv2_creator = rest_facade.create_user_with_role(roles.CREATOR)
      objctv_editor_role = rest_facade.create_access_control_role(
          object_type="Objective", read=True, update=True, delete=True)
      admin = users.current_user()
      users.set_current_user(objctv1_creator)
      objctv_custom_roles = [
          (objctv_editor_role.name, objctv_editor_role.id, [objctv2_creator])
      ]
      objctv1 = rest_facade.create_objective(custom_roles=objctv_custom_roles)
      # wait until notification and acl will assigned by background task
      rest_facade.get_obj(objctv1_creator)

      users.set_current_user(objctv2_creator)
      objctv2 = rest_facade.create_objective()
      rest_facade.map_objs(objctv1, objctv2)

      users.set_current_user(admin)
      # generate expected event data
      from lib.constants.roles import ACLRolesIDs
      # 3 predefined program roles and 1 predefined reviewer role
      acl_roles_len = len(ACLRolesIDs.object_roles(objctv1.type)) - 4
      exp_event_data = [
          {"actions": sorted(
              [objctv1_creator.email + " created", u"PersonProfile created"]),
           "user_email": admin.email,
           "time": date_utils.iso8601_to_local_datetime(
              objctv1_creator.updated_at)},
          {"actions": ["Creator linked to " + objctv1_creator.email],
           "user_email": admin.email,
           "time": date_utils.iso8601_to_local_datetime(
              objctv1_creator.updated_at)},
          {"actions": sorted(
              [objctv2_creator.email + " created", u"PersonProfile created"]),
           "user_email": admin.email,
           "time": date_utils.iso8601_to_local_datetime(
              objctv2_creator.updated_at)},
          {"actions": ["Creator linked to " + objctv2_creator.email],
           "user_email": admin.email,
           "time": date_utils.iso8601_to_local_datetime(
              objctv2_creator.updated_at)},
          {"actions": [objctv_editor_role.name + " created"],
           "user_email": admin.email,
           "time": date_utils.iso8601_to_local_datetime(
              objctv_editor_role.updated_at)},
          {"actions": [u"AccessControlList created"] * acl_roles_len +
                      [u"AccessControlPerson created"] * 2 +
                      [objctv1.title + " created"],
           "user_email": objctv1_creator.email,
           "time": date_utils.iso8601_to_local_datetime(objctv1.updated_at)},
          {"actions": [u"AccessControlList created"] * acl_roles_len +
                      [u"AccessControlPerson created",
                       objctv2.title + " created"],
           "user_email": objctv2_creator.email,
           "time": date_utils.iso8601_to_local_datetime(objctv2.updated_at)},
          {"actions": [u"{type2}:{id2} linked to {type1}:{id1}".format(
              id1=objctv1.id, id2=objctv2.id, type1=objctv1.type,
              type2=objctv2.type)],
           "user_email": objctv2_creator.email,
           "time": date_utils.iso8601_to_local_datetime(objctv2.updated_at)}
      ]
      exp_event_data.reverse()
      self.__class__._data = {
          "objctv1_creator": objctv1_creator,
          "objctv2_creator": objctv2_creator,
          "objctv_editor_role": objctv_editor_role,
          "objctv1": objctv1,
          "objctv2": objctv2,
          "exp_added_events": exp_event_data,
          "initial_count": initial_count
      }
    return self.__class__._data

  @pytest.fixture()
  def exp_act_events(self, tested_events, selenium):
    """Store actual added events to data attribute."""
    self._data["act_added_events"] = self.get_event_tab().events[:(
        len(tested_events["exp_added_events"]))]
    return self._data

  def test_chronological_sequence_1st_page(self, tested_events, selenium):
    """Verify that items on 1st page is presented on tab in chronological
    order."""
    datetime_list = self.get_event_tab().event_attrs("time")
    date_utils.assert_chronological_order(datetime_list)

  def test_btns_at_1st_page(self, tested_events, selenium):
    """Verify that 1st page has NEXT PAGE navigation button only
    and doesn't have PREVIOUS PAGE navigation button.
    """
    event_tab_btns = self.get_event_tab().paging_buttons
    actual_btn_names = [btn.text for btn in event_tab_btns]
    assert actual_btn_names == ["NEXT PAGE"]

  def test_chronological_sequence_2nd_page(self, tested_events, selenium):
    """Verify that chronological order is continue at 2nd page too."""
    page_1 = self.get_event_tab()
    last_event_datetime_page_1 = page_1.event_attrs("time")[-1]
    event_tab_page_2 = page_1.go_to_next_page()
    event_datetimes_page_2 = event_tab_page_2.event_attrs("time")
    assert last_event_datetime_page_1 >= event_datetimes_page_2[0]
    date_utils.assert_chronological_order(event_datetimes_page_2)

  def test_previous_page_redirect(self, tested_events, selenium):
    """Verify that click on PREVIOUS PAGE navigation button on 2nd page
    redirect to 1st page.
    """
    page_1 = self.get_event_tab()
    events_on_1st_page = page_1.events
    events_on_prev_page = page_1.go_to_next_page().go_to_prev_page().events
    assert events_on_1st_page == events_on_prev_page, (
        messages.AssertionMessages.
        format_err_msg_equal(events_on_1st_page, events_on_prev_page))

  def test_events_data_wo_datetime(self, exp_act_events):
    """Verify that last data in event log represent performed actions."""
    keys = ["actions", "user_email"]
    exp_events_wo_time = string_utils.extract_items(
        exp_act_events["exp_added_events"], *keys)
    act_events_wo_time = string_utils.extract_items(
        exp_act_events["act_added_events"], *keys)
    assert act_events_wo_time == exp_events_wo_time

  def test_events_datetime_only(self, exp_act_events):
    """Check times of added events."""
    key = "time"
    exp_events_times = string_utils.extract_items(
        exp_act_events["exp_added_events"], key)
    act_event_times = string_utils.extract_items(
        exp_act_events["act_added_events"], key)
    for act, exp in zip(act_event_times, exp_events_times):
      assert pytest.approx(act == exp, rel=timedelta(seconds=1))

  def test_events_increased(self, tested_events, selenium):
    """Verify that count at event tab increased correctly."""
    act_count = self.get_event_tab().tab_events.count
    exp_count = tested_events["initial_count"] + len(
        tested_events["exp_added_events"])
    assert act_count == exp_count


class TestPeopleAdministration(base.Test):
  """Test for People tab functionality."""
  data = None

  @pytest.fixture()
  def ppl_data(self, selenium):
    """Create person and return test data."""
    if not self.__class__.data:
      expected_person = entities_factory.PeopleFactory().create(
          system_wide_role=roles.NO_ROLE)
      ppl_admin_service = admin_webui_service.PeopleAdminWebUiService(
          selenium)
      self.__class__.data = {
          "exp_person": expected_person,
          "exp_ppl_count": ppl_admin_service.ppl_count + 1,
          "act_person": ppl_admin_service.create_new_person(expected_person),
          "act_ppl_count": ppl_admin_service.ppl_count
      }
    return self.__class__.data

  def test_destructive_create_new_person_w_no_role(self, ppl_data):
    """Check newly created person is on Admin People widget and ppl count
    increased by one.
    """
    self.general_equal_assert(ppl_data["exp_person"], ppl_data["act_person"])

  @pytest.mark.xfail(reason="GGRC-6528 Issue in app.")
  def test_destructive_tab_count_increased(self, ppl_data):
    """Check that tab count will be increased correctly."""
    assert ppl_data["exp_ppl_count"] == ppl_data["act_ppl_count"]
