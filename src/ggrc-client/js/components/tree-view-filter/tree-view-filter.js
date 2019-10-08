/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canStache from 'can-stache';
import canList from 'can-list';
import canMap from 'can-map';
import canComponent from 'can-component';
import makeArray from 'can-util/js/make-array/make-array';
import template from './templates/tree-view-filter.stache';
import {hasFilter} from '../../plugins/utils/state-utils';
import QueryParser from '../../generated/ggrc_filter_query_parser';
import * as AdvancedSearch from '../../plugins/utils/advanced-search-utils';
import SavedSearch from '../../models/service-models/saved-search';
import {notifier} from '../../plugins/utils/notifiers-utils';
import router from '../../router';
import pubSub from '../../pub-sub';
import {
  isObjectContextPage,
  isAllObjects,
  isMyWork,
} from '../../plugins/utils/current-page-utils';
import {concatFilters} from '../../plugins/utils/query-api-utils';

import '../tree/tree-filter-input';
import '../tree/tree-status-filter';
import '../advanced-search/advanced-search-mapping-container';
import '../advanced-search/advanced-search-filter-container';
import '../dropdown/multiselect-dropdown';
import '../saved-search/saved-search-list/saved-search-list';
import '../saved-search/create-saved-search/create-saved-search';
import '../simple-modal/simple-modal';

const EXPECTED_FILTERS_COUNT = 2;

export default canComponent.extend({
  tag: 'tree-view-filter',
  view: canStache(template),
  leakScope: false,
  viewModel: canMap.extend({
    define: {
      modelName: {
        get() {
          return this.attr('model').model_singular;
        },
      },
      statusFilterVisible: {
        get() {
          return hasFilter(this.attr('modelName'));
        },
      },
      isSavedSearchShown: {
        get() {
          if (isMyWork()) {
            // do NOT show Advanced saved search list on Dashboard page
            return false;
          }

          if (isAllObjects() &&
            this.model.model_plural === 'CycleTaskGroupObjectTasks') {
            // do NOT show Advanced saved search list on AllOjbects page (Tasks tab)
            return false;
          }

          return true;
        },
      },
      selectedSavedSearchId: {
        get() {
          if (this.attr('filterIsDirty')) {
            return;
          }

          return this.attr('advancedSearch.selectedSavedSearch.id') ||
            this.attr('appliedSavedSearch.id');
        },
      },
      savedSearchPermalink: {
        set(value) {
          pubSub.dispatch({
            type: 'savedSearchPermalinkSet',
            permalink: value,
            widgetId: this.attr('widgetId'),
          });
          return value;
        },
      },
      filtersReady: {
        value() {
          return new Set();
        },
      },
    },
    pubSub,
    router,
    model: null,
    filters: [],
    appliedSavedSearch: {},
    filterIsDirty: false,
    columns: null,
    widgetId: null,
    additionalFilter: null,
    currentFilter: {},
    shouldWaitForFilters: true,
    parentInstance: null,
    advancedSearch: {
      open: false,
      filter: null,
      request: canList(),
      filterItems: canList(),
      appliedFilterItems: canList(),
      mappingItems: canList(),
      appliedMappingItems: canList(),
      parentItems: canList(),
      appliedParentItems: canList(),
      parentInstance: null,
    },
    searchQueryChanged({name, query}) {
      const filter = makeArray(this.attr('filters'))
        .find((item) => item.name === name);
      if (filter) {
        filter.attr('query', query);
      } else {
        this.attr('filters').push(new canMap({name, query}));
      }

      this.updateCurrentFilter();
    },
    treeFilterReady({filterName}) {
      if (!this.attr('shouldWaitForFilters')) {
        return;
      }

      const filtersReady = this.attr('filtersReady');

      // tree-status-filter is hidden. Mark it as already ready
      if (!this.attr('statusFilterVisible')) {
        filtersReady.add('tree-status-filter');
      }

      filtersReady.add(filterName);

      if (filtersReady.size === EXPECTED_FILTERS_COUNT) {
        this.onFilter();
      }
    },
    onFilter() {
      this.dispatch('onFilter');
    },
    openAdvancedFilter() {
      const advancedSearch = this.attr('advancedSearch');

      // serialize "appliedFilterItems" before set to prevent changing of
      // "appliedFilterItems" object by changing of "filterItems" object.
      // Without "serialization" we copy reference of "appliedFilterItems" to "filterItems".
      advancedSearch.attr('filterItems',
        advancedSearch.attr('appliedFilterItems').serialize());

      advancedSearch.attr('mappingItems',
        advancedSearch.attr('appliedMappingItems').serialize());

      advancedSearch.attr('parentItems',
        advancedSearch.attr('appliedParentItems').serialize());

      if (isObjectContextPage() && !advancedSearch.attr('parentInstance')) {
        advancedSearch.attr('parentInstance',
          AdvancedSearch.create.parentInstance(this.attr('parentInstance')));

        // remove duplicates
        const parentItems = filterParentItems(
          advancedSearch.attr('parentInstance'),
          advancedSearch.attr('parentItems'));

        advancedSearch.attr('parentItems', parentItems);
      }

      advancedSearch.attr('open', true);
      this.attr('filterIsDirty', false);
    },
    clearAppliedSavedSearch() {
      this.attr('advancedSearch.selectedSavedSearch', null);
      this.attr('savedSearchPermalink', null);
      this.attr('appliedSavedSearch', null);
    },
    applySavedSearch(selectedSavedSearch) {
      if (!selectedSavedSearch || this.attr('filterIsDirty')) {
        this.clearAppliedSavedSearch();
        return;
      }

      const widgetId = this.attr('widgetId');
      const permalink = AdvancedSearch
        .buildSearchPermalink(selectedSavedSearch.id, widgetId);

      this.attr('savedSearchPermalink', permalink);
      this.attr('appliedSavedSearch', selectedSavedSearch.serialize());
    },
    applyAdvancedFilters() {
      const filters = this.attr('advancedSearch.filterItems').serialize();
      const mappings = this.attr('advancedSearch.mappingItems').serialize();
      const parents = this.attr('advancedSearch.parentItems').serialize();
      let request = canList();

      this.attr('advancedSearch.appliedFilterItems', filters);
      this.attr('advancedSearch.appliedMappingItems', mappings);
      this.attr('advancedSearch.appliedParentItems', parents);

      const builtFilters = AdvancedSearch.buildFilter(filters, request);
      const builtMappings = AdvancedSearch.buildFilter(mappings, request);
      const builtParents = AdvancedSearch.buildFilter(parents, request);
      let advancedFilters =
        QueryParser.joinQueries(builtFilters, builtMappings);
      advancedFilters = QueryParser.joinQueries(advancedFilters, builtParents);

      this.attr('advancedSearch.request', request);
      this.attr('advancedSearch.filter', advancedFilters);
      this.attr('advancedSearch.open', false);

      this.applySavedSearch(
        this.attr('advancedSearch.selectedSavedSearch')
      );
      this.onFilter();
    },
    removeAdvancedFilters() {
      this.attr('advancedSearch.appliedFilterItems', canList());
      this.attr('advancedSearch.appliedMappingItems', canList());
      this.attr('advancedSearch.request', canList());
      this.attr('advancedSearch.filter', null);
      this.attr('advancedSearch.open', false);
      this.clearAppliedSavedSearch();
      this.onFilter();
    },
    resetAdvancedFilters() {
      this.attr('advancedSearch.filterItems', canList());
      this.attr('advancedSearch.mappingItems', canList());
      this.attr('advancedSearch.parentItems', canList());
    },
    searchModalClosed() {
      this.attr('advancedSearch.selectedSavedSearch', null);
    },
    updateCurrentFilter() {
      const filters = makeArray(this.attr('filters'));
      let additionalFilter = this.attr('additionalFilter');
      let advancedSearchFilter = this.attr('advancedSearch.filter');
      let advancedSearchRequest = this.attr('advancedSearch.request');

      if (advancedSearchFilter && advancedSearchFilter.serialize) {
        this.attr('currentFilter', {
          filter: advancedSearchFilter.serialize(),
          request: advancedSearchRequest,
        });
        return;
      }

      if (additionalFilter) {
        additionalFilter = QueryParser.parse(additionalFilter);
      }

      const filter = filters
        .filter((options) => options.query)
        .reduce(concatFilters, additionalFilter);

      this.attr('currentFilter', {
        filter,
        request: advancedSearchRequest,
      });
    },
  }),
  events: {
    inserted() {
      if (isLoadSavedSearch(this.viewModel)) {
        loadSavedSearch(this.viewModel);
        this.viewModel.attr('shouldWaitForFilters', false);
      }
    },
    '{viewModel.advancedSearch} selectedSavedSearch'() {
      // applied saved search filter. Current filter is NOT dirty
      this.viewModel.attr('filterIsDirty', false);
    },
    '{viewModel.advancedSearch.filterItems} change'() {
      // filterItems changed. Current filter is dirty
      this.viewModel.attr('filterIsDirty', true);
    },
    '{viewModel.advancedSearch.mappingItems} change'() {
      // mappingItems changed. Current filter is dirty
      this.viewModel.attr('filterIsDirty', true);
    },
    '{viewModel.router} saved_search'() {
      if (isLoadSavedSearch(this.viewModel)) {
        loadSavedSearch(this.viewModel);
      }
    },
    '{viewModel.advancedSearch} change'() {
      this.viewModel.updateCurrentFilter();
    },
    '{pubSub} savedSearchSelected'(pubSub, ev) {
      const currentModelName = this.viewModel.attr('modelName');
      const isCurrentModelName = currentModelName === ev.savedSearch.modelName;
      if (ev.searchType !== 'AdvancedSearch' || !isCurrentModelName) {
        return;
      }

      selectSavedSearchFilter(
        this.viewModel.attr('advancedSearch'),
        ev.savedSearch
      );
    },
  },
});

const isLoadSavedSearch = (viewModel) => {
  return !!viewModel.attr('router.saved_search');
};

const processNotExistedSearch = (viewModel) => {
  notifier('warning', 'Saved search doesn\'t exist');
  viewModel.removeAdvancedFilters();
};

export const loadSavedSearch = (viewModel) => {
  const searchId = viewModel.attr('router.saved_search');
  viewModel.attr('loading', true);

  return SavedSearch.findOne({id: searchId}).then((response) => {
    viewModel.attr('loading', false);
    const savedSearch = response.SavedSearch;

    if (savedSearch &&
      savedSearch.object_type === viewModel.attr('modelName') &&
      savedSearch.search_type === 'AdvancedSearch') {
      const parsedSavedSearch = {
        ...AdvancedSearch.parseFilterJson(savedSearch.filters),
        id: savedSearch.id,
      };

      selectSavedSearchFilter(
        viewModel.attr('advancedSearch'),
        parsedSavedSearch
      );
      viewModel.applyAdvancedFilters();
    } else {
      // clear filter and apply default
      processNotExistedSearch(viewModel);
    }
  }).fail(() => {
    viewModel.attr('loading', false);
    processNotExistedSearch(viewModel);
  });
};

/**
 * Filter parentInstance items to remove duplicates
 * @param {Object} parentInstance - parent instance attribute of Advanced search
 * @param {Array} parentItems - parentItems attribute of Advanced search
 * @return {Array} - filtered parentItems
 */
export const filterParentItems = (parentInstance, parentItems) => {
  return parentItems.filter((item) =>
    item.value.id !== parentInstance.value.id ||
    item.value.type !== parentInstance.value.type);
};

/**
 * Select saved search filter to current advanced search
 * @param {can.Map} advancedSearch - current advanced search
 * @param {Object} savedSearch - saved search
 */
const selectSavedSearchFilter = (advancedSearch, savedSearch) => {
  const parentInstance = advancedSearch.attr('parentInstance');
  if (parentInstance && savedSearch.parentItems) {
    savedSearch.parentItems =
      filterParentItems(parentInstance, savedSearch.parentItems);
  }

  advancedSearch.attr('filterItems', savedSearch.filterItems);
  advancedSearch.attr('mappingItems', savedSearch.mappingItems);
  advancedSearch.attr('parentItems', savedSearch.parentItems);

  const selectedSavedSearch = {
    filterItems: savedSearch.filterItems,
    mappingItems: savedSearch.mappingItems,
    parentItems: savedSearch.parentItems,
    id: savedSearch.id,
  };

  // save selected saved search
  advancedSearch.attr('selectedSavedSearch', selectedSavedSearch);
};
