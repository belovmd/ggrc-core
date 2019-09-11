/*
  Copyright (C) 2019 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import {getComponentVM} from '../../../../js_specs/spec_helpers';
import Component from '../tree-filter-input';
import router from '../../../router';

describe('tree-filter-input component', () => {
  let viewModel;

  beforeEach(() => {
    viewModel = getComponentVM(Component);
  });

  describe('inserted() event', () => {
    let insertedEvent;
    beforeEach(() => {
      spyOn(viewModel, 'setupFilterFromUrl');
      spyOn(viewModel, 'dispatch');
      insertedEvent = Component.prototype.events.inserted.bind({viewModel});
    });

    it('setups filter for component based on url', () => {
      insertedEvent();
      expect(viewModel.setupFilterFromUrl).toHaveBeenCalled();
    });

    it('dispatch "treeFilterReady" event', () => {
      insertedEvent();
      expect(viewModel.dispatch).toHaveBeenCalledWith({
        type: 'treeFilterReady',
        filterName: 'tree-filter-input',
      });
    });
  });

  describe('setupFilterFromUrl() method', () => {
    let originalRouter;

    beforeAll(() => {
      originalRouter = router.attr();
    });

    beforeEach(() => {
      router.attr({}, true);
    });

    afterAll(() => {
      router.attr(originalRouter, true);
    });

    it('sets "filter" field to the string from url\'s "query" param', () => {
      router.attr('query', 'some string');
      viewModel.setupFilterFromUrl();
      expect(viewModel.attr('filter')).toBe(router.attr('query'));
    });

    it('sets "filter" field to an empty string if url does not have ' +
    '"query" param', () => {
      router.removeAttr('query');
      viewModel.setupFilterFromUrl();
      expect(viewModel.attr('filter')).toBe('');
    });
  });
});
