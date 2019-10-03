# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Base classes."""
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-lines

import random
import re

import pytest
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common import keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote import webelement

from lib import constants, exception, mixin, environment, browsers
from lib.constants import messages
from lib.decorator import lazy_property
from lib.entities import entity
from lib.utils import selenium_utils, help_utils


class InstanceRepresentation(object):
  def __repr__(self):
    return str(
        {key: value for key, value in self.__dict__.items()
         if "__" not in key})


class CustomDriver(webdriver.Chrome):
  """Extension to web driver."""

  def find_elements_by_visible_locator(self, locator):
    """Sometimes we have to find in list of elements only that one that is
    visible to user.
    Args: locator (tuple)
    Return: selenium.webdriver.remote.webelement.WebElement
    Raises: exception.ElementNotFound
    """
    # pylint: disable=invalid-name
    elements = self.find_elements(*locator)
    for element in elements:
      if element.is_displayed():
        return element
    raise exception.ElementNotFound(locator)


class Test(InstanceRepresentation):
  """Base test class."""
  __metaclass__ = mixin.MetaTestDecorator

  @staticmethod
  def general_equal_assert(expected_objs, actual_objs, *exclude_attrs):
    """Perform general equal assert for deepcopy converted to list expected and
    actual objects according to '*exclude_attrs' tuple of excluding attributes'
    names (compare objects' collections w/ attributes' values set to None).
    """
    expected_objs_wo_excluded_attrs, actual_objs_wo_excluded_attrs = (
        entity.Representation.extract_objs(
            help_utils.convert_to_list(expected_objs),
            help_utils.convert_to_list(actual_objs), *exclude_attrs))
    assert (expected_objs_wo_excluded_attrs ==
            actual_objs_wo_excluded_attrs), (
        messages.AssertionMessages.format_err_msg_equal(
            expected_objs_wo_excluded_attrs, actual_objs_wo_excluded_attrs))

  @staticmethod
  def general_contain_assert(expected_obj, actual_objs, *exclude_attrs):
    """Perform general contain assert for deepcopy converted expected object
    and actual objects according to '*exclude_attrs' tuple of excluding
    attributes' names
    (compare objects' collections w/ attributes' values set to None).
    """
    expected_obj_wo_excluded_attrs = (
        entity.Representation.extract_objs_wo_excluded_attrs(
            help_utils.convert_to_list(expected_obj), *exclude_attrs)[0])
    actual_objs_wo_excluded_attrs = (
        entity.Representation.extract_objs_wo_excluded_attrs(
            help_utils.convert_to_list(actual_objs), *exclude_attrs))
    assert (expected_obj_wo_excluded_attrs in
            actual_objs_wo_excluded_attrs), (
        messages.AssertionMessages.format_err_msg_contains(
            expected_obj_wo_excluded_attrs, actual_objs_wo_excluded_attrs))

  @staticmethod
  def xfail_equal_assert(expected_objs, actual_objs, issue_msg,
                         *exclude_attrs):
    """Perform xfail equal assert based on deepcopy converted to list expected
    and actual objects according to 'issue_msg' string and '*exclude_attrs'
    tuple of excluding attributes' names (compare simple' collections based on
    excluding attributes (attributes' names and values, if 'False' then rise
    pytest's xfail, else pytest's fail.
    """
    expected_excluded_attrs, actual_excluded_attrs = (
        entity.Representation.extract_simple_collections(
            help_utils.convert_to_list(expected_objs),
            help_utils.convert_to_list(actual_objs), *exclude_attrs))
    assert_msg = messages.AssertionMessages.format_err_msg_equal(
        expected_excluded_attrs, actual_excluded_attrs)
    is_list_excluded_attrs_equal = (
        entity.Representation.is_list_of_attrs_equal(
            expected_excluded_attrs, actual_excluded_attrs))
    Test.check_xfail_or_fail(
        is_condition=is_list_excluded_attrs_equal, issue_msg=issue_msg,
        assert_msg=assert_msg)

  @staticmethod
  def check_xfail_or_fail(is_condition, issue_msg, assert_msg):
    """Check according to 'is_condition' if test test was xfailed or failed for
    some reason which corresponds to 'issue_msg' and 'assert_msg' messages.
    If 'is_condition' is False then xfail, if True then fail.
    """
    if not is_condition:
      pytest.xfail(reason=issue_msg + assert_msg)
    else:
      pytest.fail(
          msg=issue_msg + " was fixed or changed behavior" + assert_msg)


class TestUtil(InstanceRepresentation):
  """Abstract class for all test util classes."""


class Element(InstanceRepresentation):
  """Element class represents primitives in models. Initializing by 'driver'
  Web driver and 'locator_or_element' (CSS selector (tuple) or Web element
  (instance of webelement.WebElement).
  """

  def __init__(self, driver, locator_or_element):
    super(Element, self).__init__()
    self._driver = driver
    self._browser = browsers.get_browser()
    self.locator_or_element = locator_or_element
    self.element = self.get_element()
    self.text = self.element.text

  def _get_visible_element(self):
    """Get element: if self object 'locator_or_element' is already Web element
    then try wait until it will be visible else try to find visible Web element
    using selenium utils method 'get_when_visible'.
    Return: selenium.webdriver.remote.webelement.WebElement
    """
    if isinstance(self.locator_or_element, webelement.WebElement):
      selenium_utils.wait_until_condition(
          self._driver, lambda x: self.locator_or_element.is_displayed())
      return self.locator_or_element
    return selenium_utils.get_when_visible(
        self._driver, self.locator_or_element)

  def get_element(self):
    """Get element if it is displayed."""
    return self._get_visible_element()

  def click(self):
    """Click on element."""
    self.element.click()

  def click_via_js(self):
    """Click on element using JS."""
    selenium_utils.click_via_js(self._driver, self.element)


class Label(Element):
  """Generic label."""


class TextInputField(Element):
  """Common class for representation of Text input."""

  def enter_text(self, text):
    """Clear text from element and enter new text."""
    self.element.clear()
    self.element.send_keys(text)
    self.text = text

  def paste_from_clipboard(self, element):
    """
    Paste value from clipboard into text input element.
    Details:
    We want to update value of this element after pasting. In order to
    do that, we click on another element.
    Args: element (Element)
    """
    self.element.clear()
    self.element.send_keys(keys.Keys.CONTROL, 'v')
    element.click()
    element = self._driver.find_element(*self.locator_or_element)
    self.text = element.get_attribute("value")

  def send_enter_key(self):
    """Send ENTER key."""
    self.element.send_keys(keys.Keys.ENTER)


class RichTextInputField(TextInputField):
  """Generic model for rich text input field."""


class Iframe(Element):
  """Iframe element methods."""

  def find_iframe_and_enter_data(self, text):
    """
    Args: text (basestring): string want to enter
    """
    self._driver.switch_to.frame(self.element)
    element = self._driver.find_element_by_tag_name("body")
    element.clear()
    element.send_keys(text)
    self._driver.switch_to.default_content()
    self.text = text


class DatePicker(Element):
  """Date picker element methods."""

  def __init__(self, driver, date_picker_locator, field_locator):
    """
    Args:
    date_picker_locator (tuple)
    field_locator (tuple): locator of field we have to click on to
    activate date picker
    """
    super(DatePicker, self).__init__(driver, field_locator)
    self._locator_datepicker = date_picker_locator
    self._element_datepicker = None

  def get_day_els_current_month(self):
    """Get day elements for current month.
    Return: list of selenium.webdriver.remote.webelement.WebElement
    """
    self.element.click()
    elements = self._driver.find_elements(*self._locator_datepicker)
    return elements

  def select_day_in_current_month(self, day):
    """Select day - sequential element from date picker. Days go from 0 to
    28,29 or 30, depending on current month. Since we're selecting an element
    from list, we can pass e.g. -1 to select last day in month.
    Args: day (int)
    """
    elements = self.get_day_els_current_month()
    elements[day].click()
    # wait for fadeout in case we're above some other element
    selenium_utils.get_when_invisible(self._driver, self._locator_datepicker)
    self.text = self.element.get_attribute("value")

  def select_rand_day_in_curr_month(self):
    """Select random day in current month."""
    random.choice(self.get_day_els_current_month()).click()
    # wait for fadeout in case we're above some other element
    selenium_utils.get_when_invisible(self._driver, self._locator_datepicker)
    self.text = self.element.get_attribute("value")

  def select_month_end(self):
    """Select last day of current month."""
    self.select_day_in_current_month(-1)

  def select_month_start(self):
    """Select first day of current month."""
    self.select_day_in_current_month(0)


class Button(Element):
  """Generic button element."""


class Checkbox(Element):
  """Generic checkbox element."""

  def check(self):
    """Select checkbox."""
    if not self.element.is_checked():
      self.element.click()

  def uncheck(self):
    """Unselect checkbox."""
    if self.element.is_checked():
      self.element.click()

  def is_checked_via_js(self):
    """Check if checkbox is checked using JS."""
    return selenium_utils.is_element_checked(self._driver, self.element)


class Toggle(Element):
  """Generic toggle element.
 Note that special function is used for detecting if element is active
 which may not work on an arbitrary element.
 """

  def __init__(self, driver, locator_or_element, is_active_attr_val="active"):
    super(Toggle, self).__init__(driver, locator_or_element)
    self.is_activated = selenium_utils.is_value_in_attr(
        self.element, value=is_active_attr_val)

  def toggle(self, on_el=True):
    """Click on element based on is_active status and "on" arg.
    Args: on_el (bool)
    """
    if on_el and not self.is_activated:
      self.click_via_js()
      self.is_activated = True
    elif not on_el and self.is_activated:
      self.click_via_js()
      self.is_activated = False


class Tab(Element):
  """Generic element representing tab."""
  def __init__(self, driver, locator_or_element, is_activated=True):
    super(Tab, self).__init__(driver, locator_or_element)
    self.is_activated = is_activated

  def click(self):
    """When clicking on tab to first make sure it's clickable i.e.
    that this element will receive click."""
    self.element.click()
    self.is_activated = True


class Dropdown(Element):
  """Generic dropdown."""


class DropdownStatic(Element):
  """Dropdown with predefined static elements."""

  def find_options(self):
    """Find all options of dropdown by options locator"""
    return self.element.find_elements(
        *constants.locator.CommonDropdownMenu.DROPDOWN_OPTIONS)

  def select(self, member_name):
    """Selects dropdown element based on dropdown element value."""
    self._select_by("value", member_name)

  def select_by_label(self, label):
    """Selects dropdown element based on dropdown element label."""
    self._select_by("label", label)

  def _select_by(self, by_attr, val):
    """Selects dropdown element based on dropdown attr"""
    for element in self.find_options():
      if element.get_attribute(by_attr) == val:
        element.click()
        break
    else:
      exception.ElementNotFound(val)


class DropdownAutocomplete(Element):
  """Dropdown with autocomplete elements."""

  def select(self, value_name):
    """Selects autocomplete dropdown element based on element value."""
    self.element.click()
    selenium_utils.get_when_visible(self._driver, (
        By.CSS_SELECTOR, "div[value={}]".format(
            value_name))).click()


class WithBrowser(InstanceRepresentation):
  """Class to contain a driver and browser instances"""

  def __init__(self, _driver=None):
    super(WithBrowser, self).__init__()
    self._driver = browsers.get_driver()
    self._browser = browsers.get_browser()


class Component(WithBrowser):
  """Component class is container for elements."""

  def __init__(self, _driver=None):
    super(Component, self).__init__()
    if self._driver.title:  # only Login page doesn't have title and jQuery
      selenium_utils.wait_for_js_to_load(self._driver)


class AnimatedComponent(Component):
  """Class for components where animation must first complete before
 elements are visible."""

  def __init__(self, driver, locators_to_check, wait_until_visible):
    """
    Args:
    driver (CustomDriver)
    locators_to_check (list of tuples): locators to wait for to become
    (in)visible
    wait_until_visible (bool): for all elements to be visible do we
    have to wait for certain elements to be invisible or visible?
    """
    super(AnimatedComponent, self).__init__(driver)
    self._locators = locators_to_check
    if wait_until_visible:
      self._wait_until_visible()
    else:
      self._wait_until_invisible()

  def _wait_until_visible(self):
    for item_locator in self._locators:
      selenium_utils.get_when_visible(self._driver, item_locator)

  def _wait_until_invisible(self):
    for item_locator in self._locators:
      selenium_utils.get_when_invisible(self._driver, item_locator)


class Modal(Component):
  """Generic modal element."""


class FilterCommon(Component):
  """Common filter elements for LHN and Tree View."""

  def __init__(self, driver, text_box_locator, bt_submit_locator):
    super(FilterCommon, self).__init__(driver)
    self.text_box = TextInputField(driver, text_box_locator)
    self.button_submit = Button(driver, bt_submit_locator)

  def enter_query(self, query):
    """Enter query to field."""
    self.text_box.enter_text(query)

  def submit_query(self):
    """Submit query that was entered to field."""
    self.button_submit.click()
    selenium_utils.wait_for_js_to_load(self._driver)

  def perform_query(self, query):
    """Clear filtering field, enter query and click submit."""
    self.enter_query(query)
    self.submit_query()


class FilterLHN(FilterCommon):
  """Filter elements for LHN."""

  def __init__(self, driver, text_box_locator,
               bt_submit_locator, bt_clear_locator):
    super(FilterLHN, self).__init__(driver, text_box_locator,
                                    bt_submit_locator)
    # clear button is only visible after a query is entered
    self.button_clear = driver.find_element(*bt_clear_locator)

  def clear_query(self):
    """Clear query that was entered to field."""
    self.button_clear.click()
    selenium_utils.wait_for_js_to_load(self._driver)


class DropdownDynamic(AnimatedComponent):
  """Dropdown that doesn't load all contents at once."""

  def __init__(self, driver, locators_to_check, wait_until_visible):
    """
    Args:
    driver (CustomDriver)
    locators_to_check (list of tuples): locators to wait for to become
    (in)visible
    wait_until_visible (bool): for all elements to be visible do we
    have to wait for certain elements to be invisible or visible?
    """
    super(DropdownDynamic, self).__init__(driver, locators_to_check,
                                          wait_until_visible)
    self.members_visible = None
    self.members_loaded = None

  def _update_loaded_members(self):
    """New members that are loaded are added to members_loaded container."""
    raise NotImplementedError

  def _set_visible_members(self):
    """When moving in dropdown it can happen we don't always see all
    the members. Here we set members, that are visible to user."""
    raise NotImplementedError

  def scroll_down(self):
    raise NotImplementedError

  def scroll_up(self):
    raise NotImplementedError


class Selectable(Element):
  """Representing list of elements that are selectable."""


class MultiInputField(Element):
  """Representing fields that added plus sign."""
  _locators = constants.locator.MultiInputField

  def __init__(self, driver, loc_or_el):
    super(MultiInputField, self).__init__(driver, loc_or_el)
    self._items = None
    self.add_btn = Button(self.element, self._locators.ADD_BTN_CSS)

  def _init_items(self):
    """Init list of input items into multi input field."""
    self._items = [
        MultiInputItem(self._driver, el) for el in
        selenium_utils.get_when_all_visible(
            self._driver, self._locators.ITEMS)]

  @property
  def values(self):
    """Return list of text w/o date from each multi input item field."""
    self._init_items()
    return [item.link.text for item in self._items]

  def add_values(self, *values):
    """Add values to multiple input field."""
    for value in values:
      self.add_btn.click()
      TextInputField(self.element, self._locators.TXT_CSS).enter_text(value)
      Button(self.element, self._locators.APPLY_BTN_CSS).click()

  def del_values(self, *values):
    """Remove values from multiple input field."""
    raise NotImplementedError


class MultiInputItem(Element):
  """Representing single item in multi input field."""
  _locators = constants.locator.MultiInputItem

  @property
  def link(self):
    """Return link element of from multi input item field."""
    return Element(self.element, self._locators.LINK_CSS)

  @property
  def date(self):
    """Return date as string in mm/dd/yyyy format when input item was
    entered.
    """
    return Element(self.element, self._locators.DATE).text


class Widget(Component):
  """Page like class for which we don't know initial url."""

  def __init__(self, _driver=None):
    super(Widget, self).__init__()


class TreeView(Component):
  """Common class for representing Tree View list with several objects."""
  # pylint: disable=too-many-instance-attributes
  _locators = constants.locator.TreeView

  def __init__(self, driver, obj_name=None):
    super(TreeView, self).__init__(driver)
    self._tree_view_headers = []
    self._tree_view_items = []
    self.locator_set_visible_fields = None
    self.locator_no_results_message = self._locators.NO_RESULTS_MSG_CSS
    self.obj_name = obj_name
    if self.obj_name is not None:
      from lib import factory
      self.fields_to_set = factory.get_fields_to_set(object_name=self.obj_name)

  def wait_loading_after_actions(self):
    """Wait loading elements of Tree View after made some action with
    object(s) under Tree View.
    """
    from lib.utils.test_utils import wait_for
    selenium_utils.wait_until_not_present(
        self._driver, self._locators.ITEM_LOADING_CSS)
    selenium_utils.get_when_invisible(
        self._driver, self._locators.TREE_SPINNER_CSS)
    if "MAPPER_TREE_SPINNER_NO_RESULT" in self._locators.__dict__:
      def is_result_ready():
        """Check if the results on mapper is ready."""
        is_results_ready = False
        if not selenium_utils.is_element_enabled(
            selenium_utils.get_when_visible(
                self._driver,
                constants.locator.CommonModalUnifiedMapper.BUTTON_SEARCH)
        ):
          return is_results_ready
        if (
            selenium_utils.is_element_exist(
                self._driver, self._locators.MAPPER_TREE_SPINNER_NO_RESULT) or
            selenium_utils.is_element_exist(
                self._driver, self._locators.MAPPER_TREE_SPINNER_ITEMS)
        ):
          return is_results_ready
        if (
            selenium_utils.is_element_exist(
                self._driver, self.locator_no_results_message) or
            selenium_utils.get_when_all_visible(
                self._driver, (By.CSS_SELECTOR, self._locators.ITEMS))
        ):
          is_results_ready = True
          return is_results_ready
        return is_results_ready
      wait_for(is_result_ready)
    selenium_utils.wait_for_doc_is_ready(self._driver)
    selenium_utils.wait_for_js_to_load(self._driver)

  def _init_tree_view_headers(self):
    """Init Tree View headers as list of elements from current widget."""
    _locator_header = (By.CSS_SELECTOR, self._locators.HEADER)
    self._tree_view_headers = selenium_utils.get_when_all_visible(
        self._driver, _locator_header)

  def _init_tree_view_items(self):
    """Init Tree View items as list of TreeViewItem from current widget.
    If no items in tree view return empty list.
    """
    _locator_items = (
        By.CSS_SELECTOR, self._locators.ITEMS)
    self.wait_loading_after_actions()
    has_no_record_found = selenium_utils.is_element_exist(
        self._driver, self.locator_no_results_message)
    self._tree_view_items = (
        [] if has_no_record_found else [
            TreeViewItem(
                driver=self._driver, locator_or_element=element,
                item_btn_locator=(
                    By.CSS_SELECTOR, self._locators.ITEM_EXPAND_BTN))
            for element in selenium_utils.get_when_all_visible(
                self._driver, _locator_items)])
    return self._tree_view_items

  def tree_view_headers(self):
    """Return Tree View header as list of elements from current widget."""
    if not self._tree_view_headers:
      self._init_tree_view_headers()
    return self._tree_view_headers

  def tree_view_items(self, is_updated=False):
    """Return Tree View items as list of TreeViewItem from current widget."""
    if is_updated or not self._tree_view_items:
      self._init_tree_view_items()
    return self._tree_view_items

  def open_set_visible_fields(self):
    """Click to Set Visible Fields button on Tree View to open
    Set Visible Fields modal.
    Return: lib.page.modal.set_fields.SetVisibleFieldsModal
    """
    _locator_set_visible_fields = self.locator_set_visible_fields
    Button(self._driver, _locator_set_visible_fields).click()
    return SetVisibleFieldsModal(self._driver, self.fields_to_set)

  def get_list_members_as_list_scopes(self):
    """Get list of scopes (dicts) from members (text scopes) which displayed on
    Tree View according to current set of visible fields.
    """
    tree_view_items = self.tree_view_items()
    list_scopes = []
    if tree_view_items:
      list_headers = [_item.text.splitlines()[:len(self.fields_to_set)] for
                      _item in self.tree_view_headers()]
      list_lists_items = [
          [_.split(", ") if len(_.split(", ")) >= 2 else _ for
           _ in _item.cell_values[:len(self.fields_to_set)]] for
          _item in tree_view_items]
      for tree_view_item, list_item in zip(tree_view_items, list_lists_items):
        scope = dict(zip(list_headers[0], list_item))
        scope.update(url=tree_view_item.url(), id=tree_view_item.obj_id())
        list_scopes.append(scope)
    return list_scopes


class UnifiedMapperTreeView(TreeView):
  """Tree-View class for Unified Mapper"""
  _locators = constants.locator.UnifiedMapperTreeView

  def __init__(self, driver, obj_name):
    super(UnifiedMapperTreeView, self).__init__(driver, obj_name)
    self.locator_set_visible_fields = self._locators.SHOW_FIELDS_BTN_CSS
    self.locator_no_results_message = self._locators.NO_RESULTS_MSG_CSS

  def open_set_visible_fields(self):
    """Click to Set Visible Fields button on Tree View to open
    Set Visible Fields modal.
    Return: lib.page.modal.set_fields.SetVisibleFieldsModal
    """
    Button(self._driver, self.locator_set_visible_fields).click()
    return MapperSetVisibleFieldsModal(self._driver, self.fields_to_set)


class AdminTreeView(TreeView):
  """Class for representing Tree View list in Admin dashboard."""
  _locators = constants.locator.AdminTreeView


class SetVisibleFieldsModal(Modal):
  """Modal to select and set visible fields for objects to represent them on
  Tree View."""
  _locators = constants.locator.ModalSetVisibleFields

  def __init__(self, driver, fields_to_set):
    super(SetVisibleFieldsModal, self).__init__(driver)
    self.fields_to_set = fields_to_set
    self.visible_fields_elements = None

  def select_visible_fields(self):
    """Select visible fields checkboxes on Select Visible Fields modal
    according to titles of fields to set."""
    # pylint: disable=attribute-defined-outside-init
    _locator_modal_fields = (By.CSS_SELECTOR,
                             self._locators.MODAL)
    _locator_fields_titles = (
        By.CSS_SELECTOR,
        self._locators.FIELDS_TITLES)
    _locator_fields_checkboxes = (
        By.CSS_SELECTOR,
        self._locators.FIELDS_CHECKBOXES)
    selenium_utils.get_when_visible(self._driver, _locator_modal_fields)
    self.visible_fields_elements = ListCheckboxes(
        self._driver, titles_locator=_locator_fields_titles,
        checkboxes_locator=_locator_fields_checkboxes)
    self.visible_fields_elements.select_by_titles(self.fields_to_set)

  def confirm_set_visible_fields(self):
    """Confirm set visible fields."""
    _locator_set_fields = (
        By.CSS_SELECTOR,
        self._locators.BUTTON_SET_FIELDS)
    Button(self._driver, _locator_set_fields).click_via_js()  # issue GGRC-1854
    selenium_utils.get_when_invisible(self._driver, _locator_set_fields)

  def select_and_set_visible_fields(self):
    """Select checkboxes to set objects visible fields and confirm set."""
    self.select_visible_fields()
    self.confirm_set_visible_fields()


class MapperSetVisibleFieldsModal(SetVisibleFieldsModal):
  """Modal to select and set visible fields for objects to represent them on
  Tree View."""
  _locators = constants.locator.ModalSetVisibleFieldsMapper


class TreeViewItem(Element):
  """Class for describing single item on Tree View."""
  _locators = constants.locator.TreeViewItem

  def __init__(self, driver, locator_or_element, item_btn_locator=None):
    super(TreeViewItem, self).__init__(driver, locator_or_element)
    self.item_btn = (
        None if item_btn_locator is None else
        selenium_utils.get_element_safe(
            self.element, item_btn_locator))
    if self.item_btn:
      self.js_field_name = "instance"
    else:
      self.js_field_name = "itemData"

  def url(self):
    """Returns url to the object."""
    view_link = self._driver.execute_script(
        "return $(arguments[0]).viewModel().{}.viewLink".format(
            self.js_field_name), self.element)
    return environment.app_url[:-1] + view_link

  def obj_id(self):
    """Returns id of the object."""
    return self._driver.execute_script(
        "return $(arguments[0]).viewModel().{}.id".format(self.js_field_name),
        self.element)

  def expand(self):
    """Expand Tree View item if it is not expanded already."""
    if not self.is_expanded:
      self.item_btn.click()
      selenium_utils.wait_until_stops_moving(self.item_btn)

  def collapse(self):
    """Collapse Tree View item if it is expanded."""
    if self.is_expanded:
      self.item_btn.click()
      selenium_utils.wait_until_stops_moving(self.item_btn)

  @property
  def is_expanded(self):
    return selenium_utils.is_value_in_attr(self.item_btn)

  @property
  def cell_values(self):
    """Return list of text from each cell"""
    return [cell.text for
            cell in selenium_utils.get_when_all_visible(
                self.element, self._locators.CELL)]


class CommentsPanel(Element):
  """Representing comments panel witch contains input part and items."""
  _locators = constants.locator.CommentsPanel

  def __init__(self, driver, locator_or_element):
    super(CommentsPanel, self).__init__(driver, locator_or_element)
    self._items = []
    self._root = self._browser.div(text="Responses/Comments").parent()

  @property
  def input_txt(self):
    return self._root.element(class_name="ql-editor")

  @property
  def add_btn(self):
    return self._root.button(text="Add")

  @property
  def send_cb(self):
    return self._root.element(class_name="comment-add-form__toolbar-item")

  @property
  def scopes(self):
    """Return list of text comments in dictionary format where each of them
    contains items:
    {'modified_by': person, 'created_at': datetime, 'description': text}.
    """
    self._items = [
        CommentItem(self._driver, element) for element in
        self.element.find_elements(*self._locators.ITEMS_CSS)]
    comments = []
    for item in self._items:
      description = item.content.text
      # reviewers emails in review comment message need to be sorted as they
      # are displayed in UI in random order
      if (re.compile(constants.element.Common.REVIEW_COMMENT_REGEXP).
         match(description)):
        splited_description = description.split('\n')
        splited_description[1] = ', '.join(
            sorted(splited_description[1].split(', ')))
        description = '\n'.join(splited_description)
      comments.append({"modified_by": item.author.text,
                       "created_at": item.datetime,
                       "description": description})
    return comments

  @property
  def count(self):
    """Return count of text comments on comments panel."""
    return len(self.scopes)

  @property
  def is_input_empty(self):
    """Return 'True' if comments input field is empty, else 'False'."""
    return not self.input_txt.text

  def add_comment(self, text):
    """Clear text from element and enter new text."""
    self.input_txt.clear()
    self.input_txt.send_keys(text)
    self.add_btn.click()

  def add_comments(self, comments):
    """Add text comments to input field."""
    count_of_comments = len(self.scopes)
    for comment in comments:
      self.add_comment(comment)
      selenium_utils.get_when_invisible(
          self._driver, constants.locator.Common.SPINNER_CSS)
      count_of_comments += 1
      try:
        selenium_utils.wait_until_condition(
            self._driver, lambda items: len(self.scopes) == count_of_comments)
      except exceptions.TimeoutException as err:
        raise (messages.ExceptionsMessages.err_comments_count.format(
            count_of_comments, len(self.scopes)) + str(err))
    return self


class CommentItem(Element):
  """Representing single comment item in comments' panel."""
  _locators = constants.locator.CommentItem

  @property
  def author(self):
    """Return author element of comment from comments item."""
    return Element(self.element, self._locators.AUTHOR_CSS)

  @property
  def datetime(self):
    """Return datetime of comment from comments item."""
    text = self.element.find_element(*self._locators.DATETIME_CSS).text
    match = re.search(r"\(.+\) (.+)", text)
    if match:
      return match.group(1)
    return text

  @property
  def content(self):
    """Return content element of comment from comments item."""
    return Label(self.element, self._locators.CONTENT_CSS)


class ListCheckboxes(Component):
  """Generic list of checkboxes elements."""

  def __init__(self, driver, titles_locator, checkboxes_locator):
    super(ListCheckboxes, self).__init__(driver)
    self.locator_titles = titles_locator
    self.locator_checkboxes = checkboxes_locator

  def _select_necessary(self, checkboxes, title_els, list_titles):
    """Select necessary and deselect unnecessary checkboxes.
    Search for elements is optimized using JS as getting checked-ness
    and text of elements in a long list takes a lot of time."""
    checkboxes_to_click = self._driver.execute_script("""
    var checkboxes = arguments[0];
    var title_els = arguments[1];
    var titles = arguments[2];
    var list_to_click = [];
    for (let i = 0; i < checkboxes.length; i++) {
      let checkbox = checkboxes[i];
      let title = title_els[i].textContent.trim();
      if (checkbox.checked && !titles.includes(title)) {
        list_to_click.push(checkbox);
      }
    }
    for (let i = 0; i < checkboxes.length; i++) {
      let checkbox = checkboxes[i];
      let title = title_els[i].textContent.trim();
      if (!checkbox.checked && titles.includes(title)) {
        list_to_click.push(checkbox);
      }
    }
    return list_to_click;
    """, checkboxes, title_els, list_titles)
    for checkbox in checkboxes_to_click:
      checkbox.click()

  def select_by_titles(self, list_titles):
    """Select checkboxes according titles."""
    selenium_utils.wait_for_js_to_load(self._driver)
    selenium_utils.get_when_visible(self._driver, self.locator_titles)
    checkboxes = self._driver.find_elements(*self.locator_checkboxes)
    title_els = self._driver.find_elements(*self.locator_titles)
    self._select_necessary(checkboxes, title_els, list_titles)

  def get_mapping_statuses(self):
    """Get list of mapping statuses by given titles"""
    selenium_utils.get_when_all_visible(self._driver, self.locator_titles)
    objs_titles = self._driver.find_elements(*self.locator_titles)
    objs_checkboxes = self._driver.find_elements(*self.locator_checkboxes)
    objs = [
        constants.element.MappingStatusAttrs(
            obj[0], obj[1][0], obj[1][1]) for obj in zip(
            [obj.text for obj in objs_titles],
            [[obj.is_selected(),
              not obj.is_enabled()]
                for obj in objs_checkboxes])]
    return objs


class ElementsList(Component):
  """List represent of list of DOM ui elements. 'list_element' is items
  container in DOM it equal to 'ul'.
  """

  def __init__(self, driver, element_or_locator):
    super(ElementsList, self).__init__(driver)
    self._driver = driver
    self.list_element = self._get_list_element(element_or_locator)
    self._items = []
    self._item_class = None
    self.item_class = Element

  @property
  def item_class(self):
    """Getter for class of Items"""
    return self._item_class

  @item_class.setter
  def item_class(self, element_class):
    """Setter for class of Items"""
    self._item_class = element_class

  def _get_list_element(self, element_or_locactor):
    """Find element by locator or do nothing if passed var is 'WebElement'.
    Then check tag of element and if it is not 'ul' raise Error
    """
    element = (element_or_locactor if isinstance(
               element_or_locactor, webdriver.remote.webelement.WebElement)
               else selenium_utils.get_when_visible(self._driver,
                                                    element_or_locactor))
    if element.tag_name != 'ul':
      raise ValueError("WebElement is {}. Pass 'ul' element".format(
          element.tag_name))
    return element

  def get_items(self):
    """Return list of items object. Class of item selected according to
    "self.item_class" property.
    """
    if not self._items:
      self._items = [
          self.item_class(self._driver, el) for el in
          self.list_element.find_elements(
              *constants.locator.CommonDropdownMenu.DROPDOWN_ITEMS_CSS)]
    return self._items

  def get_item(self, text):
    """Return item from list of items by element text"""
    return next(elem_val for elem_val in self.get_items() if
                text in elem_val.text)

  def is_item_exist(self, condition_property):
    """Check if item exists in item list return Boolean True, by comparing
    texts.
    Return boolean True if element exists.
    """
    return any(elem_val.text for elem_val in self.get_items()
               if condition_property in elem_val.text)


class DropdownMenuItem(Element):
  """Class for dropdown item"""
  _locators = constants.locator.CommonDropdownMenu
  _elements = constants.element.DropdownMenuItemTypes

  def __init__(self, driver, locator_or_element):
    super(DropdownMenuItem, self).__init__(driver, locator_or_element)
    self._enabled = None
    self._item_type = ""

  @property
  def item_type(self):
    """Item type defined by class of icon"""
    if not self._item_type:
      icon = selenium_utils.get_element_safe(
          self.element, self._locators.DROPDOWN_ITEM_ICON_CSS)
      if icon:
        icon_type = icon.get_attribute("class")
        self._item_type = next(
            (v for k, v in self._elements.__dict__.iteritems()
             if not k.startswith("_") and v in icon_type),
            icon_type)
    return self._item_type

  @property
  def enabled(self):
    """Return True if DropdownMenu Item enabled"""
    if not self._enabled:
      self._enabled = selenium_utils.is_element_enabled(self.element)
    return self._enabled


class AbstractTabContainer(Component):
  """Abstract class for TabContainer. You should define "_get_locators" and
  "_tabs" methods in the child classes
  """
  def __init__(self, driver, container_element):
    super(AbstractTabContainer, self).__init__(driver)
    self.container_element = container_element
    self._locators = self._get_locators()
    self.tabs = self._tabs()

  def _get_locators(self):
    """Abstract method. Should return locators class."""
    raise NotImplementedError

  def _tabs(self):
    """Abstract method. Should return dict. {'tab_name': tab_object, ...}"""
    raise NotImplementedError

  @lazy_property
  def tab_controller(self):
    """Lazy property for dashboard controller."""
    from lib.element.elements_list import TabController
    return TabController(self._driver, self._locators.TAB_CONTROLLER_CSS)

  @property
  def active_tab_elem(self):
    """Return active tab element."""
    return self.container_element.find_element(
        *self._locators.TAB_CONTENT_CSS)


class AbstractTable(Component):
  """Abstract class for generic table."""

  def get_headers(self):
    """"Abstract method. Should return headers element of table."""
    raise NotImplementedError

  def get_rows(self):
    """"Abstract method. Should return rows element of table."""
    raise NotImplementedError

  def get_cells(self, row):
    """"Abstract method. Should return cells element of table."""
    raise NotImplementedError

  def get_items(self, as_element=False):
    """Abstract method. Should return list of dicts for header and cell value.
    """
    raise NotImplementedError


class AbstractCustomAttribute(Element):
  """Abstract class for custom attribute element."""

  def set_value(self):
    """"Abstract method. Should set custom attribute value."""
    raise NotImplementedError

  def get_value(self):
    """Abstract method. Should get custom attribute value."""
    raise NotImplementedError


class DateCustomAttribute(DatePicker, AbstractCustomAttribute):
  """Implementation of abstarct class AbstractCustomAttribute
  for date custom attribute."""

  def __init__(self, driver, date_picker_locator, field_locator):
    super(DateCustomAttribute, self).__init__(driver, date_picker_locator,
                                              field_locator)

  def set_value(self):
    """Set value of Date custom attribute."""
    self.select_rand_day_in_curr_month()

  def get_value(self):
    """Get value of Date custom attribute."""
    _date = self.text.split("/")
    return unicode("{y}-{m}-{d}".format(y=_date[2], m=_date[0], d=_date[1]))
