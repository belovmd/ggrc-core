/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import loDebounce from 'lodash/debounce';
import loGet from 'lodash/get';
import loFindIndex from 'lodash/findIndex';
import loSortBy from 'lodash/sortBy';
import makeArray from 'can-util/js/make-array/make-array';
import canStache from 'can-stache';
import canList from 'can-list';
import canMap from 'can-map';
import canComponent from 'can-component';
import './tree-header-selector';
import './sub-tree-expander';
import './sub-tree-wrapper';
import './sub-tree-item';
import './sub-tree-models';
import './tree-item-extra-info';
import './tree-item-actions';
import './tree-item-map';
import './tree-view';
import './tree-item';
import './tree-actions';
import './tree-header';
import './tree-filter-input';
import './tree-status-filter';
import './tree-item-status-for-workflow';
import './tree-no-results';
import './tree-field-wrapper';
import './tree-field';
import './tree-people-with-role-list-field';
import '../advanced-search/advanced-search-filter-container';
import '../advanced-search/advanced-search-mapping-container';
import '../bulk-update-button/bulk-update-button';
import '../assessment-template-clone-button/assessment-template-clone-button';
import '../create-document-button/create-document-button';
import '../dropdown/multiselect-dropdown';
import '../dropdown/dropdown-wrapper';
import '../assessment/assessment-generator-button';
import '../last-comment/last-comment';
import '../saved-search/saved-search-list/saved-search-list';
import '../saved-search/create-saved-search/create-saved-search';

import template from './templates/tree-widget-container.stache';
import * as StateUtils from '../../plugins/utils/state-utils';
import {
  REFRESH_RELATED,
  REFRESH_MAPPING,
} from '../../events/eventTypes';
import * as TreeViewUtils from '../../plugins/utils/tree-view-utils';
import {
  initMappedInstances,
  isObjectContextPage,
  isAllObjects,
  isMyWork,
} from '../../plugins/utils/current-page-utils';
import {
  initCounts,
  getCounts,
  refreshCounts,
  getWidgetModels,
} from '../../plugins/utils/widgets-utils';
import {getMegaObjectRelation} from '../../plugins/utils/mega-object-utils';
import * as AdvancedSearch from '../../plugins/utils/advanced-search-utils';
import Pagination from '../base-objects/pagination';
import tracker from '../../tracker';
import router from '../../router';
import {notifier} from '../../plugins/utils/notifiers-utils';
import Cacheable from '../../models/cacheable';
import Relationship from '../../models/service-models/relationship';
import * as businessModels from '../../models/business-models';
import exportMessage from './templates/export-message.stache';
import QueryParser from '../../generated/ggrc_filter_query_parser';
import {isSnapshotType} from '../../plugins/utils/snapshot-utils';
import SavedSearch from '../../models/service-models/saved-search';
import pubSub from '../../pub-sub';

let viewModel = canMap.extend({
  define: {
    /**
     * Condition that adds into all request to server-side Query API
     */
    additionalFilter: {
      type: String,
      value: '',
      get: function () {
        return this.attr('options').additional_filter;
      },
    },
    /**
     *
     */
    currentFilter: {
      type: String,
      get: function () {
        let filters = makeArray(this.attr('filters'));
        let additionalFilter = this.attr('additionalFilter');

        if (this.attr('advancedSearch.filter')) {
          return this.attr('advancedSearch.filter');
        }

        if (additionalFilter) {
          additionalFilter = QueryParser.parse(additionalFilter);
        }

        return filters.filter(function (options) {
          return options.query;
        }).reduce(this._concatFilters, additionalFilter);
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
    modelName: {
      type: String,
      get: function () {
        return this.attr('model').model_singular;
      },
    },
    statusFilterVisible: {
      type: Boolean,
      get: function () {
        return StateUtils.hasFilter(this.attr('modelName'));
      },
    },
    statusTooltipVisible: {
      type: Boolean,
      get: function () {
        return StateUtils.hasFilterTooltip(this.attr('modelName'));
      },
    },
    cssClasses: {
      type: String,
      get: function () {
        let classes = [];

        if (this.attr('loading')) {
          classes.push('loading');
        }

        return classes.join(' ');
      },
    },
    parent_instance: {
      type: '*',
      get: function () {
        return this.attr('options').parent_instance;
      },
    },
    noResults: {
      type: Boolean,
      get: function () {
        return !this.attr('loading') && !this.attr('showedItems').length;
      },
    },
    pageInfo: {
      value: function () {
        return new Pagination({
          pageSizeSelect: [10, 25, 50],
          pageSize: 10});
      },
    },
    selectedItem: {
      set(newValue) {
        this.selectedItemHandler(newValue);
        return newValue;
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
  },
  sortingInfo: {
    sortDirection: null,
    sortBy: null,
  },
  /**
   *
   */
  model: null,
  /**
   *
   */
  showedItems: [],
  /**
   *
   */
  limitDepthTree: 0,
  /**
   * Legacy options which were built for a previous implementation of TreeView based on TreeView controller
   */
  options: {},
  router: null,
  $el: null,
  loading: false,
  refetch: false,
  columns: {
    selected: [],
    available: [],
  },
  filters: [],
  canOpenInfoPin: true,
  savedSearchPermalink: '',
  pubSub,
  loadItems: function () {
    let modelName = this.attr('modelName');
    let pageInfo = this.attr('pageInfo');
    let sortingInfo = this.attr('sortingInfo');
    let parent = this.attr('parent_instance');
    let filter = this.attr('currentFilter');
    let page = {
      current: pageInfo.current,
      pageSize: pageInfo.pageSize,
      sort: [{
        key: sortingInfo.sortBy,
        direction: sortingInfo.sortDirection,
      }],
    };
    let request = this.attr('advancedSearch.request');
    const stopFn = tracker.start(modelName,
      tracker.USER_JOURNEY_KEYS.TREEVIEW,
      tracker.USER_ACTIONS.TREEVIEW.TREE_VIEW_PAGE_LOADING(page.pageSize));

    pageInfo.attr('disabled', true);
    this.attr('loading', true);

    let loadSnapshots = this.attr('options.objectVersion');
    const operation = this.attr('options.megaRelated')
      ? getMegaObjectRelation(this.attr('options.widgetId')).relation
      : null;

    return TreeViewUtils
      .loadFirstTierItems(
        modelName,
        parent,
        page,
        filter,
        request,
        loadSnapshots,
        operation)
      .then((data) => {
        const total = data.total;

        this.attr('showedItems', data.values);
        this.attr('pageInfo.total', total);
        this.attr('pageInfo.disabled', false);
        this.attr('loading', false);
      })
      .then(stopFn, stopFn.bind(null, true));
  },
  refresh(destinationType) {
    if (!destinationType || this.attr('modelName') === destinationType) {
      this.closeInfoPane();
      return this.loadItems();
    }

    return Promise.resolve();
  },
  setColumnsConfiguration: function () {
    let columns = TreeViewUtils.getColumnsForModel(
      this.attr('model').model_singular,
      this.attr('options.widgetId')
    );

    this.addServiceColumns(columns);

    this.attr('columns.available', columns.available);
    this.attr('columns.selected', columns.selected);
    this.attr('columns.mandatory', columns.mandatory);
    this.attr('columns.disableConfiguration', columns.disableConfiguration);
  },
  addServiceColumns(columns) {
    if (this.attr('modelName') === 'Person') {
      const serviceCols =
        this.attr('model').tree_view_options.service_attr_list;

      columns.available = columns.available.concat(serviceCols);
      columns.selected = columns.selected.concat(serviceCols);

      columns.available = loSortBy(columns.available, 'order');
      columns.selected = loSortBy(columns.selected, 'order');
    }
  },
  setSortingConfiguration: function () {
    let sortingInfo = TreeViewUtils
      .getSortingForModel(this.attr('modelName'));

    this.attr('sortingInfo.sortBy', sortingInfo.key);
    this.attr('sortingInfo.sortDirection', sortingInfo.direction);
  },
  onUpdateColumns: function (event) {
    let selectedColumns = event.columns;
    let columns = TreeViewUtils.setColumnsForModel(
      this.attr('model').model_singular,
      selectedColumns,
      this.attr('options.widgetId')
    );

    this.addServiceColumns(columns);

    this.attr('columns.selected', columns.selected);
  },
  onSort: function (event) {
    this.attr('sortingInfo.sortBy', event.field);
    this.attr('sortingInfo.sortDirection', event.sortDirection);

    this.attr('pageInfo.current', 1);
    this.refresh();
  },
  onFilter: function () {
    const stopFn = tracker.start(this.attr('modelName'),
      tracker.USER_JOURNEY_KEYS.TREEVIEW,
      tracker.USER_ACTIONS.TREEVIEW.FILTER);
    this.attr('pageInfo.current', 1);
    this.refresh().then(stopFn);
  },
  getDepthFilter: function (deepLevel) {
    let filters = makeArray(this.attr('filters'));

    return filters.filter(function (options) {
      return options.query &&
        options.depth &&
        options.filterDeepLimit > deepLevel;
    }).reduce(this._concatFilters, null);
  },
  registerFilter: function (option) {
    this.attr('filters').push(option);
  },
  /**
   * Concatenation active filters.
   *
   * @param {String} filter - Parsed filter string
   * @param {Object} options - Filter parameters
   * @return {string} - Result of concatenation filters.
   * @private
   */
  _concatFilters: function (filter, options) {
    if (filter) {
      filter = QueryParser.joinQueries(
        filter,
        options.query.attr(),
        'AND');
    } else if (options.query) {
      filter = options.query;
    }

    return filter;
  },
  _widgetHidden: function () {
    this._triggerListeners(true);
  },
  _widgetShown() {
    let countsName = this.attr('options.countsName');
    let total = this.attr('pageInfo.total');
    let counts = loGet(getCounts(), countsName);

    this._triggerListeners();

    if (this.attr('refetch') ||
      router.attr('refetch') ||
      this.attr('options.forceRefetch') ||
      // this condition is mostly for Issues, Documents and Evidence as they can be created from other object info pane
      (total !== counts)) {
      this.loadItems();
      this.attr('refetch', false);
    }
  },
  _needToRefreshAfterRelRemove(relationship) {
    const parentInstance = this.attr('parent_instance');
    const {
      source,
      destination,
    } = relationship;

    const isRelForCurrentInstance = (
      (
        source.type === parentInstance.attr('type') &&
        source.id === parentInstance.attr('id')
      ) || (
        destination.type === parentInstance.attr('type') &&
        destination.id === parentInstance.attr('id')
      )
    );

    return isRelForCurrentInstance;
  },
  _isRefreshNeeded(instance) {
    let needToRefresh = true;

    if (instance instanceof Relationship) {
      needToRefresh = this._needToRefreshAfterRelRemove(instance);
    }

    return needToRefresh;
  },
  _triggerListeners: (function () {
    let activeTabModel;
    let self;

    function onCreated(ev, instance) {
      if (activeTabModel === instance.type) {
        _refresh(true);
      } else if (!(instance instanceof Relationship)) {
        _refreshCounts();
      }
    }

    function onDestroyed(ev, instance) {
      const activeTabType = businessModels[activeTabModel].model_singular;
      const isSnapshotTab =
        isSnapshotType(instance) &&
        instance.child_type === activeTabType;

      if (_verifyRelationship(instance, activeTabModel) ||
        instance instanceof businessModels[activeTabModel] ||
        isSnapshotTab) {
        if (self.attr('showedItems').length === 1) {
          const current = self.attr('pageInfo.current');
          self.attr('pageInfo.current',
            current > 1 ? current - 1 : 1);
        }

        if (self._isRefreshNeeded(instance)) {
          _refresh();

          // TODO: This is a workaround.We need to update communication between
          //       info-pin and tree views through Observer
          if (!self.attr('$el').closest('.pin-content').length) {
            $('.pin-content').control().unsetInstance();
          }
        } else {
          _refreshCounts();
        }
      } else {
        // reinit mapped instances (subTree uses mapped instances)
        initMappedInstances();
      }
    }

    const _refresh = async (sortByUpdatedAt) => {
      if (self.attr('loading')) {
        return;
      }
      if (sortByUpdatedAt) {
        self.attr('sortingInfo.sortDirection', 'desc');
        self.attr('sortingInfo.sortBy', 'updated_at');
        self.attr('pageInfo.current', 1);
      }
      await self.loadItems();
      if (self.attr('currentFilter')) {
        _refreshCounts();
      } else {
        const countsName = self.attr('options.countsName');
        const total = self.attr('pageInfo.total');
        getCounts().attr(countsName, total);
      }
      self.closeInfoPane();
    };

    // timeout required to let server correctly calculate changed counts
    const _refreshCounts = loDebounce(() => {
      // do not refresh counts for Workflow. There are additional filters
      // for history and active tabs which are handled in workflow components
      if (self.attr('parent_instance').type === 'Workflow') {
        return;
      }

      if (isMyWork() || isAllObjects()) {
        const location = window.location.pathname;
        const widgetModels = getWidgetModels('Person', location);
        initCounts(widgetModels, 'Person', GGRC.current_user.id);
      } else {
        refreshCounts();
      }
    }, 250);

    function _verifyRelationship(instance, shortName, parentInstance) {
      if (!(instance instanceof Relationship)) {
        return false;
      }

      if (parentInstance && instance.destination && instance.source) {
        if (instance.source.type === parentInstance.type &&
          (instance.destination.type === shortName ||
          instance.destination.type === 'Snapshot')) {
          return true;
        }
        return false;
      }
      if (instance.destination &&
        (instance.destination.type === shortName ||
        instance.destination.type === 'Snapshot')) {
        return true;
      }
      if (instance.source &&
        (instance.source.type === shortName ||
        instance.source.type === 'Snapshot')) {
        return true;
      }
      return false;
    }

    return function (needDestroy) {
      activeTabModel = this.options.model.model_singular;
      self = this;
      if (needDestroy) {
        // Remove listeners for inactive tabs
        Cacheable.unbind('created', onCreated);
        Cacheable.unbind('destroyed', onDestroyed);
      } else {
        // Add listeners on creations instance or mappings objects for current tab
        // and refresh page after that.
        Cacheable.bind('created', onCreated);
        Cacheable.bind('destroyed', onDestroyed);
      }
    };
  })(),

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
  openAdvancedFilter: function () {
    // serialize "appliedFilterItems" before set to prevent changing of
    // "appliedFilterItems" object by changing of "filterItems" object.
    // Without "serialization" we copy reference of "appliedFilterItems" to "filterItems".
    this.attr('advancedSearch.filterItems',
      this.attr('advancedSearch.appliedFilterItems').serialize());

    this.attr('advancedSearch.mappingItems',
      this.attr('advancedSearch.appliedMappingItems').serialize());

    this.attr('advancedSearch.parentItems',
      this.attr('advancedSearch.appliedParentItems').serialize());

    if (isObjectContextPage() && !this.attr('advancedSearch.parentInstance')) {
      this.attr('advancedSearch.parentInstance',
        AdvancedSearch.create.parentInstance(this.attr('parent_instance')));

      // remove duplicates
      const parentItems = filterParentItems(
        this.attr('advancedSearch.parentInstance'),
        this.attr('advancedSearch.parentItems'));

      this.attr('advancedSearch.parentItems', parentItems);
    }

    this.attr('advancedSearch.open', true);
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

    const widgetId = this.attr('options.widgetId');
    const permalink = AdvancedSearch
      .buildSearchPermalink(selectedSavedSearch.id, widgetId);

    this.attr('savedSearchPermalink', permalink);
    this.attr('appliedSavedSearch', selectedSavedSearch.serialize());
  },
  applyAdvancedFilters: function () {
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
  removeAdvancedFilters: function () {
    this.attr('advancedSearch.appliedFilterItems', canList());
    this.attr('advancedSearch.appliedMappingItems', canList());
    this.attr('advancedSearch.request', canList());
    this.attr('advancedSearch.filter', null);
    this.attr('advancedSearch.open', false);
    this.clearAppliedSavedSearch();
    this.onFilter();
  },
  resetAdvancedFilters: function () {
    this.attr('advancedSearch.filterItems', canList());
    this.attr('advancedSearch.mappingItems', canList());
    this.attr('advancedSearch.parentItems', canList());
  },
  closeInfoPane: function () {
    $('.pin-content')
      .control()
      .close();
  },
  getAbsoluteItemNumber: function (instance) {
    let showedItems = this.attr('showedItems');
    let pageInfo = this.attr('pageInfo');
    let startIndex = pageInfo.pageSize * (pageInfo.current - 1);
    let relativeItemIndex = loFindIndex(showedItems,
      {id: instance.id, type: instance.type});
    return relativeItemIndex > -1 ?
      startIndex + relativeItemIndex :
      relativeItemIndex;
  },
  getRelativeItemNumber: function (absoluteNumber, pageSize) {
    let pageNumber = Math.floor(absoluteNumber / pageSize);
    let startIndex = pageSize * pageNumber;
    return absoluteNumber - startIndex;
  },
  getNextItemPage: function (absoluteNumber, pageInfo) {
    let pageNumber = Math.floor(absoluteNumber / pageInfo.pageSize) + 1;
    let dfd = $.Deferred().resolve();

    if (pageInfo.current !== pageNumber) {
      this.attr('loading', true);
      this.attr('pageInfo.current', pageNumber);
      dfd = this.loadItems();
    }

    return dfd;
  },
  updateActiveItemIndicator: function (index) {
    let element = this.attr('$el');
    element
      .find('.item-active')
      .removeClass('item-active');
    element
      .find('tree-item:nth-of-type(' + (index + 1) +
        ') .tree-item-content')
      .addClass('item-active');
  },
  showLastPage: function () {
    const lastPageIndex = this.attr('pageInfo.count');

    this.attr('pageInfo.current', lastPageIndex);
  },
  export() {
    let modelName = this.attr('modelName');
    let parent = this.attr('parent_instance');
    let filter = this.attr('currentFilter');
    let request = this.attr('advancedSearch.request');
    let loadSnapshots = this.attr('options.objectVersion');
    const operation = this.attr('options.megaRelated') ?
      getMegaObjectRelation(this.attr('options.widgetId')).relation :
      null;

    TreeViewUtils.startExport(
      modelName,
      parent,
      filter,
      request,
      loadSnapshots,
      operation,
    );

    notifier('info', exportMessage, {data: true});
  },
  selectedItemHandler(itemIndex) {
    let componentSelector = 'assessment-info-pane';
    let pageInfo = this.attr('pageInfo');

    let relativeIndex = this
      .getRelativeItemNumber(itemIndex, pageInfo.pageSize);
    let pageLoadDfd = this
      .getNextItemPage(itemIndex, pageInfo);
    let pinControl = $('.pin-content').control();

    if (!this.attr('canOpenInfoPin')) {
      return;
    }

    pinControl.setLoadingIndicator(componentSelector, true);

    pageLoadDfd
      .then(function () {
        const items = this.attr('showedItems');
        const newInstance = items[relativeIndex];

        if (!newInstance) {
          this.closeInfoPane();
          this.showLastPage();

          return $.Deferred().resolve();
        }

        return newInstance
          .refresh();
      }.bind(this))
      .then(function (newInstance) {
        if (!newInstance) {
          return;
        }

        pinControl
          .updateInstance(componentSelector, newInstance);
        newInstance.dispatch('refreshRelatedDocuments');
        newInstance.dispatch({
          ...REFRESH_RELATED,
          model: 'Assessment',
        });

        this.updateActiveItemIndicator(relativeIndex);
      }.bind(this))
      .fail(function () {
        notifier('error', 'Failed to fetch an object.');
      })
      .always(function () {
        pinControl.setLoadingIndicator(componentSelector, false);
      });
  },
  searchModalClosed() {
    this.attr('advancedSearch.selectedSavedSearch', null);
  },
});

/**
 *
 */
export default canComponent.extend({
  tag: 'tree-widget-container',
  view: canStache(template),
  leakScope: true,
  viewModel,
  init: function () {
    this.viewModel.setColumnsConfiguration();
    this.viewModel.setSortingConfiguration();
  },
  events: {
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
    '{viewModel.pageInfo} current': function () {
      if (!this.viewModel.attr('loading')) {
        this.viewModel.refresh();
      }
    },
    '{viewModel.pageInfo} pageSize': function () {
      this.viewModel.loadItems();
    },
    ' selectTreeItem': function (el, ev, selectedEl, instance) {
      let parent = this.viewModel.attr('parent_instance');
      let setInstanceDfd;
      let infoPaneOptions = new canMap({
        instance: instance,
        parent_instance: parent,
        options: this.viewModel,
      });
      let itemNumber = this.viewModel.getAbsoluteItemNumber(instance);
      let isSubTreeItem = itemNumber === -1;

      ev.stopPropagation();

      if (!this.viewModel.attr('canOpenInfoPin')) {
        return;
      }

      if (!isSubTreeItem) {
        this.viewModel.attr('selectedItem', itemNumber);
      }

      this.viewModel.attr('canOpenInfoPin', false);
      this.viewModel.attr('isSubTreeItem', isSubTreeItem);
      el.find('.item-active').removeClass('item-active');
      selectedEl.addClass('item-active');

      setInstanceDfd = $('.pin-content').control()
        .setInstance(infoPaneOptions, selectedEl, true);

      setInstanceDfd.then(function () {
        this.viewModel.attr('canOpenInfoPin', true);
      }.bind(this));
    },
    ' refreshTree'(el, ev) {
      ev.stopPropagation();
      this.viewModel.refresh();
    },
    [`{viewModel.parent_instance} ${REFRESH_MAPPING.type}`](
      [scope], {destinationType}
    ) {
      this.viewModel.refresh(destinationType);
    },
    inserted() {
      let viewModel = this.viewModel;
      viewModel.attr('$el', this.element);
      viewModel.attr('router', router);

      this.element.closest('.widget')
        .on('widget_hidden', viewModel._widgetHidden.bind(viewModel));
      this.element.closest('.widget')
        .on('widget_shown', viewModel._widgetShown.bind(viewModel));
      viewModel._triggerListeners();

      if (isLoadSavedSearch(this.viewModel)) {
        loadSavedSearch(this.viewModel);
      } else {
        viewModel.loadItems();
      }
    },
    '{viewModel.parent_instance} displayTree'([scope], {destinationType}) {
      this.viewModel.refresh(destinationType);
    },
    '{viewModel.router} saved_search'() {
      if (isLoadSavedSearch(this.viewModel)) {
        loadSavedSearch(this.viewModel);
      }
    },
    '{pubSub} savedSearchSelected'(pubSub, ev) {
      const currentModelName = this.viewModel.attr('model').model_singular;
      const isCurrentModelName = currentModelName === ev.savedSearch.modelName;
      if (ev.searchType !== 'AdvancedSearch' || !isCurrentModelName) {
        return;
      }

      selectSavedSearchFilter(
        this.viewModel.attr('advancedSearch'),
        ev.savedSearch
      );
    },
    '{pubSub} refetchOnce'(scope, event) {
      if (event.modelNames.includes(this.viewModel.attr('modelName'))) {
        // refresh widget content when tab is opened
        this.viewModel.attr('refetch', true);
      }
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
