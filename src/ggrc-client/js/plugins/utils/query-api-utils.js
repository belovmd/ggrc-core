/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import loCompact from 'lodash/compact';
import loGroupBy from 'lodash/groupBy';
import loIsNumber from 'lodash/isNumber';
import loMap from 'lodash/map';
import {ggrcAjax} from '../../plugins/ajax_extensions';
import makeArray from 'can-util/js/make-array/make-array';
import QueryParser from '../../generated/ggrc_filter_query_parser';
import {
  notifier,
} from './notifiers-utils';
import {
  isConnectionLost,
  handleAjaxError,
} from './errors-utils';
/**
 * Util methods for work with QueryAPI.
 */

/**
 * @typedef LimitArray
 * @type {array}
 * @property {number} 0  - Lower bound is inclusive.
 * @property {number} 1  - Upper bound is exclusive.
 */

/**
 * @typedef QueryAPIRequest
 * @type {Object}
 * @property {string} object_name - The name of object
 * @property {LimitArray} limit - The boundaries of the requested values.
 * @property {object} filters - Filter properties
 */

const BATCH_TIMEOUT = 100;
let batchQueue = [];
let batchTimeout = null;

/**
 * Collect requests to Query API.
 *
 * @param {Object} params - Params for request
 * @param {Object} params.headers - Custom headers for request.
 * @param {Object} params.data - Object with parameters on Query API needed.
 * @return {Promise} Promise on Query API request.
 */
function batchRequests(params) {
  let dfd = $.Deferred();
  batchQueue.push({dfd: dfd, params: params});

  if (loIsNumber(batchTimeout)) {
    clearTimeout(batchTimeout);
  }

  batchTimeout = setTimeout(function () {
    _resolveBatch(batchQueue.splice(0, batchQueue.length));
  }, BATCH_TIMEOUT);
  return dfd;
}

/**
 * Build params for ids type request on Query API.
 *
 * @param {String} objName - Name of requested object
 * @param {Object} page - Information about page state.
 * @param {Number} page.current - Current page
 * @param {Number} page.pageSize - Page size
 * @param {Array} page.sort - Array of sorting criteria
 * @param {String} page.filter - Filter string
 * @param {Object} relevant - Information about relevant object
 * @param {Object} relevant.type - Type of relevant object
 * @param {Object} relevant.id - Id of relevant object
 * @param {Object} relevant.operation - Type of operation.
 * @param {Object|Array} additionalFilter - Additional filters to be applied
 * @return {Object} Object of QueryAPIRequest
 */
function buildRelevantIdsQuery(objName, page, relevant, additionalFilter) {
  let param = buildParam(objName, page, relevant, null, additionalFilter);
  param.type = 'ids';
  return param;
}

/**
 * Build params for request on Query API.
 *
 * @param {String} objName - Name of requested object
 * @param {Object} page - Information about page state.
 * @param {Number} page.current - Current page
 * @param {Number} page.pageSize - Page size
 * @param {Array} page.sort - Array of sorting criteria
 * @param {Number} page.buffer - Size of additional items
 * @param {Number} page.first - first item number in the list
 * @param {Number} page.last - last item number in the list
 * @param {Object|Object[]} relevant - Information about relevant object
 * @param {Object} relevant.type - Type of relevant object
 * @param {Object} relevant.id - Id of relevant object
 * @param {Object} relevant.operation - Type of operation.
 * @param {Array} fields - Array of requested fields.
 * @param {Object|Array} filters - Filters to be applied
 * @return {Object} Object of QueryAPIRequest
 */
function buildParam(objName, page, relevant, fields, filters) {
  let params = {};

  if (!objName) {
    return {};
  }

  params.object_name = objName;
  params.filters = _makeFilter(filters, relevant);

  if (page.current && page.pageSize) {
    let first = (page.current - 1) * page.pageSize;
    let last = page.current * page.pageSize;
    if (page.buffer) {
      last += page.buffer;
    }
    params.limit = [first, last];
  } else if (loIsNumber(page.first) && loIsNumber(page.last)) {
    params.limit = [page.first, page.last];
  }

  if (page.sort) {
    params.order_by = loMap(page.sort, (el) => {
      if (el.key) {
        return {
          name: el.key,
          desc: el.direction === 'desc',
        };
      }
    });

    params.order_by = loCompact(params.order_by);
    params.order_by = params.order_by.length ? params.order_by : undefined;
  }

  if (fields) {
    params.fields = fields;
  }
  return params;
}

/**
 * Build Count Params.
 *
 * @param {Array} types - Names of requested object
 * @param {Object} relevant - Information about relevant object
 * @param {Object} filter - A filter to be applied
 * @return {Array} Array of QueryAPIRequests
 */
function buildCountParams(types, relevant, filter) {
  let params;

  if (!types || !Array.isArray(types)) {
    return [];
  }

  params = types.map(function (objName) {
    let param = {};

    if (!objName) {
      return {};
    }

    param.object_name = objName;
    param.type = 'count';

    if (relevant) {
      param.filters = _makeFilter(filter, relevant);
    }

    return param;
  });

  return params;
}

/**
 * Params for request on Query API
 * @param {Object} params - Params for request
 * @param {Object} params.headers - Custom headers for request.
 * @param {Object} params.data - Object with parameters on Query API needed.
 * @return {Promise} Promise on Query API request.
 */
function makeRequest(params) {
  let reqParams = params.data || [];
  return ggrcAjax({
    type: 'POST',
    headers: $.extend({
      'Content-Type': 'application/json',
    }, params.headers || {}),
    url: '/query',
    data: JSON.stringify(reqParams),
  });
}

function makeRelevantFilter(filter) {
  let relevantFilter = QueryParser.parse('#' + filter.type + ',' +
    filter.id + '#');

  if (filter && !filter.operation) {
    filter.operation = 'relevant';
  }

  if (filter.operation &&
    filter.operation !== relevantFilter.expression.op.name) {
    relevantFilter.expression.op.name = filter.operation;
  }

  return relevantFilter;
}

function _makeFilter(filter, relevant) {
  let relevantFilters;
  let filterList = [];

  if (relevant) {
    relevant = Array.isArray(relevant) ?
      relevant :
      makeArray(relevant);
    relevantFilters = relevant.map(function (filter) {
      return makeRelevantFilter(filter);
    });
    filterList = filterList.concat(relevantFilters);
  }

  if (filter) {
    filter = Array.isArray(filter) ?
      filter :
      makeArray(filter);
    filterList = filterList.concat(filter);
  }
  if (filterList.length) {
    return filterList.reduce(function (left, right) {
      return QueryParser.joinQueries(left, right);
    });
  }
  return {expression: {}};
}

function _resolveBatch(queue) {
  makeRequest({
    data: queue.map(function (el) {
      return el.params;
    }),
  }).then(function (result) {
    result.forEach(function (info, i) {
      let req = queue[i];

      req.dfd.resolve(info);
    });
  }).catch((jqxhr, textStatus, exception) => {
    if (isConnectionLost()) {
      notifier('error', 'Internet connection was lost.');
    } else {
      handleAjaxError(jqxhr, exception);
    }
    queue.forEach((req) => req.dfd.reject());
  });
}

/**
 * Loads objects based on passed stubs.
 * @async
 * @param {Stub[]} stubs Array of stubs for which objects
 * should be loaded
 * @param {string[]} fields Fields, which should be presented in response
 * for each object
 * @return {Promise<object[]>} Loaded objects
 */
async function loadObjectsByStubs(stubs, fields) {
  const batchedRequest = _buildMappedObjectsRequest(stubs, fields);
  const response = await Promise.all(batchedRequest);
  return _processObjectsResponse(response);
}

/**
 * Loads objects based on passed types. If objects with passed type weren't
 * found then the results won't contain objects with mentioned type.
 * @async
 * @param {canModel.Cacheable|Stub} relevant - Information about relevant
 * object
 * @param {object|Stub[]} types Array of types for which objects
 * should be loaded
 * @param {string[]} fields Fields, which should be presented in response
 * for each object
 * @return {Promise<object[]>} Loaded objects
 */
async function loadObjectsByTypes(relevant, types, fields) {
  const batchedRequest = _buildAllMappedObjectsRequest(relevant, types, fields);
  const response = await Promise.all(batchedRequest);
  return _processObjectsResponse(response);
}

function _buildAllMappedObjectsRequest(relevant, types, fields) { // eslint-disable-line
  return loMap(types, (type) =>
    batchRequests(buildParam(
      type,
      {},
      relevant,
      fields,
      null,
    ))
  );
}

function _buildMappedObjectsRequest(stubs, fields) { // eslint-disable-line
  const groupedStubsByType = loGroupBy(stubs, 'type');

  return loMap(groupedStubsByType, (stubs, objectsType) =>
    batchRequests(buildParam(
      objectsType,
      {},
      null,
      fields,
      _buildObjectsFilter(stubs),
    ))
  );
}

function _buildObjectsFilter(stubs) {
  return {
    expression: {
      left: 'id',
      op: {name: 'IN'},
      right: stubs.map((stub) => stub.id),
    },
  };
}

function _processObjectsResponse(response) {
  return response.reduce((result, responseObj) => {
    const [{values}] = Object.values(responseObj);
    result.push(...values);
    return result;
  }, []);
}

/**
 * Concatenation active filters.
 *
 * @param {String} filter - Parsed filter string
 * @param {Object} options - Filter parameters
 * @return {string} - Result of concatenation filters.
 * @private
 */
function concatFilters(filter, options) {
  if (filter) {
    filter = QueryParser.joinQueries(
      filter,
      options.query.attr(),
      'AND');
  } else if (options.query) {
    filter = options.query;
  }

  return filter;
}

export {
  makeRelevantFilter,
  buildParam,
  buildRelevantIdsQuery,
  batchRequests,
  buildCountParams,
  loadObjectsByStubs,
  loadObjectsByTypes,
  concatFilters,
};
