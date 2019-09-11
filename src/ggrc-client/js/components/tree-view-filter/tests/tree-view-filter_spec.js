/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canList from 'can-list';
import canMap from 'can-map';
import {getComponentVM} from '../../../../js_specs/spec_helpers';
import Component, {loadSavedSearch, filterParentItems} from '../tree-view-filter';
import * as AdvancedSearch from '../../../plugins/utils/advanced-search-utils';
import * as CurrentPageUtils from '../../../plugins/utils/current-page-utils';
import * as StateUtils from '../../../plugins/utils/state-utils';
import QueryParser from '../../../generated/ggrc_filter_query_parser';
import SavedSearch from '../../../models/service-models/saved-search';
import * as QueryApiUtils from '../../../plugins/utils/query-api-utils';
import Control from '../../../models/business-models/control';

describe('tree-view-filter component', () => {
  let viewModel;

  beforeAll(() => {
    viewModel = getComponentVM(Component);
  });

  describe('openAdvancedFilter() method', () => {
    it('copies applied filter and mapping items', () => {
      let appliedFilterItems = new canList([
        AdvancedSearch.create.attribute(),
      ]);
      let appliedMappingItems = new canList([
        AdvancedSearch.create.mappingCriteria({
          filter: AdvancedSearch.create.attribute(),
        }),
      ]);
      viewModel.attr('advancedSearch.appliedFilterItems', appliedFilterItems);
      viewModel.attr('advancedSearch.appliedMappingItems', appliedMappingItems);
      viewModel.attr('advancedSearch.filterItems', canList());
      viewModel.attr('advancedSearch.mappingItems', canList());

      viewModel.openAdvancedFilter();

      expect(viewModel.attr('advancedSearch.filterItems').attr())
        .toEqual(appliedFilterItems.attr());
      expect(viewModel.attr('advancedSearch.mappingItems').attr())
        .toEqual(appliedMappingItems.attr());
    });

    it('opens modal window', () => {
      viewModel.attr('advancedSearch.open', false);

      viewModel.openAdvancedFilter();

      expect(viewModel.attr('advancedSearch.open')).toBe(true);
    });

    it('should add "parentInstance" when isObjectContextPage is TRUE' +
    'and "parentInstance" is empty', () => {
      const parentInstance = {id: 1, type: 'Audit'};
      spyOn(CurrentPageUtils, 'isObjectContextPage').and.returnValue(true);
      spyOn(AdvancedSearch.create, 'parentInstance')
        .and.returnValue({type: 'parentInstance', value: parentInstance});

      viewModel.attr('advancedSearch.parentInstance', null);

      viewModel.openAdvancedFilter();

      expect(AdvancedSearch.create.parentInstance).toHaveBeenCalled();
      expect(viewModel.attr('advancedSearch.parentInstance.value').serialize())
        .toEqual(parentInstance);
    });

    it('should NOT add "parentInstance" because it already set', () => {
      spyOn(CurrentPageUtils, 'isObjectContextPage').and.returnValue(true);
      spyOn(AdvancedSearch.create, 'parentInstance');

      viewModel.attr('advancedSearch.parentInstance', {id: 1});

      viewModel.openAdvancedFilter();

      expect(AdvancedSearch.create.parentInstance).not.toHaveBeenCalled();
      expect(viewModel.attr('advancedSearch.parentInstance')).not.toBeNull();
    });

    it('should NOT add "parentInstance" because isObjectContextPage is FALSE',
      () => {
        spyOn(CurrentPageUtils, 'isObjectContextPage').and.returnValue(false);
        spyOn(AdvancedSearch.create, 'parentInstance');

        viewModel.attr('advancedSearch.parentInstance', null);

        viewModel.openAdvancedFilter();

        expect(AdvancedSearch.create.parentInstance).not.toHaveBeenCalled();
        expect(viewModel.attr('advancedSearch.parentInstance')).toBeNull();
      }
    );

    it('should filter parentItems and exclude parentInstance', () => {
      const parentInstance = {id: 1, type: 'Audit'};
      spyOn(CurrentPageUtils, 'isObjectContextPage').and.returnValue(true);
      spyOn(AdvancedSearch.create, 'parentInstance')
        .and.returnValue({type: 'parentInstance', value: parentInstance});

      viewModel.attr('advancedSearch.parentInstance', null);

      viewModel.attr('advancedSearch.appliedParentItems', [
        {value: {id: 1, type: 'Audit'}},
        {value: {id: 2, type: 'Audit'}},
        {value: {id: 1, type: 'Program'}},
      ]);

      viewModel.openAdvancedFilter();

      expect(viewModel.attr('advancedSearch.parentItems').serialize()).toEqual([
        {value: {id: 2, type: 'Audit'}},
        {value: {id: 1, type: 'Program'}},
      ]);

      expect(viewModel.attr('advancedSearch.parentInstance.value').serialize())
        .toEqual({
          id: 1,
          type: 'Audit',
        });
    });
  });

  describe('applyAdvancedFilters() method', () => {
    let filterItems = new canList([
      AdvancedSearch.create.attribute(),
    ]);
    let mappingItems = new canList([
      AdvancedSearch.create.mappingCriteria({
        filter: AdvancedSearch.create.attribute(),
      }),
    ]);
    beforeEach(() => {
      viewModel.attr('advancedSearch.filterItems', filterItems);
      viewModel.attr('advancedSearch.mappingItems', mappingItems);
      viewModel.attr('advancedSearch.appliedFilterItems', canList());
      viewModel.attr('advancedSearch.appliedMappingItems', canList());
      spyOn(viewModel, 'onFilter');
      spyOn(AdvancedSearch, 'buildFilter')
        .and.callFake((items, request) => {
          request.push({name: 'item'});
        });
      spyOn(QueryParser, 'joinQueries');
    });

    it('copies filter and mapping items to applied', () => {
      viewModel.applyAdvancedFilters();

      expect(viewModel.attr('advancedSearch.appliedFilterItems').attr())
        .toEqual(filterItems.attr());
      expect(viewModel.attr('advancedSearch.appliedMappingItems').attr())
        .toEqual(mappingItems.attr());
    });

    it('initializes advancedSearch.filter property', () => {
      QueryParser.joinQueries.and.returnValue({
        name: 'test',
      });
      viewModel.attr('advancedSearch.filter', null);

      viewModel.applyAdvancedFilters();

      expect(viewModel.attr('advancedSearch.filter.name')).toBe('test');
    });

    it('initializes advancedSearch.request property', () => {
      viewModel.attr('advancedSearch.request', canList());


      viewModel.applyAdvancedFilters();

      expect(viewModel.attr('advancedSearch.request.length')).toBe(3);
    });

    it('closes modal window', () => {
      viewModel.attr('advancedSearch.open', true);

      viewModel.applyAdvancedFilters();

      expect(viewModel.attr('advancedSearch.open')).toBe(false);
    });

    it('calls onFilter() method', () => {
      viewModel.applyAdvancedFilters();

      expect(viewModel.onFilter).toHaveBeenCalled();
    });
  });

  describe('removeAdvancedFilters() method', () => {
    beforeAll(() => {
      spyOn(viewModel, 'onFilter');
    });

    it('removes applied filter and mapping items', () => {
      viewModel.attr('advancedSearch.appliedFilterItems', new canList([
        {title: 'item'},
      ]));
      viewModel.attr('advancedSearch.appliedMappingItems', new canList([
        {title: 'item'},
      ]));

      viewModel.removeAdvancedFilters();

      expect(viewModel.attr('advancedSearch.appliedFilterItems.length'))
        .toBe(0);
      expect(viewModel.attr('advancedSearch.appliedMappingItems.length'))
        .toBe(0);
    });

    it('cleans advancedSearch.filter property', () => {
      viewModel.attr('advancedSearch.filter', {});
      viewModel.removeAdvancedFilters();

      expect(viewModel.attr('advancedSearch.filter')).toBe(null);
    });

    it('closes modal window', () => {
      viewModel.attr('advancedSearch.open', true);
      viewModel.removeAdvancedFilters();

      expect(viewModel.attr('advancedSearch.open')).toBe(false);
    });

    it('calls onFilter() method', () => {
      viewModel.removeAdvancedFilters();

      expect(viewModel.onFilter).toHaveBeenCalled();
    });

    it('resets advancedSearch.request list', () => {
      viewModel.attr('advancedSearch.request', new canList([{data: 'test'}]));
      viewModel.removeAdvancedFilters();

      expect(viewModel.attr('advancedSearch.request.length')).toBe(0);
    });
  });

  describe('resetAdvancedFilters() method', () => {
    it('resets filter items', () => {
      viewModel.attr('advancedSearch.filterItems', new canList([
        {title: 'item'},
      ]));

      viewModel.resetAdvancedFilters();

      expect(viewModel.attr('advancedSearch.filterItems.length')).toBe(0);
    });

    it('resets mapping items', () => {
      viewModel.attr('advancedSearch.mappingItems', new canList([
        {title: 'item'},
      ]));

      viewModel.resetAdvancedFilters();

      expect(viewModel.attr('advancedSearch.mappingItems.length')).toBe(0);
    });
  });

  describe('treeFilterReady() method', () => {
    beforeEach(() => {
      viewModel.attr('shouldWaitForFilters', true);
      viewModel.attr('filtersReady', new Set());
      viewModel.attr('model', Control);
      spyOn(viewModel, 'onFilter');
    });

    it('should NOT call "onFilter" method after 1 call', () => {
      spyOn(StateUtils, 'hasFilter').and.returnValue(true);
      viewModel.treeFilterReady({filterName: 'some filter #1'});
      expect(viewModel.onFilter).not.toHaveBeenCalled();
    });

    it('should call "onFilter" method when filterNames are NOT ' +
    'uniq after 2 calls', () => {
      spyOn(StateUtils, 'hasFilter').and.returnValue(true);
      viewModel.treeFilterReady({filterName: 'some filter #1'});
      expect(viewModel.onFilter).not.toHaveBeenCalled();
      viewModel.treeFilterReady({filterName: 'some filter #1'});
      expect(viewModel.onFilter).not.toHaveBeenCalled();
    });

    it('should call "onFilter" method when filterNames are uniq after 2 calls',
      () => {
        spyOn(StateUtils, 'hasFilter').and.returnValue(true);
        viewModel.treeFilterReady({filterName: 'some filter #1'});
        expect(viewModel.onFilter).not.toHaveBeenCalled();
        viewModel.treeFilterReady({filterName: 'some filter #2'});
        expect(viewModel.onFilter).toHaveBeenCalled();
      }
    );

    it('should NOT call "onFilter" method when filterNames are ' +
    'uniq after 2 calls, but shouldWaitForFilters is false', () => {
      spyOn(StateUtils, 'hasFilter').and.returnValue(true);
      viewModel.attr('shouldWaitForFilters', false);
      viewModel.treeFilterReady({filterName: 'some filter #1'});
      expect(viewModel.onFilter).not.toHaveBeenCalled();
      viewModel.treeFilterReady({filterName: 'some filter #2'});
      expect(viewModel.onFilter).not.toHaveBeenCalled();
    });

    it('should call "onFilter" method after 1 call when tree view ' +
    'does NOT have status filter', () => {
      spyOn(StateUtils, 'hasFilter').and.returnValue(false);
      viewModel.treeFilterReady({filterName: 'some filter #1'});
      expect(viewModel.onFilter).toHaveBeenCalled();
    });
  });

  describe('applySavedSearch() method', () => {
    let method;

    beforeEach(() => {
      spyOn(viewModel, 'clearAppliedSavedSearch');
      viewModel.attr('filterIsDirty', false);
      viewModel.attr('savedSearchPermalink', '');

      method = viewModel.applySavedSearch.bind(viewModel);
    });

    it('should call "clearAppliedSavedSearch" when selectedSavedSearch is null',
      () => {
        method(null);
        expect(viewModel.clearAppliedSavedSearch).toHaveBeenCalled();
      }
    );

    it('should call "clearAppliedSavedSearch" when filter is dirty', () => {
      viewModel.attr('filterIsDirty', true);

      method({});
      expect(viewModel.clearAppliedSavedSearch).toHaveBeenCalled();
    });

    it('should set permalink when selectedSavedSearch is not empty ' +
    'and filter is NOT dirty', () => {
      spyOn(AdvancedSearch, 'buildSearchPermalink').and.returnValue('link');

      method(new canMap({id: 5}));
      expect(AdvancedSearch.buildSearchPermalink).toHaveBeenCalled();
      expect(viewModel.attr('savedSearchPermalink')).toEqual('link');
    });

    it('should set appliedSavedSearch when selectedSavedSearch is not empty ' +
    'and filter is NOT dirty', () => {
      const selectedSavedSearch = {id: 123};
      spyOn(AdvancedSearch, 'buildSearchPermalink').and.returnValue('link');

      method(new canMap(selectedSavedSearch));
      expect(viewModel.attr('appliedSavedSearch').serialize())
        .toEqual(selectedSavedSearch);
    });
  });

  describe('searchQueryChanged() method', () => {
    let method;

    beforeAll(() => {
      method = viewModel.searchQueryChanged.bind(viewModel);
      spyOn(viewModel, 'updateCurrentFilter');
    });

    it('should add filter because "filters" doesn\'t contain filter', () => {
      viewModel.attr('filters', []);

      const filter = {
        name: 'my new filter',
        query: {left: 'title', op: {name: '~'}, right: 'my title'},
      };

      method(filter);
      expect(viewModel.attr('filters')[0].serialize()).toEqual(filter);
    });

    it('should update filter because "filters" contains that one', () => {
      viewModel.attr('filters', [{
        name: 'my new filter',
        query: null,
      }]);

      const filter = {
        name: 'my new filter',
        query: {left: 'title', op: {name: '~'}, right: 'my title'},
      };

      method(filter);
      expect(viewModel.attr('filters')[0].serialize()).toEqual(filter);
    });

    it('should call "updateCurrentFilter" method', () => {
      method({name: 'my name', query: null});
      expect(viewModel.updateCurrentFilter).toHaveBeenCalled();
    });
  });

  describe('updateCurrentFilter() method', () => {
    let method;

    beforeAll(() => {
      method = viewModel.updateCurrentFilter.bind(viewModel);
    });

    beforeEach(() => {
      viewModel.attr('currentFilter', null);
    });

    it('should set "currentFilter" from advancedSearch filter ' +
    'when it isn\t empty', () => {
      viewModel.attr('additionalFilter', 'some filter');

      const advancedSearch = {
        filter: {
          expression: {
            left: 'Status',
            op: {name: 'IN'},
            right: ['Active'],
          },
        },
        request: [{query: null}],
      };

      viewModel.attr('advancedSearch', advancedSearch);

      method();
      expect(viewModel.attr('currentFilter.filter').serialize())
        .toEqual(advancedSearch.filter);
      expect(viewModel.attr('currentFilter.request').serialize())
        .toEqual(advancedSearch.request);
    });

    it('should set "currentFilter" from additionalFilter ' +
    'when advancedSearch filter is empty', () => {
      viewModel.attr('filters', []);
      viewModel.attr('additionalFilter', 'some filter');

      const advancedSearch = {
        filter: null,
        request: [{query: null}],
      };

      viewModel.attr('advancedSearch', advancedSearch);

      spyOn(QueryParser, 'parse').and.returnValue({
        query: 'some additional query',
      });

      method();

      expect(viewModel.attr('currentFilter.filter').serialize())
        .toEqual({
          query: 'some additional query',
        });
      expect(viewModel.attr('currentFilter.request').serialize())
        .toEqual(advancedSearch.request);
    });

    it('should call "QueryParser.parse" when additionalFilter is NOT empty' +
    'advanced advancedSearch filter is empty', () => {
      viewModel.attr('additionalFilter', 'some additional query');
      viewModel.attr('advancedSearch', null);

      spyOn(QueryParser, 'parse');
      method();

      expect(QueryParser.parse).toHaveBeenCalledWith(
        viewModel.attr('additionalFilter')
      );
    });

    it('should call "concatFilters" util when additionalFilter and "filter"' +
    'are NOT empty', () => {
      viewModel.attr('filters', [{
        name: 'myFilter',
        query: {left: 'title', op: {name: '~'}, right: 'my title'},
      }]);

      viewModel.attr('additionalFilter', 'some additional query');
      viewModel.attr('advancedSearch', null);

      spyOn(QueryParser, 'parse').and.returnValue({
        query: 'some additional query',
      });
      spyOn(QueryApiUtils, 'concatFilters');

      method();

      expect(QueryApiUtils.concatFilters).toHaveBeenCalled();
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
