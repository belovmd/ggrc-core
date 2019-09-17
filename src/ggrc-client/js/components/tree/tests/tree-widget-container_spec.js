/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import makeArray from 'can-util/js/make-array/make-array';
import canList from 'can-list';
import canMap from 'can-map';
import {
  makeFakeInstance,
  makeFakeModel,
} from '../../../../js_specs/spec_helpers';
import * as TreeViewUtils from '../../../plugins/utils/tree-view-utils';
import * as WidgetsUtils from '../../../plugins/utils/widgets-utils';
import * as AdvancedSearch from '../../../plugins/utils/advanced-search-utils';
import * as NotifierUtils from '../../../plugins/utils/notifiers-utils';
import * as MegaObjectUtils from '../../../plugins/utils/mega-object-utils';
import tracker from '../../../tracker';
import {getComponentVM} from '../../../../js_specs/spec_helpers';
import Component, {loadSavedSearch, filterParentItems} from '../tree-widget-container';
import Relationship from '../../../models/service-models/relationship';
import exportMessage from '../templates/export-message.stache';
import QueryParser from '../../../generated/ggrc_filter_query_parser';
import SavedSearch from '../../../models/service-models/saved-search';
import * as CurrentPageUtils from '../../../plugins/utils/current-page-utils';
import router from '../../../router';
import Cacheable from '../../../models/cacheable';
import Program from '../../../models/business-models/program';
import Assessment from '../../../models/business-models/assessment';

describe('tree-widget-container component', function () {
  let vm;

  beforeEach(function () {
    vm = getComponentVM(Component);
  });

  describe('onSort() method', function () {
    let onSort;

    beforeEach(function () {
      onSort = vm.onSort.bind(vm);
      vm.attr('pageInfo.count', 3);

      spyOn(vm, 'loadItems');
      spyOn(vm, 'closeInfoPane');
    });

    it('sets current order properties', function () {
      onSort({
        field: 'col1',
        sortDirection: 'asc',
      });

      expect(vm.attr('sortingInfo.sortBy')).toEqual('col1');
      expect(vm.attr('sortingInfo.sortDirection')).toEqual('asc');
      expect(vm.attr('pageInfo.current')).toEqual(1);
      expect(vm.loadItems).toHaveBeenCalled();
      expect(vm.closeInfoPane).toHaveBeenCalled();
    });
  });

  describe('loadItems() method', function () {
    let loadItems;
    let modelName;
    let parent;
    let page;
    let filter;
    let request;
    let loadSnapshots;

    beforeEach(function () {
      modelName = 'testModelName';
      parent = new canMap({testParent: true});
      page = {
        current: 1,
        pageSize: 10,
        sort: [{
          key: null,
          direction: null,
        }],
      },
      filter = new canMap({testFilter: true});
      request = new canList([{testRequest: true}]);

      vm.attr('model', {
        model_singular: modelName,
      });
      vm.attr('options', {
        parent_instance: parent,
      });
      vm.attr('advancedSearch', {
        filter,
        request,
      });

      loadItems = vm.loadItems.bind(vm);
      spyOn(tracker, 'start').and.returnValue(() => {});
      spyOn(MegaObjectUtils, 'getMegaObjectRelation')
        .and.returnValue({relation: 'child'});
    });

    it('should call TreeViewUtils.loadFirstTierItems with specified ' +
    'arguments if "options.megaRelated" attr is truthy', function (done) {
      vm.attr('options.megaRelated', true);
      spyOn(TreeViewUtils, 'loadFirstTierItems')
        .and.returnValue($.Deferred().resolve({
          total: 100,
          values: [],
        }));
      loadItems().then(function () {
        expect(TreeViewUtils.loadFirstTierItems).toHaveBeenCalledWith(
          modelName, parent, page, filter, request, loadSnapshots, 'child');
        expect(vm.attr('pageInfo.total')).toEqual(100);
        expect(makeArray(vm.attr('showedItems'))).toEqual([]);
        done();
      });
    });

    it('should call TreeViewUtils.loadFirstTierItems with specified ' +
    'arguments if "options.megaRelated" attr is falsy', function (done) {
      vm.attr('options.megaRelated', false);
      spyOn(TreeViewUtils, 'loadFirstTierItems')
        .and.returnValue($.Deferred().resolve({
          total: 100,
          values: [],
        }));
      loadItems().then(function () {
        expect(TreeViewUtils.loadFirstTierItems).toHaveBeenCalledWith(
          modelName, parent, page, filter, request, loadSnapshots, null);
        expect(vm.attr('pageInfo.total')).toEqual(100);
        expect(makeArray(vm.attr('showedItems'))).toEqual([]);
        done();
      });
    });
  });

  describe('on widget appearing', function () {
    let _widgetShown;

    beforeEach(function () {
      _widgetShown = vm._widgetShown.bind(vm);
      spyOn(vm, '_triggerListeners');
      spyOn(vm, 'loadItems');
    });

    beforeEach(function () {
      let modelName = 'Model';
      spyOn(WidgetsUtils, 'getCounts').and.returnValue({[modelName]: 123});
      vm.attr({
        options: {
          countsName: modelName,
        },
        pageInfo: {
          total: 123,
        },
      });
    });

    it('should add listeners', function () {
      _widgetShown();
      expect(vm._triggerListeners).toHaveBeenCalled();
      expect(vm.loadItems).not.toHaveBeenCalled();
    });

    it('should load items if refetch flag is true', () => {
      vm.attr('refetch', true);
      router.attr('refetch', false);
      vm.attr('options.forceRefetch', false);

      _widgetShown();
      expect(vm.loadItems).toHaveBeenCalled();
    });

    it('should load items if url has refetch param', () => {
      vm.attr('refetch', false);
      router.attr('refetch', true);
      vm.attr('options.forceRefetch', false);

      _widgetShown();
      expect(vm.loadItems).toHaveBeenCalled();
      expect(vm.attr('refetch')).toBeFalsy();
    });

    it('should load items if widget has forceRefetch option', () => {
      vm.attr('refetch', false);
      router.attr('refetch', false);
      vm.attr('options.forceRefetch', true);

      _widgetShown();
      expect(vm.loadItems).toHaveBeenCalled();
    });

    it('should load items if count has changed', () => {
      vm.attr('refetch', false);
      router.attr('refetch', false);
      vm.attr('options.forceRefetch', false);
      vm.attr('pageInfo.total', 100); // less than current count

      _widgetShown();
      expect(vm.loadItems).toHaveBeenCalled();
    });
  });

  describe('openAdvancedFilter() method', function () {
    it('copies applied filter and mapping items', function () {
      let appliedFilterItems = new canList([
        AdvancedSearch.create.attribute(),
      ]);
      let appliedMappingItems = new canList([
        AdvancedSearch.create.mappingCriteria({
          filter: AdvancedSearch.create.attribute(),
        }),
      ]);
      vm.attr('advancedSearch.appliedFilterItems', appliedFilterItems);
      vm.attr('advancedSearch.appliedMappingItems', appliedMappingItems);
      vm.attr('advancedSearch.filterItems', canList());
      vm.attr('advancedSearch.mappingItems', canList());

      vm.openAdvancedFilter();

      expect(vm.attr('advancedSearch.filterItems').attr())
        .toEqual(appliedFilterItems.attr());
      expect(vm.attr('advancedSearch.mappingItems').attr())
        .toEqual(appliedMappingItems.attr());
    });

    it('opens modal window', function () {
      vm.attr('advancedSearch.open', false);

      vm.openAdvancedFilter();

      expect(vm.attr('advancedSearch.open')).toBe(true);
    });

    it('should add "parentInstance" when isObjectContextPage is TRUE' +
    'and "parentInstance" is empty', () => {
      const parentInstance = {id: 1, type: 'Audit'};
      spyOn(CurrentPageUtils, 'isObjectContextPage').and.returnValue(true);
      spyOn(AdvancedSearch.create, 'parentInstance')
        .and.returnValue({type: 'parentInstance', value: parentInstance});

      vm.attr('advancedSearch.parentInstance', null);

      vm.openAdvancedFilter();

      expect(AdvancedSearch.create.parentInstance).toHaveBeenCalled();
      expect(vm.attr('advancedSearch.parentInstance.value').serialize())
        .toEqual(parentInstance);
    });

    it('should NOT add "parentInstance" because it already set', () => {
      spyOn(CurrentPageUtils, 'isObjectContextPage').and.returnValue(true);
      spyOn(AdvancedSearch.create, 'parentInstance');

      vm.attr('advancedSearch.parentInstance', {id: 1});

      vm.openAdvancedFilter();

      expect(AdvancedSearch.create.parentInstance).not.toHaveBeenCalled();
      expect(vm.attr('advancedSearch.parentInstance')).not.toBeNull();
    });

    it('should NOT add "parentInstance" because isObjectContextPage is FALSE',
      () => {
        spyOn(CurrentPageUtils, 'isObjectContextPage').and.returnValue(false);
        spyOn(AdvancedSearch.create, 'parentInstance');

        vm.attr('advancedSearch.parentInstance', null);

        vm.openAdvancedFilter();

        expect(AdvancedSearch.create.parentInstance).not.toHaveBeenCalled();
        expect(vm.attr('advancedSearch.parentInstance')).toBeNull();
      }
    );

    it('should filter parentItems and exclude parentInstance', () => {
      const parentInstance = {id: 1, type: 'Audit'};
      spyOn(CurrentPageUtils, 'isObjectContextPage').and.returnValue(true);
      spyOn(AdvancedSearch.create, 'parentInstance')
        .and.returnValue({type: 'parentInstance', value: parentInstance});

      vm.attr('advancedSearch.parentInstance', null);

      vm.attr('advancedSearch.appliedParentItems', [
        {value: {id: 1, type: 'Audit'}},
        {value: {id: 2, type: 'Audit'}},
        {value: {id: 1, type: 'Program'}},
      ]);

      vm.openAdvancedFilter();

      expect(vm.attr('advancedSearch.parentItems').serialize()).toEqual([
        {value: {id: 2, type: 'Audit'}},
        {value: {id: 1, type: 'Program'}},
      ]);

      expect(vm.attr('advancedSearch.parentInstance.value').serialize())
        .toEqual({
          id: 1,
          type: 'Audit',
        });
    });
  });

  describe('applyAdvancedFilters() method', function () {
    let filterItems = new canList([
      AdvancedSearch.create.attribute(),
    ]);
    let mappingItems = new canList([
      AdvancedSearch.create.mappingCriteria({
        filter: AdvancedSearch.create.attribute(),
      }),
    ]);
    beforeEach(function () {
      vm.attr('advancedSearch.filterItems', filterItems);
      vm.attr('advancedSearch.mappingItems', mappingItems);
      vm.attr('advancedSearch.appliedFilterItems', canList());
      vm.attr('advancedSearch.appliedMappingItems', canList());
      spyOn(vm, 'onFilter');
      spyOn(AdvancedSearch, 'buildFilter')
        .and.callFake(function (items, request) {
          request.push({name: 'item'});
        });
      spyOn(QueryParser, 'joinQueries');
    });

    it('copies filter and mapping items to applied', function () {
      vm.applyAdvancedFilters();

      expect(vm.attr('advancedSearch.appliedFilterItems').attr())
        .toEqual(filterItems.attr());
      expect(vm.attr('advancedSearch.appliedMappingItems').attr())
        .toEqual(mappingItems.attr());
    });

    it('initializes advancedSearch.filter property', function () {
      QueryParser.joinQueries.and.returnValue({
        name: 'test',
      });
      vm.attr('advancedSearch.filter', null);

      vm.applyAdvancedFilters();

      expect(vm.attr('advancedSearch.filter.name')).toBe('test');
    });

    it('initializes advancedSearch.request property', function () {
      vm.attr('advancedSearch.request', canList());


      vm.applyAdvancedFilters();

      expect(vm.attr('advancedSearch.request.length')).toBe(3);
    });

    it('closes modal window', function () {
      vm.attr('advancedSearch.open', true);

      vm.applyAdvancedFilters();

      expect(vm.attr('advancedSearch.open')).toBe(false);
    });

    it('calls onFilter() method', function () {
      vm.applyAdvancedFilters();

      expect(vm.onFilter).toHaveBeenCalled();
    });
  });

  describe('removeAdvancedFilters() method', function () {
    beforeEach(function () {
      spyOn(vm, 'onFilter');
    });

    it('removes applied filter and mapping items', function () {
      vm.attr('advancedSearch.appliedFilterItems', new canList([
        {title: 'item'},
      ]));
      vm.attr('advancedSearch.appliedMappingItems', new canList([
        {title: 'item'},
      ]));

      vm.removeAdvancedFilters();

      expect(vm.attr('advancedSearch.appliedFilterItems.length')).toBe(0);
      expect(vm.attr('advancedSearch.appliedMappingItems.length')).toBe(0);
    });

    it('cleans advancedSearch.filter property', function () {
      vm.attr('advancedSearch.filter', {});

      vm.removeAdvancedFilters();

      expect(vm.attr('advancedSearch.filter')).toBe(null);
    });

    it('closes modal window', function () {
      vm.attr('advancedSearch.open', true);

      vm.removeAdvancedFilters();

      expect(vm.attr('advancedSearch.open')).toBe(false);
    });

    it('calls onFilter() method', function () {
      vm.removeAdvancedFilters();

      expect(vm.onFilter).toHaveBeenCalled();
    });

    it('resets advancedSearch.request list', function () {
      vm.attr('advancedSearch.request', new canList([{data: 'test'}]));

      vm.removeAdvancedFilters();

      expect(vm.attr('advancedSearch.request.length')).toBe(0);
    });
  });

  describe('resetAdvancedFilters() method', function () {
    it('resets filter items', function () {
      vm.attr('advancedSearch.filterItems', new canList([
        {title: 'item'},
      ]));

      vm.resetAdvancedFilters();

      expect(vm.attr('advancedSearch.filterItems.length')).toBe(0);
    });

    it('resets mapping items', function () {
      vm.attr('advancedSearch.mappingItems', new canList([
        {title: 'item'},
      ]));

      vm.resetAdvancedFilters();

      expect(vm.attr('advancedSearch.mappingItems.length')).toBe(0);
    });
  });

  describe('getAbsoluteItemNumber() method', function () {
    beforeEach(function () {
      vm.attr({
        pageInfo: {
          pageSize: 10,
          count: 5,
        },
        showedItems: [{id: 1, type: 'object'},
          {id: 2, type: 'object'},
          {id: 3, type: 'object'}],
      });
      vm.attr('pageInfo.current', 3);
    });

    it('should return correct item number when item is on page',
      function () {
        let result;

        result = vm.getAbsoluteItemNumber({id: 2, type: 'object'});

        expect(result).toEqual(21);
      });

    it('should return "-1" when item is not on page',
      function () {
        let result;

        result = vm.getAbsoluteItemNumber({id: 4, type: 'object'});

        expect(result).toEqual(-1);
      });
    it('should return "-1" when item is of different type',
      function () {
        let result;

        result = vm.getAbsoluteItemNumber({id: 3, type: 'snapshot'});

        expect(result).toEqual(-1);
      });
    it('should return correct item number for first item on non first page',
      function () {
        let result;

        result = vm.getAbsoluteItemNumber({id: 1, type: 'object'});

        expect(result).toEqual(20);
      });
  });

  describe('getRelativeItemNumber() method', function () {
    it('should return correct item number on page', function () {
      let result = vm.getRelativeItemNumber(12, 5);

      expect(result).toEqual(2);
    });
  });

  describe('getNextItemPage() method', function () {
    beforeEach(function () {
      spyOn(vm, 'loadItems');
    });

    it('should load items for appropriate page when item is not loaded',
      function () {
        vm.getNextItemPage(10, {current: 2, pageSize: 5});

        expect(vm.attr('loading')).toBeTruthy();
        expect(vm.loadItems).toHaveBeenCalled();
      });

    it('shouldn\'t load items when current item was already loaded',
      function () {
        vm.getNextItemPage(10, {current: 3, pageSize: 5});

        expect(vm.attr('loading')).toBeFalsy();
        expect(vm.loadItems).not.toHaveBeenCalled();
      });
  });

  describe('setSortingConfiguration() method', () => {
    beforeEach(() => {
      vm.attr('model', {
        model_singular: 'shortModelName',
      });
    });

    it('sets up default sorting configuration', () => {
      vm.attr('sortingInfo', {});
      spyOn(TreeViewUtils, 'getSortingForModel')
        .and.returnValue({
          key: 'key',
          direction: 'direction',
        });

      vm.setSortingConfiguration();

      expect(vm.attr('sortingInfo.sortBy')).toEqual('key');
      expect(vm.attr('sortingInfo.sortDirection')).toEqual('direction');
    });
  });

  describe('init() method', () => {
    let method;

    beforeEach(() => {
      vm.attr('model', {
        model_singular: 'shortModelName',
      });
      method = Component.prototype.init.bind({viewModel: vm});
      spyOn(vm, 'setSortingConfiguration');
      spyOn(vm, 'setColumnsConfiguration');
    });

    it('sets up columns configuration', () => {
      method();
      expect(vm.setColumnsConfiguration).toHaveBeenCalled();
    });

    it('sets up sorting configuration', () => {
      method();
      expect(vm.setSortingConfiguration).toHaveBeenCalled();
    });
  });

  describe('getDepthFilter() method', function () {
    it('returns an empty string if depth is not set for filter', function () {
      let result;
      spyOn(vm, 'attr')
        .and.returnValue([{
          query: {
            expression: {
              left: 'task assignees',
              op: {name: '='},
              right: 'user@example.com',
            },
          },
          name: 'custom',
        }, {
          query: {
            expression: {
              left: 'state',
              op: {name: '='},
              right: 'Assigned',
            },
          },
          name: 'custom',
        }]);

      result = vm.getDepthFilter();

      expect(result).toBe(null);
    });

    it('returns filter that applied for depth', function () {
      let result;
      spyOn(vm, 'attr')
        .and.returnValue([{
          query: {
            expression: {
              left: 'task assignees',
              op: {name: '='},
              right: 'user@example.com',
            },
          },
          name: 'custom',
          depth: true,
          filterDeepLimit: 2,
        }, {
          query: {
            expression: {
              left: 'state',
              op: {name: '='},
              right: 'Assigned',
            },
          },
          name: 'custom',
          depth: true,
          filterDeepLimit: 1,
        }]);

      result = vm.getDepthFilter(1);

      expect(result).toEqual({
        expression: {
          left: 'task assignees',
          op: {name: '='},
          right: 'user@example.com',
        },
      });
    });
  });

  describe('_needToRefreshAfterRelRemove() method', () => {
    let relationship;

    beforeEach(function () {
      relationship = {
        source: {},
        destination: {},
      };
      vm.attr('options.parent_instance', {
        type: 'Type',
        id: 1,
      });
    });

    describe('returns true', () => {
      it('if source of passed relationship is current instance', function () {
        const source = {
          type: 'SomeType',
          id: 12345,
        };
        vm.attr('parent_instance').attr(source);
        Object.assign(relationship.source, source);
        const result = vm._needToRefreshAfterRelRemove(relationship);
        expect(result).toBe(true);
      });

      it('if source of passed relationship is current instance', function () {
        const destination = {
          type: 'SomeType',
          id: 12345,
        };
        vm.attr('parent_instance').attr(destination);
        Object.assign(relationship.destination, destination);
        const result = vm._needToRefreshAfterRelRemove(relationship);
        expect(result).toBe(true);
      });
    });

    it('returns false when there are no need to refresh', function () {
      const result = vm._needToRefreshAfterRelRemove(relationship);
      expect(result).toBe(false);
    });
  });

  describe('_isRefreshNeeded() method', () => {
    describe('if instance is relationship then', () => {
      let instance;

      beforeEach(function () {
        instance = makeFakeInstance({model: Relationship})();
      });

      it('returns result of the relationship check', function () {
        const expectedResult = true;
        spyOn(vm, '_needToRefreshAfterRelRemove')
          .and.returnValue(expectedResult);
        const result = vm._isRefreshNeeded(instance);
        expect(result).toBe(expectedResult);
        expect(vm._needToRefreshAfterRelRemove)
          .toHaveBeenCalledWith(instance);
      });
    });

    it('returns true by default', function () {
      const result = vm._isRefreshNeeded();
      expect(result).toBe(true);
    });
  });

  describe('showLastPage() method', () => {
    beforeEach(() => {
    });

    it('assigns last page index to pageInfo.current', () => {
      const count = 711;
      vm.attr('pageInfo.count', count);
      vm.attr('pageInfo.current', count + 1);

      vm.showLastPage();

      expect(vm.attr('pageInfo.current')).toBe(count);
    });
  });

  describe('export() method', () => {
    let modelName;
    let parent;
    let filter;
    let request;
    let loadSnapshots;
    const operation = null;

    beforeEach(() => {
      spyOn(TreeViewUtils, 'startExport');
      spyOn(NotifierUtils, 'notifier');

      modelName = 'testModelName';
      parent = new canMap({testParent: true});
      filter = new canMap({testFilter: true});
      request = new canList([{testRequest: true}]);

      vm.attr('model', {
        model_singular: modelName,
      });
      vm.attr('options', {
        parent_instance: parent,
      });
      vm.attr('advancedSearch', {
        filter,
        request,
      });
    });

    it('starts export correctly', () => {
      vm.export();

      expect(TreeViewUtils.startExport).toHaveBeenCalledWith(
        modelName, parent, filter, request, loadSnapshots, operation);
    });

    it('shows info message', () => {
      vm.export();

      expect(NotifierUtils.notifier).toHaveBeenCalledWith(
        'info',
        exportMessage,
        {data: true});
    });
  });

  describe('applySavedSearch() method', () => {
    let method;

    beforeEach(() => {
      spyOn(vm, 'clearAppliedSavedSearch');
      vm.attr('filterIsDirty', false);
      vm.attr('savedSearchPermalink', '');

      method = vm.applySavedSearch.bind(vm);
    });

    it('should call "clearAppliedSavedSearch" when selectedSavedSearch is null',
      () => {
        method(null);
        expect(vm.clearAppliedSavedSearch).toHaveBeenCalled();
      }
    );

    it('should call "clearAppliedSavedSearch" when filter is dirty', () => {
      vm.attr('filterIsDirty', true);

      method({});
      expect(vm.clearAppliedSavedSearch).toHaveBeenCalled();
    });

    it('should set permalink when selectedSavedSearch is not empty ' +
    'and filter is NOT dirty', () => {
      spyOn(AdvancedSearch, 'buildSearchPermalink').and.returnValue('link');

      method(new canMap({id: 5}));
      expect(AdvancedSearch.buildSearchPermalink).toHaveBeenCalled();
      expect(vm.attr('savedSearchPermalink')).toEqual('link');
    });

    it('should set appliedSavedSearch when selectedSavedSearch is not empty ' +
    'and filter is NOT dirty', () => {
      const selectedSavedSearch = {id: 123};
      spyOn(AdvancedSearch, 'buildSearchPermalink').and.returnValue('link');

      method(new canMap(selectedSavedSearch));
      expect(vm.attr('appliedSavedSearch').serialize())
        .toEqual(selectedSavedSearch);
    });
  });

  describe('setColumnsConfiguration() method', () => {
    it('should call addServiceColumns() method', () => {
      vm.attr('model', {
        model_singular: 'test model',
      });
      spyOn(TreeViewUtils, 'getColumnsForModel')
        .and.returnValue([]);
      spyOn(vm, 'addServiceColumns');

      vm.setColumnsConfiguration();

      expect(vm.addServiceColumns).toHaveBeenCalled();
    });
  });

  describe('onUpdateColumns() method', () => {
    it('should call addServiceColumns() method', () => {
      vm.attr('model', {
        model_singular: 'test model',
      });
      spyOn(TreeViewUtils, 'setColumnsForModel')
        .and.returnValue([]);
      spyOn(vm, 'addServiceColumns');

      vm.onUpdateColumns({});

      expect(vm.addServiceColumns).toHaveBeenCalled();
    });
  });

  describe('addServiceColumns() method', () => {
    const columns = {};

    beforeEach(() => {
      columns.available = [{
        name: 'col1',
      }, {
        name: 'col2',
      }];
      columns.selected = [{
        name: 'col1',
      }, {
        name: 'col2',
      }];

      const fakeModel = makeFakeModel({
        model: Cacheable,
        staticProps: {
          model_singular: 'Person',
          tree_view_options: {
            service_attr_list: [{
              name: 'serviceCol1',
            }],
          },
        },
      });

      vm.attr('model', fakeModel);
    });

    it('should work for Persons', () => {
      vm.addServiceColumns(columns);

      const expectedOutput = {
        available: [{
          name: 'col1',
        }, {
          name: 'col2',
        }, {
          name: 'serviceCol1',
        }],
        selected: [{
          name: 'col1',
        }, {
          name: 'col2',
        }, {
          name: 'serviceCol1',
        }],
      };

      expect(columns).toEqual(expectedOutput);
    });

    it('should not work for models except Person', () => {
      const expectedOutput = {
        available: [{
          name: 'col1',
        }, {
          name: 'col2',
        }],
        selected: [{
          name: 'col1',
        }, {
          name: 'col2',
        }],
      };

      vm.attr('model', Assessment);
      vm.addServiceColumns(columns);
      expect(columns).toEqual(expectedOutput);

      vm.attr('model', Program);
      vm.addServiceColumns(columns);
      expect(columns).toEqual(expectedOutput);
    });

    it('should sort columns by order', () => {
      columns.available = [{
        name: 'col1',
      }, {
        name: 'col2',
        order: 2,
      }];
      columns.selected = [{
        name: 'col1',
      }, {
        name: 'col2',
        order: 2,
      }];

      vm.attr('model').tree_view_options.service_attr_list = [{
        name: 'serviceCol1',
        order: 1,
      }];

      const expectedOutput = {
        available: [{
          name: 'serviceCol1',
          order: 1,
        }, {
          name: 'col2',
          order: 2,
        }, {
          name: 'col1',
        }],
        selected: [{
          name: 'serviceCol1',
          order: 1,
        }, {
          name: 'col2',
          order: 2,
        }, {
          name: 'col1',
        }],
      };

      vm.addServiceColumns(columns);
      expect(columns).toEqual(expectedOutput);
    });
  });
});

describe('loadSavedSearch() function', () => {
  const viewModel = new canMap({
    router: {
      saved_search: 1,
    },
    loading: false,
    modelName: 'Control',
    advancedSearch: {},
    removeAdvancedFilters: () => {},
    applyAdvancedFilters: () => {},
  });

  let treeFunction;

  beforeAll(() => {
    treeFunction = loadSavedSearch;
  });

  it('should set "loading" flag to true while loading', (done) => {
    let dfd = $.Deferred();

    spyOn(SavedSearch, 'findOne').and.returnValue(dfd);

    let loadDfd = treeFunction(viewModel);
    expect(viewModel.attr('loading')).toBeTruthy();

    loadDfd.then(() => {
      expect(viewModel.attr('loading')).toBeFalsy();
      done();
    });

    dfd.resolve({});
  });

  it('should call "removeAdvancedFilters" when search response is null',
    (done) => {
      let dfd = $.Deferred();

      spyOn(SavedSearch, 'findOne').and.returnValue(dfd);
      spyOn(viewModel, 'removeAdvancedFilters');

      treeFunction(viewModel).then(() => {
        expect(viewModel.removeAdvancedFilters).toHaveBeenCalled();
        done();
      });

      dfd.resolve({SavedSearch: null});
    }
  );

  it('should call "removeAdvancedFilters" when search is NOT AdvancedSearch',
    (done) => {
      let dfd = $.Deferred();

      spyOn(SavedSearch, 'findOne').and.returnValue(dfd);
      spyOn(viewModel, 'removeAdvancedFilters');

      treeFunction(viewModel).then(() => {
        expect(viewModel.removeAdvancedFilters).toHaveBeenCalled();
        done();
      });

      dfd.resolve({SavedSearch: {
        search_type: 'GlobalSearch',
        object_type: 'Control',
      }});
    }
  );

  it('should call "removeAdvancedFilters" when search.object_type' +
  ' is NOT equal to viewModel.modelName',
  (done) => {
    let dfd = $.Deferred();

    spyOn(SavedSearch, 'findOne').and.returnValue(dfd);
    spyOn(viewModel, 'removeAdvancedFilters');

    treeFunction(viewModel).then(() => {
      expect(viewModel.removeAdvancedFilters).toHaveBeenCalled();
      done();
    });

    dfd.resolve({SavedSearch: {
      search_type: 'AdvancedSearch',
      object_type: 'Regulation',
    }});
  });

  it('should call "removeAdvancedFilters" when search loading was failed',
    (done) => {
      let dfd = $.Deferred();

      spyOn(SavedSearch, 'findOne').and.returnValue(dfd);
      spyOn(viewModel, 'removeAdvancedFilters');

      treeFunction(viewModel).fail(() => {
        expect(viewModel.removeAdvancedFilters).toHaveBeenCalled();
        done();
      });

      dfd.reject();
    }
  );

  it('should call "applyAdvancedFilters" when search appropriate to viewModel',
    (done) => {
      let dfd = $.Deferred();

      spyOn(SavedSearch, 'findOne').and.returnValue(dfd);
      spyOn(viewModel, 'applyAdvancedFilters');
      spyOn(AdvancedSearch, 'parseFilterJson');

      treeFunction(viewModel).then(() => {
        expect(viewModel.applyAdvancedFilters).toHaveBeenCalled();
        done();
      });

      dfd.resolve({SavedSearch: {
        search_type: 'AdvancedSearch',
        object_type: 'Control',
      }});
    }
  );
});

describe('filterParentItems() method', () => {
  it('should exclude parentInstance from parentItem', () => {
    const parentInstance = {
      value: {
        id: 5,
        type: 'Control',
      },
    };

    const parentItems = [
      {value: {id: 7, type: 'Regulation'}},
      {value: {id: 5, type: 'Regulation'}},
      {value: {id: 5, type: 'Control'}},
      {value: {id: 6, type: 'Control'}},
    ];

    const result = filterParentItems(parentInstance, parentItems);
    expect(result).toEqual([
      {value: {id: 7, type: 'Regulation'}},
      {value: {id: 5, type: 'Regulation'}},
      {value: {id: 6, type: 'Control'}},
    ]);
  });
});
