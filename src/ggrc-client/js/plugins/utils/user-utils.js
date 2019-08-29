/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import loUniq from 'lodash/uniq';
import loForEach from 'lodash/forEach';
import Person from '../../models/business-models/person';
import PersonProfile from '../../models/service-models/person-profile';
import RefreshQueue from '../../models/refresh_queue';
import {getPageInstance} from './current-page-utils';
import {notifier} from './notifiers-utils';

function cacheCurrentUser() {
  Person.model(GGRC.current_user);
}

function getPersonInfo(person) {
  const dfd = $.Deferred();
  let actualPerson;

  if (!person || !person.id) {
    dfd.resolve(person);
    return dfd;
  }

  actualPerson = Person.findInCacheById(person.id) || {};
  if (actualPerson.email) {
    dfd.resolve(actualPerson);
  } else {
    actualPerson = new Person({id: person.id});
    new RefreshQueue()
      .enqueue(actualPerson)
      .trigger()
      .done((personItem) => {
        personItem = Array.isArray(personItem) ? personItem[0] : personItem;
        dfd.resolve(personItem);
      })
      .fail(function () {
        notifier('error',
          'Failed to fetch data for person ' + person.id + '.');
        dfd.reject();
      });
  }

  return dfd;
}

function loadPersonProfile(person) {
  return PersonProfile.findOne({
    id: person.attr('profile.id'),
  });
}

function getUserSystemRoles(person) {
  const globalRole = person.system_wide_role === 'No Access' ?
    'No Role' : person.system_wide_role;
  return [globalRole];
}

function getUserObjectRoles(person) {
  const parentInstance = getPageInstance();

  const roles = {};
  let allRoleNames = [];

  loForEach(GGRC.access_control_roles, (role) => {
    roles[role.id] = role;
  });

  if (parentInstance && parentInstance.access_control_list) {
    allRoleNames = loUniq(parentInstance.access_control_list.filter((acl) => {
      return acl.person.id === person.id && acl.ac_role_id in roles;
    }).map((acl) => {
      return roles[acl.ac_role_id].name;
    }));
  }
  return allRoleNames;
}

export {
  cacheCurrentUser,
  getPersonInfo,
  loadPersonProfile,
  getUserSystemRoles,
  getUserObjectRoles,
};
