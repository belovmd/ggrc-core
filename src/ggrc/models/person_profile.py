# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module for person's profile object"""

from datetime import datetime, timedelta

from sqlalchemy.orm import relationship

from ggrc import db
from ggrc.models.inflector import ModelInflectorDescriptor
from ggrc.models.mixins.base import Identifiable

# Offset for default last seen what's new date in days
DEFAULT_LAST_SEEN_OFFSET = 60


def default_last_seen_date():
  """Function counts last_seen_whats_new date for new users"""
  return datetime.now() - timedelta(DEFAULT_LAST_SEEN_OFFSET)


# pylint: disable=too-few-public-methods
class PersonProfile(Identifiable, db.Model):
  """Class represents person's profile.

  Profile keeps user's preferences and local user settings such as
  "last seen what's" new date"""

  __tablename__ = 'people_profiles'
  _inflector = ModelInflectorDescriptor()

  person_id = db.Column(db.Integer, db.ForeignKey('people.id'))

  last_seen_whats_new = db.Column(db.DateTime, default=default_last_seen_date)

  person = relationship("Person", back_populates='profile')
