/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import Component from '../create-saved-search';
import {getComponentVM} from '../../../../../js_specs/spec_helpers';
import pubSub from '../../../../pub-sub';
import SavedSearch from '../../../../models/service-models/saved-search';
import * as NotifierUtils from '../../../../plugins/utils/notifiers-utils';
import * as ErrorsUtils from '../../../../plugins/utils/errors-utils';

describe('create-saved-search component', () => {
  let viewModel;

  beforeAll(() => {
    viewModel = getComponentVM(Component);
  });

  describe('"getFilters" method', () => {
    let method;

    beforeAll(() => {
      method = viewModel.getFilters.bind(viewModel);
    });

    it('should NOT change "parentItems". "parentInstance" is null', () => {
      viewModel.attr('parentItems', [{type: 'parent items'}]);
      viewModel.attr('parentInstance', null);

      const result = method();
      expect(result.parentItems)
        .toEqual(viewModel.attr('parentItems').serialize());
    });

    it('should add item to "parentItems" from "parentInstance"', () => {
      viewModel.attr('parentItems', [{type: 'parent items'}]);
      viewModel.attr('parentInstance', {type: 'parentInstance'});

      const result = method();
      expect(result.parentItems.length).toBe(2);
      expect(result.parentItems[0])
        .toEqual(viewModel.attr('parentItems')[0].serialize());
      expect(result.parentItems[1])
        .toEqual(viewModel.attr('parentInstance').serialize());
    });

    it('should set "parentItems" from "parentInstance"', () => {
      viewModel.attr('parentItems', []);
      viewModel.attr('parentInstance', {type: 'parentInstance'});

      const result = method();
      expect(result.parentItems.length).toBe(1);
      expect(result.parentItems[0])
        .toEqual(viewModel.attr('parentInstance').serialize());
    });
  });

  describe('"saveSearch" method', () => {
    let method;

    beforeAll(() => {
      method = viewModel.saveSearch.bind(viewModel);
    });

    beforeEach(() => {
      viewModel.attr('isDisabled', false);
      viewModel.attr('searchName', 'my saved search');
    });

    it('should NOT trigger "save" when component is disabled', () => {
      viewModel.attr('isDisabled', true);

      spyOn(SavedSearch.prototype, 'save');
      method();

      expect(SavedSearch.prototype.save).not.toHaveBeenCalled();
    });

    it('should NOT trigger "save" when "searchName" is empty', () => {
      viewModel.attr('searchName', '');
      spyOn(SavedSearch.prototype, 'save');
      spyOn(NotifierUtils, 'notifier');

      method();

      expect(SavedSearch.prototype.save).not.toHaveBeenCalled();
      expect(NotifierUtils.notifier).toHaveBeenCalled();
    });

    it('should disable component while saving', (done) => {
      const dfd = $.Deferred();
      spyOn(SavedSearch.prototype, 'save').and.returnValue(dfd);

      const saveDfd = method();

      expect(viewModel.attr('isDisabled')).toBeTruthy();

      saveDfd.then(() => {
        expect(viewModel.attr('isDisabled')).toBeFalsy();
        done();
      });

      dfd.resolve();
    });

    it('should reset "searchName" and dispatch pubSub after saving', (done) => {
      const dfd = $.Deferred();
      const savedSearchResponse = {id: 1, type: 'Global'};

      spyOn(SavedSearch.prototype, 'save').and.returnValue(dfd);
      spyOn(pubSub, 'dispatch');

      method().then(() => {
        expect(viewModel.attr('searchName')).toBe('');
        expect(pubSub.dispatch).toHaveBeenCalledWith({
          type: 'savedSearchCreated',
          search: {...savedSearchResponse},
        });
        done();
      });

      dfd.resolve(savedSearchResponse);
    });

    it('should trigger "handleAjaxError" if "save" was failed', (done) => {
      const dfd = $.Deferred();
      const error = {errorMessage: 'something wrong'};

      spyOn(SavedSearch.prototype, 'save').and.returnValue(dfd);
      spyOn(ErrorsUtils, 'handleAjaxError');

      method().then(() => {
        expect(ErrorsUtils.handleAjaxError).toHaveBeenCalledWith({
          ...error,
        });
        done();
      });

      dfd.reject(error);
    });
  });
});
