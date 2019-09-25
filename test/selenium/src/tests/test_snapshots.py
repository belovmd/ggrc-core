# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Snapshot smoke tests."""
# pylint: disable=no-self-use
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-public-methods
import copy

import pytest

from lib import base, users
from lib.constants import messages, objects, object_states, roles
from lib.constants.element import Lhn, MappingStatusAttrs
from lib.entities.entity import Representation
from lib.factory import get_cls_webui_service, get_cls_rest_service
from lib.service import rest_facade, webui_facade, webui_service
from lib.utils.filter_utils import FilterUtils


class TestSnapshots(base.Test):
  """Tests for snapshot functionality."""

  @classmethod
  def check_ggrc_1773(cls, is_updateable_condition,
                      is_control_updateable_actual):
    """Particular check if issue in app exist or not according to GGRC-1773."""
    cls.check_xfail_or_fail(
        is_condition=is_updateable_condition,
        issue_msg="Issue in app GGRC-1773",
        assert_msg=("\nis_control_updateable:\n" +
                    messages.AssertionMessages.format_err_msg_equal(
                        True, is_control_updateable_actual)))

  @classmethod
  def get_controls_and_general_assert(cls, controls_ui_service,
                                      exp_controls, src_obj):
    """Get Controls objects' count and objects from Tree View and perform count
    and general assertion accordingly.
    """
    actual_controls_tab_count = (
        controls_ui_service.get_count_objs_from_tab(src_obj=src_obj))
    actual_controls = (
        controls_ui_service.get_list_objs_from_tree_view(src_obj=src_obj))
    assert len(exp_controls) == actual_controls_tab_count
    # 'actual_controls': created_at, updated_at, custom_attributes (None)
    cls.general_equal_assert(exp_controls, actual_controls,
                             *Representation.tree_view_attrs_to_exclude)

  @pytest.fixture(scope="function")
  def create_audit_and_update_first_of_two_original_controls(
      self, program, control_mapped_to_program, audit
  ):
    """Create Audit with snapshotable Control and update original Control under
    Program via REST API. After that create second Control and map it to
    Program via REST API.
    Preconditions:
    - Execution and return of fixture
      'create_audit_with_control_and_update_control'.
    - Second Control created via REST API.
    - Second Control mapped to Program via REST API.
    """
    return {
        "audit": audit,
        "program": program,
        "control": copy.deepcopy(control_mapped_to_program),
        "updated_control": rest_facade.update_object(
            control_mapped_to_program),
        "second_control": rest_facade.create_control_mapped_to_program(program)
    }

  @pytest.mark.smoke_tests
  def test_audit_contains_readonly_ver_of_control(
      self, program, control_mapped_to_program, audit, selenium
  ):
    """Check via UI that Audit contains read-only snapshotable Control.
    Preconditions:
    - Program, Control created via REST API.
    - Control mapped to Program via REST API.
    - Audit created under Program via REST API.
    """
    controls_ui_service = webui_service.ControlsService(selenium)
    actual_controls_tab_count = controls_ui_service.get_count_objs_from_tab(
        src_obj=audit)
    assert len([control_mapped_to_program]) == actual_controls_tab_count
    is_control_editable = controls_ui_service.is_obj_editable_via_info_panel(
        src_obj=audit, obj=control_mapped_to_program)
    assert is_control_editable is False

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      ("obj", "expected_control", "is_openable",
       "is_updateable"),
      [
          ("create_audit_with_control_and_update_control",
           "control", True, True),
          pytest.mark.skip(reason="CADs are not set in response")(
              ("create_audit_with_control_and_delete_control",
               "control", False, False)),
          ("create_audit_with_control_with_cas_and_update_control_cav",
           "control", True, True),
          ("create_audit_with_control_with_cas_and_delete_cas_for_controls",
           "control", True, False)],
      ids=["Audit contains snapshotable Control after updating Control",
           "Audit contains snapshotable Control after deleting Control",
           "Audit contains snapshotable Control "
           "after updating Control with CAs",
           "Audit contains snapshotable Control "
           "after deleting CAs for Controls"],
      indirect=["obj"])
  def test_destructive_audit_contains_snapshotable_control(
      self, login_as_creator, obj, expected_control, is_openable,
      is_updateable, selenium
  ):
    """Test snapshotable Control and check via UI that:
    - Audit contains snapshotable Control after updating Control.
    - Audit contains snapshotable Control after deleting Control.
    - Audit contains snapshotable Control after updating Control with CAs.
    - "Audit contains snapshotable Control after deleting CAs of Control.
    Preconditions:
      Execution and return of dynamic fixtures used REST API:
    - 'new_cas_for_controls_rest' *(due to Issue in app GGRC-2344)
    - 'create_audit_with_control_and_update_control'.
    - 'create_audit_with_control_and_delete_control'.
    - 'create_audit_with_control_with_cas_and_update_control_with_cas'.
    - 'create_audit_with_control_with_cas_and_delete_cas_for_controls'.
    This test is marked as destructive as deletion of GCA leads to
    changing of modified_by and updated_at of all objects with this GCA.
    Bug wasn't filed for this as deletion of GCA doesn't work currently
    and considered not critical (see GGRC-4055).
    """
    audit_with_one_control = obj
    audit = audit_with_one_control["audit"]
    expected_control = audit_with_one_control[expected_control].repr_ui()
    controls_ui_service = webui_service.ControlsService(selenium)
    actual_controls_tab_count = controls_ui_service.get_count_objs_from_tab(
        src_obj=audit)
    assert len([expected_control]) == actual_controls_tab_count
    is_control_updateable = (
        controls_ui_service.is_obj_updateble_via_info_panel(
            src_obj=audit, obj=expected_control))
    is_control_openable = controls_ui_service.is_obj_page_exist_via_info_panel(
        src_obj=audit, obj=expected_control)
    actual_control = controls_ui_service.get_list_objs_from_info_panels(
        src_obj=audit, objs=expected_control)
    assert is_control_updateable is is_updateable
    assert is_control_openable is is_openable
    # 'actual_control': created_at, updated_at, modified_by (None)
    self.general_equal_assert(
        expected_control, actual_control, "modified_by",
        *Representation.tree_view_attrs_to_exclude)

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      "obj",
      ["create_audit_with_control_and_update_control",
       "create_audit_with_control_with_cas_and_update_control_cav",
       pytest.param(
           "create_audit_with_control_with_cas_and_delete_cas_for_controls",
           marks=pytest.mark.xfail(
               reason="External user can remove only external relationships.")
       )
       ],
      ids=["Update snapshotable Control to latest ver "
           "after updating Control",
           "Update snapshotable Control to latest ver "
           "after updating Control with CAs",
           "Update snapshotable Control to latest ver "
           "after deleting CAs for Controls"],
      indirect=["obj"])
  def test_destructive_update_snapshotable_control_to_latest_ver(
      self, obj, selenium
  ):
    """Test snapshotable Control and check via UI that:
    - Update snapshotable Control to latest ver after updating Control.
    - Update snapshotable Control to latest ver
    after updating Control with CAs.
    - Update snapshotable Control to latest ver
    after deleting CAs of Control.
    Preconditions:
      Execution and return of dynamic fixtures used REST API:
    - 'new_cas_for_controls_rest' *(due to Issue in app GGRC-2344)
    - 'create_audit_with_control_and_update_control'.
    - 'create_audit_with_control_with_cas_and_update_control_with_cas'.
    - 'create_audit_with_control_with_cas_and_delete_cas_for_controls'.
    """
    audit_with_one_control = obj
    audit = audit_with_one_control["audit"]
    control = audit_with_one_control["control"]
    expected_control = audit_with_one_control["updated_control"].repr_ui()
    controls_ui_service = webui_service.ControlsService(selenium)
    actual_controls_tab_count = controls_ui_service.get_count_objs_from_tab(
        src_obj=audit)
    assert len([expected_control]) == actual_controls_tab_count
    controls_ui_service.update_obj_ver_via_info_panel(
        src_obj=audit, obj=control)
    is_control_updateable = (
        controls_ui_service.is_obj_updateble_via_info_panel(
            src_obj=audit, obj=expected_control))
    is_control_openable = controls_ui_service.is_obj_page_exist_via_info_panel(
        src_obj=audit, obj=expected_control)
    actual_control = controls_ui_service.get_list_objs_from_info_panels(
        src_obj=audit, objs=expected_control)
    assert is_control_updateable is False
    assert is_control_openable is True
    # 'actual_control': created_at, updated_at, modified_by (None)
    self.general_equal_assert(
        expected_control, actual_control,
        "created_at", "updated_at", "modified_by",
        *Representation.tree_view_attrs_to_exclude)

  @pytest.mark.smoke_tests
  def test_mapped_to_program_controls_does_not_added_to_existing_audit(
      self, create_audit_and_update_first_of_two_original_controls, selenium
  ):
    """Check via UI that Audit contains snapshotable Control that equal to
    original Control does not contain Control that was mapped to
    Program after Audit creation.
    Preconditions:
    - Execution and return of fixture
      'create_audit_and_update_first_of_two_original_controls'.
    """
    audit_with_two_controls = (
        create_audit_and_update_first_of_two_original_controls)
    audit = audit_with_two_controls["audit"]
    expected_control = audit_with_two_controls["control"].repr_ui()
    controls_ui_service = webui_service.ControlsService(selenium)
    actual_controls_tab_count = controls_ui_service.get_count_objs_from_tab(
        src_obj=audit)
    assert len([expected_control]) == actual_controls_tab_count
    actual_controls = controls_ui_service.get_list_objs_from_tree_view(
        src_obj=audit)
    # 'actual_controls': created_at, updated_at, custom_attributes (None)
    self.general_equal_assert(
        [expected_control], actual_controls,
        *Representation.tree_view_attrs_to_exclude)

  @pytest.mark.smoke_tests
  def test_bulk_update_audit_objects_to_latest_ver(
      self, create_audit_and_update_first_of_two_original_controls, selenium
  ):
    """Check via UI that Audit contains snapshotable Controls that up-to-date
    with their actual states after bulk updated audit objects
    to latest version.
    Preconditions:
    - Execution and return of fixture
      'create_audit_and_update_first_of_two_original_controls'.
    """
    audit_with_two_controls = (
        create_audit_and_update_first_of_two_original_controls)
    audit = audit_with_two_controls["audit"]
    expected_controls = [expected_control.repr_ui() for expected_control
                         in [audit_with_two_controls["updated_control"],
                             audit_with_two_controls["second_control"]]]
    (webui_service.AuditsService(selenium).
     bulk_update_via_info_page(audit_obj=audit))
    controls_ui_service = webui_service.ControlsService(selenium)
    actual_controls_tab_count = controls_ui_service.get_count_objs_from_tab(
        src_obj=audit)
    assert len(expected_controls) == actual_controls_tab_count
    actual_controls = controls_ui_service.get_list_objs_from_tree_view(
        src_obj=audit)
    # 'actual_controls': created_at, updated_at, custom_attributes (None)
    self.general_equal_assert(
        sorted(expected_controls), sorted(actual_controls),
        *Representation.tree_view_attrs_to_exclude)

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize("tab_name", [Lhn.ALL_OBJS, Lhn.MY_OBJS])
  @pytest.mark.parametrize(
      "version_of_ctrl, is_found",
      [("control", False), ("updated_control", True)],
      ids=["Snapshoted version is not found",
           "Actual snapshotable control is presented"])
  def test_destructive_search_snapshots_in_lhn(
      self, create_audit_with_control_and_update_control, version_of_ctrl,
      is_found, tab_name, lhn_menu
  ):
    """Check via UI that LHN search not looking for snapshots."""
    audit_with_one_control = create_audit_with_control_and_update_control
    lhn_menu.select_tab(tab_name)
    expected_control_title = audit_with_one_control[version_of_ctrl].title
    lhn_menu.filter_query(expected_control_title)
    actual_controls = (lhn_menu.select_controls_or_objectives().
                       select_controls().members_visible)
    actual_controls_titles = [act_ctrl.text for act_ctrl in actual_controls]
    assert is_found is (expected_control_title in actual_controls_titles), (
        messages.AssertionMessages.format_err_msg_contains(
            expected_control_title, actual_controls_titles))

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      "version_of_ctrl, is_found",
      [("control", True), ("updated_control", False)],
      ids=["Snapshoted version is filtered",
           "Actual snapshotable Control is not filtered"])
  def test_filter_of_snapshotable_control(
      self, create_audit_with_control_and_update_control, version_of_ctrl,
      is_found, selenium
  ):
    """Check via UI that filtering work for snapshoted version of Control only,
    filtering by actual values returns no items in scope of Audit page.
    """
    audit_with_one_control = create_audit_with_control_and_update_control
    audit = audit_with_one_control["audit"]
    expected_control = audit_with_one_control[version_of_ctrl].repr_ui()
    filter_exp = FilterUtils.get_filter_exp_by_title(expected_control.title)
    actual_controls = (webui_service.ControlsService(selenium).
                       filter_and_get_list_objs_from_tree_view(
                           src_obj=audit, filter_exp=filter_exp))
    # 'actual_controls': created_at, updated_at, custom_attributes (None)
    expected_controls, actual_controls = Representation.extract_objs(
        [expected_control], actual_controls,
        *Representation.tree_view_attrs_to_exclude)
    expected_control = expected_controls[0]
    assert is_found is (expected_control in actual_controls), (
        messages.AssertionMessages.format_err_msg_contains(
            expected_control, actual_controls))

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      "control_for_mapper, control_for_tree_view, obj, "
      "expected_map_statuses, expected_is_found",
      [pytest.param(
          "control", "control", None, (True, True),
          False, marks=pytest.mark.xfail(reason="GGRC-6523")),
       pytest.param(
           "updated_control", "control", None, (True, True),
           True, marks=pytest.mark.xfail(reason="GGRC-6523")),
       ("control", None, "assessment",
        (False, False), True),
       ("updated_control", None, "assessment",
        (False, False), False),
       ("control", None, "issue_mapped_to_audit",
        (False, False), False),
       ("updated_control", None, "issue_mapped_to_audit",
        (False, False), True)],
      ids=["Mapper: snapshoted version is not found for Audit "
           "which based on Program w' updated Control; "
           "Tree View: snapshotable Control is mapped to Audit.",
           "Mapper: Actual snapshotable Control is found and mapped to new "
           "Audit which based on Program w' updated Control; "
           "Tree View: snapshotable Control is mapped to new Audit.",
           "Mapper: Snapshoted version is found for Assessment "
           "which created in Audit scope; "
           "Tree View: Assessment doesn't contain Controls.",
           "Mapper: Actual snapshotable Control is not found for Assessment "
           "which created in Audit scope; "
           "Tree View: Assessment doesn't contain Controls.",
           "Mapper: Snapshoted version is not found for standalone Issue "
           "which mapped to Audit; "
           "Tree View: Issue doesn't contain Controls.",
           "Mapper: Actual version of Control found for standalone Issue "
           "which mapped to Audit; "
           "Tree View: Issue doesn't contain Controls."],
      indirect=["obj"])
  def test_destructive_search_unified_mapper_and_check_mapping(
      self, create_audit_with_control_and_update_control, control_for_mapper,
      control_for_tree_view, obj,
      expected_map_statuses, expected_is_found, selenium
  ):
    """Check searching of shapshotable and snapshoted objects via Unified
    Mapper modal and check their correct mapping.
    """
    audit_with_one_control = create_audit_with_control_and_update_control
    source_obj = (
        audit_with_one_control["audit"] if not obj else
        obj)
    expected_control_from_mapper = (
        audit_with_one_control[control_for_mapper].repr_ui())
    expected_control_from_tree_view = (
        (expected_control_from_mapper
         if control_for_mapper == control_for_tree_view else
         audit_with_one_control[control_for_tree_view].repr_ui())
        if control_for_tree_view else None)
    expected_map_status = MappingStatusAttrs(
        expected_control_from_mapper.title, *expected_map_statuses)
    controls_ui_service = webui_service.ControlsService(selenium)
    actual_controls_from_mapper, actual_map_status = (
        controls_ui_service.get_list_objs_from_mapper(
            src_obj=source_obj, dest_objs=[expected_control_from_mapper]))
    actual_controls_from_tree_view = (
        controls_ui_service.get_list_objs_from_tree_view(src_obj=source_obj))
    # 'actual_controls': created_at, updated_at, custom_attributes (None)
    expected_controls_from_mapper, actual_controls_from_mapper = (
        Representation.extract_objs(
            [expected_control_from_mapper], actual_controls_from_mapper,
            *Representation.tree_view_attrs_to_exclude))
    expected_controls_from_tree_view = []
    if expected_control_from_tree_view:
      expected_controls_from_tree_view, actual_controls_from_tree_view = (
          Representation.extract_objs(
              [expected_control_from_tree_view],
              actual_controls_from_tree_view,
              *Representation.tree_view_attrs_to_exclude))
    assert (expected_is_found
            is (expected_controls_from_mapper[0] in
                actual_controls_from_mapper)
            is (expected_map_status in actual_map_status)) == (
        (expected_controls_from_tree_view[0] in actual_controls_from_tree_view)
        if expected_control_from_tree_view else
        expected_controls_from_tree_view ==
        actual_controls_from_tree_view), (
        messages.AssertionMessages.format_err_msg_equal(
            messages.AssertionMessages.format_err_msg_contains(
                expected_controls_from_mapper[0], actual_controls_from_mapper),
            messages.AssertionMessages.format_err_msg_contains(
                expected_controls_from_tree_view[0],
                actual_controls_from_tree_view)
            if expected_control_from_tree_view else
            messages.AssertionMessages.format_err_msg_equal(
                expected_controls_from_tree_view,
                actual_controls_from_tree_view)))

  @pytest.mark.smoke_tests
  def test_destructive_mapping_control_to_existing_audit(
      self, program, audit, control, selenium
  ):
    """Check if Control can be mapped to existing Audit and mapping
    between Control and Program of this Audit automatically created.
    Preconditions:
    - Audit and program, and different control created via REST API
    """
    # 'actual_controls': created_at, updated_at, custom_attributes (None)
    expected_control = Representation.extract_objs_wo_excluded_attrs(
        [control.repr_ui()],
        *Representation.tree_view_attrs_to_exclude)[0]
    controls_ui_service = webui_service.ControlsService(selenium)
    controls_ui_service.map_objs_via_tree_view(
        src_obj=audit, dest_objs=[control])
    actual_controls_count_in_tab_audit = (
        controls_ui_service.get_count_objs_from_tab(src_obj=audit))
    actual_controls_in_audit = (
        controls_ui_service.get_list_objs_from_tree_view(
            src_obj=audit))
    actual_controls_count_in_tab_program = (
        controls_ui_service.get_count_objs_from_tab(src_obj=program))
    actual_controls_in_program = (
        controls_ui_service.get_list_objs_from_tree_view(
            src_obj=program))
    assert (len([expected_control]) == actual_controls_count_in_tab_audit ==
            actual_controls_count_in_tab_program)
    assert ([expected_control] == actual_controls_in_audit ==
            actual_controls_in_program), (
        messages.AssertionMessages.format_err_msg_equal(
            messages.AssertionMessages.format_err_msg_equal(
                [expected_control], actual_controls_in_audit),
            messages.AssertionMessages.format_err_msg_equal(
                [expected_control], actual_controls_in_program)))

  @pytest.mark.smoke_tests
  def test_snapshot_cannot_be_unmapped_from_audit(
      self, program, control_mapped_to_program, audit, selenium
  ):
    """Check Snapshot cannot be unmapped from audit using "Unmap" button on
    info panel.
    Check that snapshot cannot be mapped from tree-view using "Map to this
    object" button.
    Preconditions:
    - Audit with mapped Control Snapshot created via REST API
    """
    controls_ui_service = webui_service.ControlsService(selenium)
    is_mappable_on_tree_view_item = (
        controls_ui_service.is_obj_mappable_via_tree_view(
            audit, control_mapped_to_program))
    is_unmappable_on_info_panel = (
        controls_ui_service.
        is_obj_unmappable_via_info_panel(
            src_obj=audit, obj=control_mapped_to_program))
    assert (False
            is is_mappable_on_tree_view_item is is_unmappable_on_info_panel)

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      "is_via_tw_map_btn_not_item, expected_snapshoted_control, obj",
      [(True, "control", "assessment_w_mapped_control_w_issue"),
       (True, "control", "assessment_wo_mapped_control_wo_issue"),
       (False, "control", "assessment_w_mapped_control_w_issue"),
       (False, "control", "assessment_wo_mapped_control_wo_issue")],
      ids=["Via Tree View MAP btn (map snapshoted Control to Assessment)",
           "Via Tree View MAP btn (map snapshoted Control to Issue using "
           "Assessment with mapped snapshoted Control)",
           "Via Tree View item (map snapshoted Control to Assessment)",
           "Via Tree View item (map snapshoted Control to Issue using "
           "Assessment with mapped snapshoted Control)"],
      indirect=["obj"])
  def test_destructive_mapping_of_objects_to_snapshots(
      self, create_audit_with_control_and_update_control,
      is_via_tw_map_btn_not_item, expected_snapshoted_control, obj, selenium
  ):
    """Check mapping of objects to Control's snapshots via UI using Unified
    Mapper functionality (Tree View's 'MAP' button and item):
    - Assessments: using Audit's scope;
    - Issues: using auto-mapping in Assessment's with mapped snapshoted object
              scope.
    """
    audit_with_one_control = create_audit_with_control_and_update_control
    is_issue_flow = obj["issue"] is not None
    expected_control = (
        audit_with_one_control[expected_snapshoted_control].repr_ui())
    source_obj_for_map, destination_obj_for_map = (
        (obj["assessment"], obj["issue"]) if is_issue_flow else
        (obj["assessment"], expected_control))
    obj_for_map = (destination_obj_for_map if is_via_tw_map_btn_not_item else
                   source_obj_for_map)
    objs_ui_service = (
        get_cls_webui_service(objects.get_plural(obj_for_map.type))(selenium))
    ui_action = ("map_objs_via_tree_view" if is_via_tw_map_btn_not_item else
                 "map_objs_via_tree_view_item")
    getattr(objs_ui_service, ui_action)(
        src_obj=(source_obj_for_map if is_via_tw_map_btn_not_item else
                 audit_with_one_control["audit"]),
        dest_objs=[destination_obj_for_map])
    source_obj_for_controls = (obj["issue"] if is_issue_flow else
                               obj["assessment"])
    # check snapshoted Controls
    controls_ui_service = webui_service.ControlsService(
        selenium, is_versions_widget=is_issue_flow)
    self.get_controls_and_general_assert(
        controls_ui_service, [expected_control], source_obj_for_controls)
    # check original Controls when Issue is source object
    if is_issue_flow:
      expected_control = []
      controls_ui_service = webui_service.ControlsService(selenium)
      self.get_controls_and_general_assert(
          controls_ui_service, expected_control, source_obj_for_controls)

  @pytest.fixture()
  def ge_user(self):
    """Create GE user and set him as current."""
    user = rest_facade.create_user_with_role(roles.EDITOR)
    users.set_current_user(user)
    return user

  @pytest.mark.smoke_tests
  @pytest.mark.xfail(raises=IOError)
  @pytest.mark.parametrize(
      "obj",
      [pytest.param(None),
       pytest.param(
          "assessment_w_mapped_control_w_issue",
          marks=pytest.mark.skip(
              reason="Issue has another mapping flow to control")),
       pytest.param("assessment_w_mapped_control_wo_issue")],
      ids=["Export of snapshoted Control from Audit's Info Page "
           "via mapped Controls' Tree View",
           "Export of snapshoted Control from Issue's Info Page "
           "via mapped Controls' Tree View",
           "Export of snapshoted Control from Assessment's Info Page "
           "via mapped Controls' Tree View"],
      indirect=True)
  def test_export_of_snapshoted_control_from_src_objs_pages_via_tree_view(
      self, ge_user, create_tmp_dir,
      create_audit_with_control_and_update_control, obj, selenium
  ):
    """Check if snapshoted Control can be exported from (Audit's, Issue's,
    Assessment's) Info Page via mapped Controls's Tree View.
    Preconditions:
    - Execution and return of fixtures:
      - 'create_tmp_dir';
      - 'create_audit_and_update_first_of_two_original_controls'.
    Test parameters:
    - 'dynamic_objects';
    - 'dynamic_relationships'.
    """
    audit_with_one_control = create_audit_with_control_and_update_control
    is_issue_flow = obj is not None and obj["issue"] is not None
    dynamic_objects = (
        (obj["issue"] if is_issue_flow else obj["assessment"]) if obj
        else audit_with_one_control["audit"])
    expected_control = audit_with_one_control["control"].repr_ui()
    actual_controls = webui_facade.export_objects(
        path_to_export_dir=create_tmp_dir,
        obj_type=audit_with_one_control["control"].type,
        src_obj=dynamic_objects,
        is_versions_widget=is_issue_flow)
    # 'actual_controls': created_at, updated_at,
    #                    custom_attributes (GGRC-2344) (None)
    self.general_equal_assert(
        [expected_control], actual_controls,
        *Representation.tree_view_attrs_to_exclude)

  @pytest.fixture()
  def assessment_wo_mapped_control_wo_issue(self, assessment):
    """Create assessment without mapped control without issue."""
    return {"assessment": assessment,
            "issue": None,
            "expected_state": object_states.NOT_STARTED}

  @pytest.fixture()
  def assessment_w_mapped_control_wo_issue(
      self, create_audit_with_control_and_update_control, assessment
  ):
    """Create assessment with mapped control without issue."""
    rest_facade.map_to_snapshot(
        assessment, create_audit_with_control_and_update_control["control"],
        create_audit_with_control_and_update_control["audit"])
    return {"assessment": assessment,
            "issue": None,
            "expected_state": object_states.DRAFT}

  @pytest.fixture()
  def assessment_w_mapped_control_w_issue(
      self, create_audit_with_control_and_update_control, assessment,
      issue_mapped_to_audit
  ):
    """Create assessment with mapped control with issue."""
    rest_facade.map_to_snapshot(
        assessment, create_audit_with_control_and_update_control["control"],
        create_audit_with_control_and_update_control["audit"])
    return {"assessment": assessment,
            "issue": issue_mapped_to_audit,
            "expected_state": object_states.DRAFT}

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      "obj",
      ["assessment_wo_mapped_control_wo_issue",
       "assessment_w_mapped_control_w_issue"],
      ids=["Mapping snapshot of Control to Assessment",
           "Mapping Assessment with mapped snapshot of Control to Issue"],
      indirect=["obj"]
  )
  def test_destructive_asmt_and_issue_mapped_to_origin_control(
      self, create_audit_with_control_and_update_control, assessment,
      obj, selenium
  ):
    """
    Check Assessment, Issue was mapped to origin Control after mapping:
    - snapshot of Control to Assessment;
    - Assessment with mapped snapshot of Control to Issue.
    """
    is_issue_flow = obj["issue"] is not None
    origin_control = create_audit_with_control_and_update_control[
        "updated_control"]
    snapshoted_control = create_audit_with_control_and_update_control[
        "control"]
    expected_obj = (
        obj["issue"] if is_issue_flow
        else obj["assessment"]).repr_ui().update_attrs(
        status=obj["expected_state"])
    ui_mapping_service, src_obj, dest_objs = (
        (webui_service.IssuesService(selenium),
         obj["assessment"], [obj["issue"]]) if is_issue_flow else
        (webui_service.ControlsService(selenium), expected_obj,
         [snapshoted_control]))
    ui_mapping_service.map_objs_via_tree_view(
        src_obj=src_obj, dest_objs=dest_objs)
    actual_objs = (get_cls_webui_service(
        objects.get_plural(expected_obj.type))(selenium).
        get_list_objs_from_tree_view(src_obj=origin_control))
    # 'actual_controls': created_at, updated_at, custom_attributes, audit
    #                    assessment_type, modified_by (None)
    exclude_attrs = (Representation.tree_view_attrs_to_exclude +
                     ("audit", "assessment_type", "modified_by"))
    if is_issue_flow:
      exclude_attrs += ("objects_under_assessment", )
      self.general_equal_assert([], actual_objs, *exclude_attrs)
    else:
      self.general_equal_assert([expected_obj], actual_objs, *exclude_attrs)

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      "obj, object_state",
      [("assessment", object_states.NOT_STARTED),
       ("assessment", object_states.IN_PROGRESS),
       ("assessment", object_states.READY_FOR_REVIEW),
       ("assessment", object_states.COMPLETED),
       pytest.mark.xfail(reason="Issue GGRC-2817", strict=True)
          (("issue_mapped_to_audit", object_states.DRAFT))],
      indirect=["obj"])
  def test_destructive_snapshot_can_be_unmapped_from_assessment_or_issue(
      self, create_audit_with_control_and_update_control, obj,
      selenium, object_state
  ):
    """Check Snapshot can be unmapped from assessment using "Unmap" button on
    info panel.
    Test parameters:
      "Checking assessment"
      "Checking issue"
    Steps:
      - Create assessment
      - Map snapshoted control with assessment
      - Unmap snapshot from assessment
      - Make sure that assessment has no any mapped snapshots
    """
    # pylint: disable=misplaced-comparison-constant
    audit_with_one_control = create_audit_with_control_and_update_control
    control = audit_with_one_control["control"].repr_ui()
    audit = audit_with_one_control["audit"]
    existing_obj = obj
    existing_obj_name = objects.get_plural(existing_obj.type)
    (get_cls_webui_service(existing_obj_name)(selenium).
        map_objs_via_tree_view_item(src_obj=audit, dest_objs=[control]))
    controls_ui_service = webui_service.ControlsService(selenium)
    (get_cls_rest_service(existing_obj_name)().
        update_obj(obj=existing_obj, status=object_state))
    controls_ui_service.unmap_via_info_panel(existing_obj, control)
    actual_controls_count = controls_ui_service.get_count_objs_from_tab(
        src_obj=existing_obj)
    actual_controls = (controls_ui_service.get_list_objs_from_tree_view(
        src_obj=existing_obj))
    assert 0 == actual_controls_count
    assert [] == actual_controls

  @pytest.mark.smoke_tests
  @pytest.mark.parametrize(
      "obj",
      ["assessment", "issue"],
      ids=["All Snapshotable objects, Issues to Assessment",
           "All Snapshotable objects, Issues, Programs, Projects to Issue"],
      indirect=True)
  def test_availability_mapping_of_objects_via_mapper_and_add_widget(
      self, create_audit_with_control_and_update_control, obj, selenium
  ):
    """Check availability mapping of objects to Assessment and Issue via UI
    using Unified Mapper functionality and AddWidget button on Horizontal
    Nav Bar.

    Steps:
      - Get list of available objects from Unified Mapper;
      - Get list of available objects from HNB;
      - Compare their with constant of expected objects accordingly.
    """
    expected_objs_names_from_mapper = (
        objects.ALL_SNAPSHOTABLE_OBJS + (objects.ISSUES, ))
    if obj.type == objects.get_obj_type(objects.ISSUES):
      rest_facade.map_objs(
          create_audit_with_control_and_update_control["audit"], obj)
      expected_objs_names_from_mapper = expected_objs_names_from_mapper + (
          objects.PROGRAMS, objects.DOCUMENTS)
    expected_objs_names_from_add_widget = expected_objs_names_from_mapper
    expected_objs_types_from_mapper = sorted(
        objects.get_normal_form(obj_name)
        for obj_name in expected_objs_names_from_mapper)
    expected_objs_types_from_add_widget = sorted(
        objects.get_normal_form(obj_name)
        for obj_name in expected_objs_names_from_add_widget)
    mapped_audit = create_audit_with_control_and_update_control["audit"]
    obj_ui_service = get_cls_webui_service(
        objects.get_plural(obj.type))(selenium)
    actual_objs_types_from_mapper = (
        obj_ui_service.get_objs_available_to_map_via_mapper(
            src_obj=mapped_audit))
    actual_objs_types_from_add_widget = (
        obj_ui_service.get_objs_available_to_map_via_add_widget(
            src_obj=obj))
    assert (expected_objs_types_from_mapper ==
            actual_objs_types_from_mapper), (
        messages.AssertionMessages.format_err_msg_equal(
            expected_objs_types_from_mapper, actual_objs_types_from_mapper))
    assert (expected_objs_types_from_add_widget ==
            actual_objs_types_from_add_widget), (
        messages.AssertionMessages.format_err_msg_equal(
            expected_objs_types_from_add_widget,
            actual_objs_types_from_add_widget))

  def test_create_audit_with_manually_mapping_snapshots(
      self, program, control_mapped_to_program, selenium
  ):
    """Check that newly created audit with manually mapping snapshots doesn't
    have snapshots.
    Steps:
    - Create program via rest
    - Create control mapped to program via rest
    - Create audit with checked "Manually map snapshots"
    - Check that newly created audit doesn't have snapshots"""
    actual_count = webui_facade.get_controls_snapshots_count(
        selenium, webui_facade.create_audit(
            selenium, program, manual_snapshots=True))
    assert actual_count == {"controls_tab_count": 0, "controls_count": 0}

  @pytest.mark.parametrize(
      'obj_mapped_to_control',
      ["requirement_mapped_to_program", "regulation_mapped_to_program"],
      indirect=True)
  @pytest.mark.parametrize(
      'obj',
      ["audit_w_manually_mapped_control_and_obj_mapped_to_control", "audit"],
      indirect=True)
  def test_related_snapshots_in_control_snapshot_info_modal(
      self, control_mapped_to_program, obj_mapped_to_control, obj,
      asmt_w_control_snapshot, selenium
  ):
    """Check that snapshot which is related to control snapshot is shown in
    'SHOW RELATED' section of control snapshot info modal.
    Preconditions:
    - Program with mapped Control
    - Audit with manually/auto mapped Control snapshot
    - Regulation/Requirement mapped to the Program and Control
    - Regulation/Requirement snapshot mapped to Audit
    - Assessment for Audit with a Control snapshot
    """
    related_objs = (webui_service.AssessmentsService(selenium)
                    .get_snapshots_which_are_related_to_control_snapshot(
        asmt_w_control_snapshot, control_mapped_to_program,
        obj_mapped_to_control.type))
    self.general_contain_assert(
        obj_mapped_to_control, related_objs, 'status', 'modified_by',
        'slug', *obj_mapped_to_control.tree_view_attrs_to_exclude)
