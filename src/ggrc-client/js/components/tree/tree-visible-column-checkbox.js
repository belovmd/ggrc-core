/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canStache from 'can-stache';
import canMap from 'can-map';
import canComponent from 'can-component';
import template from './templates/tree-visible-column-checkbox.stache';

export default canComponent.extend({
  tag: 'tree-visible-column-checkbox',
  view: canStache(template),
  leakScope: true,
  viewModel: canMap.extend({
    column: {},
  }),
});
