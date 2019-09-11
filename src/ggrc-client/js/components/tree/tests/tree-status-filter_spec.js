/*
    Copyright (C) 2019 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import canList from 'can-list';
import Component from '../tree-status-filter';
import * as StateUtils from '../../../plugins/utils/state-utils';
import router from '../../../router';
import {getComponentVM} from '../../../../js_specs/spec_helpers';
import * as DisplayPrefs from '../../../plugins/utils/display-prefs-utils';

describe('tree-status-filter component', () => {
  let viewModel;

  beforeEach(() => {
    viewModel = getComponentVM(Component);
  });

  describe('buildSearchQuery() method', () => {
    const FILTER = {
      expression: 'test',
    };
    beforeEach(() => {
      spyOn(StateUtils, 'buildStatusFilter').and.returnValue(FILTER);
      spyOn(StateUtils, 'getStatesForModel').and.returnValue(['A', 'B', 'C']);
      spyOn(viewModel, 'dispatch');
    });

    it('dispatches empty query when all statuses selected', () => {
      viewModel.buildSearchQuery(['A', 'B', 'C']);

      expect(viewModel.dispatch).toHaveBeenCalledWith({
        type: 'searchQueryChanged',
        name: 'status',
        query: null,
      });
    });

    it('dispatches empty query when no status selected', () => {
      viewModel.buildSearchQuery([]);

      expect(viewModel.dispatch).toHaveBeenCalledWith({
        type: 'searchQueryChanged',
        name: 'status',
        query: null,
      });
    });

    it('dispatches NOT empty query when some status selected', () => {
      viewModel.buildSearchQuery(['A']);

      expect(viewModel.dispatch).toHaveBeenCalledWith({
        type: 'searchQueryChanged',
        name: 'status',
        query: FILTER,
      });
    });
  });

  describe('setStatesRoute() method', () => {
    beforeEach(() => {
      spyOn(StateUtils, 'getStatesForModel').and.returnValue(['A', 'B', 'C']);
    });

    it('write states to query string property', () => {
      let statuses = ['A'];

      viewModel.setStatesRoute(statuses);

      let result = router.attr('state').attr();
      expect(result).toEqual(statuses);
    });

    it('clear query string property when there are no states', () => {
      let statuses = [];
      router.attr('state', ['A']);

      viewModel.setStatesRoute(statuses);

      let result = router.attr('state');
      expect(result).toBeUndefined();
    });

    it('clear query string property when selected all states', () => {
      let statuses = ['A', 'B', 'C'];
      router.attr('state', ['A']);

      viewModel.setStatesRoute(statuses);

      let result = router.attr('state');
      expect(result).toBeUndefined();
    });
  });

  describe('setStatesDropdown() mthod', () => {
    beforeEach(() => {
      viewModel.attr('filterStates', [
        {value: 'A', checked: false},
        {value: 'B', checked: false},
        {value: 'C', checked: false},
      ]);
    });

    it('makes provided options checked', () => {
      viewModel.setStatesDropdown(['A', 'C']);

      expect(viewModel.attr('filterStates').serialize()).toEqual([
        {value: 'A', checked: true},
        {value: 'B', checked: false},
        {value: 'C', checked: true},
      ]);
    });
  });

  describe('saveTreeStates() method', () => {
    const filters = ['A', 'B'];
    beforeEach(() => {
      spyOn(DisplayPrefs, 'setTreeViewStates');
    });

    describe('saves filter to display preferences', () => {
      it('by widget id', () => {
        viewModel.attr('widgetId', 'testId');

        viewModel.saveTreeStates(filters);

        expect(DisplayPrefs.setTreeViewStates)
          .toHaveBeenCalledWith('testId', filters);
      });
    });
  });

  describe('getDefaultStates() method', () => {
    let savedFilters;
    beforeEach(() => {
      savedFilters = new canList(['c', 'd']);
      spyOn(savedFilters, 'filter').and.returnValue(['c']);
      spyOn(DisplayPrefs, 'getTreeViewStates').and.returnValue(savedFilters);
    });

    it('use filter set from query if it is presented', () => {
      let queryFilters = new canList(['a', 'b']);
      spyOn(queryFilters, 'filter').and.returnValue(['a']);
      router.attr('state', queryFilters);

      viewModel.getDefaultStates();

      expect(queryFilters.filter).toHaveBeenCalled();
    });

    it('use saved filters if set from query is not presented', () => {
      router.removeAttr('state');

      viewModel.getDefaultStates();

      expect(savedFilters.filter).toHaveBeenCalled();
    });
  });

  describe('"{viewModel.router} state" event handler', () => {
    let handler;
    let newStatuses;
    beforeEach(() => {
      handler = Component.prototype.events['{viewModel.router} state'].bind({
        viewModel,
      });
      spyOn(viewModel, 'buildSearchQuery');
      spyOn(viewModel, 'setStatesDropdown');
      spyOn(viewModel, 'dispatch');
    });

    describe('launches search', () => {
      afterEach(() => {
        handler([router], null, newStatuses);
        expect(viewModel.buildSearchQuery).toHaveBeenCalledWith(newStatuses);
        expect(viewModel.setStatesDropdown).toHaveBeenCalledWith(newStatuses);
        expect(viewModel.dispatch).toHaveBeenCalledWith('filter');
      });

      it(`when component is enabled,
        launched on current widget and statuses were changed`, () => {
        viewModel.attr('filterStates', [
          {value: 'A', checked: true},
          {value: 'B', checked: true},
        ]);
        newStatuses = ['C', 'D'];
        viewModel.attr('widgetId', 'test1');
        router.attr('widget', 'test1');
        viewModel.attr('disabled', false);
      });
    });

    describe('does not launch search', () => {
      afterEach(() => {
        handler([router], null, newStatuses);
        expect(viewModel.buildSearchQuery).not.toHaveBeenCalled();
        expect(viewModel.setStatesDropdown).not.toHaveBeenCalled();
        expect(viewModel.dispatch).not.toHaveBeenCalled();
      });

      it(`when component is disabled,
        launched on current widget and statuses were changed`, () => {
        viewModel.attr('filterStates', [
          {value: 'A', checked: true},
          {value: 'B', checked: true},
        ]);
        newStatuses = ['C', 'D'];
        viewModel.attr('widgetId', 'test1');
        router.attr('widget', 'test1');
        viewModel.attr('disabled', true);
      });

      it(`when component is enabled,
        launched on other widget and statuses were changed`, () => {
        viewModel.attr('filterStates', [
          {value: 'A', checked: true},
          {value: 'B', checked: true},
        ]);
        newStatuses = ['C', 'D'];
        viewModel.attr('widgetId', 'test1');
        router.attr('widget', 'test2');
        viewModel.attr('disabled', false);
      });

      it(`when component is enabled,
        launched on current widget and statuses were not changed`, () => {
        viewModel.attr('filterStates', [
          {value: 'A', checked: true},
          {value: 'B', checked: true},
        ]);
        newStatuses = ['A', 'B'];
        viewModel.attr('widgetId', 'test1');
        router.attr('widget', 'test1');
        viewModel.attr('disabled', false);
      });
    });
  });

  describe('"{viewModel} disabled" event handler', () => {
    let handler;
    let defaultFilters;
    beforeEach(() => {
      handler = Component.prototype.events['{viewModel} disabled'].bind({
        viewModel,
      });
      defaultFilters = ['A', 'B'];
      spyOn(viewModel, 'setStatesDropdown');
      spyOn(viewModel, 'setStatesRoute');
      spyOn(viewModel, 'getDefaultStates').and.returnValue(defaultFilters);
    });

    it('initializes empty filter if component is disabled', () => {
      viewModel.attr('disabled', true);

      handler();

      expect(viewModel.setStatesDropdown).toHaveBeenCalledWith([]);
      expect(viewModel.setStatesRoute).toHaveBeenCalledWith([]);
    });

    it('initializes default filter if component is not disabled', () => {
      viewModel.attr('disabled', false);

      handler();

      expect(viewModel.getDefaultStates).toHaveBeenCalled();
      expect(viewModel.setStatesDropdown).toHaveBeenCalledWith(defaultFilters);
      expect(viewModel.setStatesRoute).toHaveBeenCalledWith(defaultFilters);
    });
  });

  describe('"{viewModel.router} widget" event handler', () => {
    let handler;
    beforeEach(() => {
      handler = Component.prototype.events['{viewModel.router} widget'].bind({
        viewModel,
      });
      spyOn(viewModel, 'setStatesRoute');
      viewModel.attr('filterStates', [
        {value: 'A', checked: true},
        {value: 'B', checked: true},
      ]);
    });

    describe('sets current states to route', () => {
      afterEach(() => {
        handler([router]);
        expect(viewModel.setStatesRoute.calls.argsFor(0)[0].attr())
          .toEqual(['A', 'B']);
      });

      it(`when component is enabled,
        launched on current widget and there are no statuses in route`, () => {
        viewModel.attr('disabled', false);
        viewModel.attr('widgetId', 'test1');
        router.attr('widget', 'test1');
        router.removeAttr('state');
      });
    });
  });
});
