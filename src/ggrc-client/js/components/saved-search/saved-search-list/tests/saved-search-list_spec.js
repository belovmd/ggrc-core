/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import canMap from 'can-map';
import Component from '../saved-search-list';
import {
  getComponentVM,
  makeFakeInstance,
} from '../../../../../js_specs/spec_helpers';
import * as AdvancedSearchUtils
  from '../../../../plugins/utils/advanced-search-utils';
import pubSub from '../../../../pub-sub';
import Control from '../../../../models/business-models/control';
import SavedSearch from '../../../../models/service-models/saved-search';

describe('saved-search-list component', () => {
  let viewModel;

  beforeAll(() => {
    viewModel = getComponentVM(Component);
    viewModel.attr('searchType', 'AdvancedSearch');
  });

  describe('selectSearch() method', () => {
    const parsedFilterJson = {
      filterItems: [{type: 'state'}],
      mappingItems: [],
      parentItems: [],
      statusItem: null,
    };

    let method;

    beforeAll(() => {
      spyOn(AdvancedSearchUtils, 'parseFilterJson')
        .and.returnValue(parsedFilterJson);
      spyOn(pubSub, 'dispatch');

      method = viewModel.selectSearch.bind(viewModel);
    });

    it('should call "dispatch"', () => {
      method({id: 5});
      expect(pubSub.dispatch).toHaveBeenCalledWith({
        type: 'savedSearchSelected',
        savedSearch: {
          ...parsedFilterJson,
          id: 5,
        },
        searchType: viewModel.attr('searchType'),
      });
    });

    it('should set "modelName" and "modelDisplayName" from model', () => {
      const controlInstance = makeFakeInstance({model: Control})({});
      const search = {object_type: 'Control', id: 5};
      method(search);

      expect(pubSub.dispatch).toHaveBeenCalledWith({
        type: 'savedSearchSelected',
        savedSearch: {
          ...parsedFilterJson,
          id: search.id,
          modelName: controlInstance.constructor.model_singular,
          modelDisplayName: controlInstance.constructor.title_plural,
        },
        searchType: viewModel.attr('searchType'),
      });
    });

    it('should set "selectedSearchId" from search id', () => {
      const expectedId = 5;
      method({id: expectedId});

      expect(viewModel.attr('selectedSearchId')).toBe(expectedId);
    });
  });

  describe('loadSavedSearches() method', () => {
    let method;

    beforeAll(() => {
      method = viewModel.loadSavedSearches.bind(viewModel);
    });

    it('should set "searches" and "total" from response', (done) => {
      const dfd = $.Deferred();
      const expectedSearches = [{id: 123}, {id: 5}];
      const responseData = {total: 2, values: expectedSearches};

      viewModel.attr('searches', []);

      spyOn(SavedSearch, 'findBy').and.returnValue(dfd);
      method();

      dfd.resolve(responseData).then(() => {
        expect(viewModel.attr('searches').serialize())
          .toEqual(expectedSearches);
        expect(viewModel.attr('searchesPaging.total')).toBe(2);
        done();
      });
    });

    it('should set "isLoading" to true before response and ' +
      'set "isLoading" to false after response', (done) => {
      const dfd = $.Deferred();
      spyOn(SavedSearch, 'findBy').and.returnValue(dfd);

      expect(viewModel.attr('isLoading')).toBeFalsy();
      method();
      expect(viewModel.attr('isLoading')).toBeTruthy();

      dfd.resolve({total: 0, values: []}).then(() => {
        expect(viewModel.attr('isLoading')).toBeFalsy();
        done();
      });
    });

    it('should NOT send objectType for global search', () => {
      const dfd = $.Deferred();

      viewModel.attr('searchType', 'GlobalSearch');
      viewModel.attr('searchesPaging', {current: 10});
      viewModel.attr('objectType', 'Control');

      spyOn(SavedSearch, 'findBy').and.returnValue(dfd);

      method();
      expect(SavedSearch.findBy).toHaveBeenCalledWith(
        'GlobalSearch',
        viewModel.attr('searchesPaging'),
        null
      );
    });

    it('should set objectType for advanced search', () => {
      const dfd = $.Deferred();
      const expectedObjectType = 'Control';

      viewModel.attr('searchType', 'AdvancedSearch');
      viewModel.attr('searchesPaging', {current: 10});
      viewModel.attr('objectType', expectedObjectType);

      spyOn(SavedSearch, 'findBy').and.returnValue(dfd);

      method();
      expect(SavedSearch.findBy).toHaveBeenCalledWith(
        'AdvancedSearch',
        viewModel.attr('searchesPaging'),
        expectedObjectType,
      );
    });
  });

  describe('removeSearch() method', () => {
    let method;

    beforeEach(() => {
      spyOn(viewModel, 'loadSavedSearches');
      spyOn(SavedSearch.prototype, 'destroy')
        .and.returnValue($.Deferred().resolve());

      method = viewModel.removeSearch.bind(viewModel);
    });

    it('should decrease count of searches', (done) => {
      const searchInstance = makeFakeInstance({model: SavedSearch})({id: 11});

      method(searchInstance, {stopPropagation: () => {}}).done(() => {
        expect(searchInstance.destroy).toHaveBeenCalled();
        done();
      });
    });

    it('should decrease current page when searches.length == 1', (done) => {
      const currentPage = 6;
      const expectedCurrentPage = 5;
      const searchInstance = makeFakeInstance({model: SavedSearch})({});

      viewModel.attr('searchesPaging', {current: currentPage});
      // Only one search on the page
      viewModel.attr('searches', [{id: 11}]);

      method(searchInstance, {stopPropagation: () => {}}).done(() => {
        expect(viewModel.attr('searchesPaging.current'))
          .toBe(expectedCurrentPage);
        expect(viewModel.loadSavedSearches).not.toHaveBeenCalled();
        done();
      });
    });

    it('should NOT decrease current page when searches.length > 1', (done) => {
      const currentPage = 6;
      const searchInstance = makeFakeInstance({model: SavedSearch})({});

      viewModel.attr('searchesPaging', {current: currentPage});
      // 2 searches on the page
      viewModel.attr('searches', [{id: 11}, {id: 22}]);

      method(searchInstance, {stopPropagation: () => {}}).done(() => {
        expect(viewModel.attr('searchesPaging.current')).toBe(currentPage);
        expect(viewModel.loadSavedSearches).toHaveBeenCalled();
        done();
      });
    });
  });

  describe('permalinkBuilder() helper', () => {
    let helper;
    const widgetId = 'regulation';
    const vm = new canMap({widgetId});
    const helperOptions = {
      fn: () => {},
    };
    const builtPermalink = 'https://my-website.net';

    beforeAll(() => {
      spyOn(AdvancedSearchUtils, 'buildSearchPermalink')
        .and.returnValue(builtPermalink);
      spyOn(helperOptions, 'fn');

      helper = Component.prototype.helpers.permalinkBuilder
        .bind(vm);
    });

    it('should call buildSearchPermalink when savedSearch is object', () => {
      const savedSearch = {id: 12345};
      helper(savedSearch, helperOptions);

      expect(AdvancedSearchUtils.buildSearchPermalink)
        .toHaveBeenCalledWith(savedSearch.id, widgetId);

      expect(helperOptions.fn).toHaveBeenCalledWith({
        permalink: builtPermalink,
      });
    });

    it('should call buildSearchPermalink when savedSearch is function', () => {
      const savedSearch = () => {
        return {id: 12345};
      };

      helper(savedSearch, helperOptions);

      expect(AdvancedSearchUtils.buildSearchPermalink)
        .toHaveBeenCalledWith(savedSearch().id, widgetId);

      expect(helperOptions.fn).toHaveBeenCalledWith({
        permalink: builtPermalink,
      });
    });
  });
});
