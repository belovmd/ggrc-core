/*
    Copyright (C) 2019 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import loFindIndex from 'lodash/findIndex';
import loMap from 'lodash/map';
import canMap from 'can-map';
import canComponent from 'can-component';
import canStache from 'can-stache';
import template from './templates/assessment-template-attributes.stache';
import './template-field/template-field';
import './add-template-field/add-template-field';
import '../spinner-component/spinner-component';

/*
 * Assessment template main component
 *
 * It collects fields data and it transforms them into appropriate
 * format for saving
 */
export default canComponent.extend({
  tag: 'assessment-template-attributes',
  view: canStache(template),
  viewModel: canMap.extend({
    fields: [],
    editMode: true,
    isLoading: false,
    types: [{
      type: 'Text',
      name: 'Text',
      text: 'Enter description',
    }, {
      type: 'Rich Text',
      name: 'Rich Text',
      text: 'Enter description',
    }, {
      type: 'Date',
      name: 'Date',
      text: 'MM/DD/YYYY',
    }, {
      type: 'Checkbox',
      name: 'Checkbox',
      text: '',
    }, {
      type: 'Multiselect',
      name: 'Multiselect',
      text: 'Enter values separated by comma',
    }, {
      type: 'Dropdown',
      name: 'Dropdown',
      text: 'Enter values separated by comma',
    }, {
      type: 'Map:Person',
      name: 'Person',
      text: '',
    }],

    /**
     * A handler for when a user removes a Custom Attribute Definition.
     *
     * It removes the corresponding CA definition object from the list to
     * keep it in sync with the definitions listed in DOM.
     *
     * @param {CustomAttributeDefinition} field -
     *   the definition that was removed
     */
    fieldRemoved: function (field) {
      let idx = loFindIndex(this.fields, {title: field.title});
      if (idx >= 0) {
        this.fields.splice(idx, 1);
      } else {
        console.warn('The list of CAD doesn\'t contain item with "' +
          field.title + '" title');
      }
    },
  }),
  events: {
    inserted: function () {
      let el = $(this.element);
      let list = el.find('.sortable-list');
      list.sortable({
        items: '.sortable-item',
        placeholder: 'sortable-placeholder',
      });
    },
    '.sortable-list sortstop': function () {
      let el = $(this.element);
      let sortables = el.find('.sortable-item');
      // It's not nice way to rely on DOM for sorting,
      // but it was easiest for implementation
      this.viewModel.fields.replace(loMap(sortables,
        function (item) {
          return $(item).data('field');
        }
      ));
    },
  },
});
