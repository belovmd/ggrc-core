# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Handlers for access control roles."""
from ggrc.converters import errors
from ggrc.converters.handlers import handlers
from ggrc.login import get_current_user
from ggrc.models.mixins.autostatuschangeable import AutoStatusChangeable
from ggrc.models.mixins.statusable import Statusable


class AccessControlRoleColumnHandler(handlers.UsersColumnHandler):
  """Handler for access control roles."""

  def __init__(self, row_converter, key, **options):
    super(AccessControlRoleColumnHandler, self).__init__(
        row_converter, key, **options)
    role_name = (options.get("attr_name") or self.display_name)
    self.acl = row_converter.obj.acr_name_acl_map[role_name]

  def set_obj_attr(self):
    """Update current AC list with correct people values."""
    value_is_correct = self.value or self.set_empty
    if not value_is_correct:
      return
    new_value = set() if self.set_empty else set(self.value)
    is_updated = self.acl.update_people(new_value)
    if isinstance(self.row_converter.obj, AutoStatusChangeable):
      is_status_changing = self.row_converter.obj.status in \
          Statusable.DONE_STATES
      if is_updated and is_status_changing and not self.row_converter.is_new:
        self.obj.status = "In Progress"
        self.add_warning(errors.STATE_WILL_BE_IGNORED,
                         column_name=self.display_name)

  def get_value(self):
    """Get list of emails for people with the current AC role."""
    people = sorted(
        acp.person.email
        for acp in self.acl.access_control_people
    )
    return "\n".join(people)

  def insert_object(self):
    """Set the assignee type of imported comments"""
    if self.row_converter.comments:
      current_user = get_current_user()
      role_name = self.acl.ac_role.name
      parent = self.row_converter.obj
      acl_people = [person for person, acl in parent.access_control_list
                    if acl.ac_role.name == self.acl.ac_role.name]

      if current_user in acl_people:
        for comment in self.row_converter.comments:
          if role_name not in comment.assignee_type:
            if comment.assignee_type:
              comment.assignee_type += ',' + role_name
            else:
              comment.assignee_type = role_name
