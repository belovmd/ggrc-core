/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canMap from 'can-map';
import canComponent from 'can-component';
import {
  loadPersonProfile,
} from '../../plugins/utils/user-utils';
import PersonProfile from '../../models/service-models/person-profile';

const NO_RESET_KEYS = [
  'Control',
  'Alt',
  'Meta',
  'Tab',
  'CapsLock',
  'Shift',
  'Escape',
  'ArrowLeft',
  'ArrowRight',
  'ArrowUp',
  'ArrowDown',
  'Enter',
];

const viewModel = canMap.extend({
  instance: null,
  isNewInstance: false,
  turnOnCalendarEvents: true,
  isNameReadOnly: false,
  async updatePersonProfile() {
    const instance = this.attr('instance');
    let profile = PersonProfile.findInCacheById(instance.attr('profile.id'));

    // If we use "Create" modal then profile might be empty.
    // It's generated on BE after person creation. Because of this,
    // profile should be loaded.
    if (!profile) {
      profile = await loadPersonProfile(instance);
    }

    profile
      .attr('send_calendar_events', this.attr('turnOnCalendarEvents'))
      .save();
  },
  loadPersonProfile() {
    // Profile is loaded in the moment of modal initialization via person's
    // formPreload method
    const profile = PersonProfile.findInCacheById(
      this.attr('instance.profile.id')
    );
    this.attr('turnOnCalendarEvents', profile.attr('send_calendar_events'));
  },
  setIsNameReadOnly() {
    const email = this.attr('instance.email') || '';
    const isEmailInternal = email.endsWith('@google.com');
    this.attr('isNameReadOnly', isEmailInternal);
  },
  personSelected({person}) {
    this.attr('instance.email', person.email);
    this.attr('instance.name', person.name);
    this.setIsNameReadOnly();
  },
  onEmailFieldKeyUp({key}) {
    if (!NO_RESET_KEYS.includes(key)) {
      this.attr('isNameReadOnly', false);
    }
  },
  init() {
    this.setIsNameReadOnly();
  },
});

const events = {
  '{instance} created'() {
    this.viewModel.updatePersonProfile();
  },
  '{instance} updated'() {
    this.viewModel.updatePersonProfile();
  },
  inserted() {
    const viewModel = this.viewModel;

    // If we open Edit modal then person profile should be loaded
    if (!viewModel.attr('isNewInstance')) {
      viewModel.loadPersonProfile();
    }
  },
};

export default canComponent.extend({
  tag: 'person-modal',
  leakScope: true,
  viewModel,
  events,
});
