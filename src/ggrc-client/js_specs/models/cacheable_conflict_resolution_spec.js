/*
    Copyright (C) 2019 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import * as AjaxExtensions from '../../js/plugins/ajax_extensions';
import Cacheable from '../../js/models/cacheable';
import {
  failAll,
  makeFakeModel,
} from '../spec_helpers';

describe('Cacheable conflict resolution', function () {
  let DummyModel;
  let ajaxSpy;

  beforeAll(function () {
    ajaxSpy = spyOn(AjaxExtensions, 'ggrcAjax');
    DummyModel = makeFakeModel({
      model: Cacheable,
      staticProps: {
        ajax: AjaxExtensions.ggrcAjax,
        update: 'PUT /api/dummy_models/{id}',
        table_singular: 'dummy_model',
      },
    });
  });

  function _resovleDfd(obj, reject) {
    return new $.Deferred(function (dfd) {
      setTimeout(function () {
        if (!reject) {
          dfd.resolve(obj);
        } else {
          dfd.reject(obj, 409, 'CONFLICT');
        }
      }, 10);
    });
  }

  it('does not refresh model', function (done) {
    let obj = new DummyModel({id: 1});
    spyOn(obj, 'refresh').and.returnValue($.when(obj));
    ajaxSpy.and.returnValue(
      new $.Deferred().reject({status: 409}, 409, 'CONFLICT'));
    DummyModel.update(obj.id, obj.serialize()).then(function () {
      done();
    }, function () {
      expect(obj.refresh).not.toHaveBeenCalled();
      done();
    });
  });

  // TODO: Spy on setTimeout blocks then chain. This
  // test should be updated or removed if this check
  // is not possible.
  xit('sets timeout id to XHR-response', function (done) {
    let obj = new DummyModel({id: 1});
    spyOn(obj, 'refresh').and.returnValue($.when(obj));
    spyOn(window, 'setTimeout').and.returnValue(999);
    ajaxSpy.and.returnValue(
      new $.Deferred().reject({status: 409}, 409, 'CONFLICT'));
    DummyModel.update(obj.id, obj.serialize()).then(function () {
      done();
    }, function (xhr) {
      expect(xhr.warningId).toEqual(999);
      done();
    });
  });


  it('merges changed properties and saves', function (done) {
    let obj = new DummyModel({id: 1});
    obj.attr('foo', 'bar');
    obj.attr('baz', 'bazz');
    obj.backup();
    expect(obj._backupStore()).toEqual(
      jasmine.objectContaining({id: obj.id, foo: 'bar', baz: 'bazz'}));

    // current user changes "foo" attr
    obj.attr('foo', 'plonk');
    spyOn(obj, 'save').and.returnValue($.when(obj));

    ajaxSpy.and.callFake(() => {
      return _resovleDfd(
        {
          status: 409,
          responseJSON: {
            dummy_model: {
              // updated "baz" by other user
              baz: 'quux',

              // previous value of "foo"
              foo: 'bar',
              id: obj.id,
            },
          },
        }, true);
    });

    DummyModel.update(obj.id, obj.serialize()).then(function () {
      expect(obj).toEqual(jasmine.objectContaining(
        {id: obj.id, foo: 'plonk', baz: 'quux'}));
      expect(obj.save).toHaveBeenCalled();
      setTimeout(function () {
        done();
      }, 10);
    }, failAll(done));
  });


  it('lets other error statuses pass through', function (done) {
    let obj = new DummyModel({id: 1});
    let xhr = {status: 400};
    spyOn(obj, 'refresh').and.returnValue($.when(obj.serialize()));
    ajaxSpy.and.returnValue(
      new $.Deferred().reject(xhr, 400, 'BAD REQUEST'));
    DummyModel.update(1, obj.serialize()).then(function (_xhr) {
      expect(_xhr).toBe(xhr);
      done();
    });
  });
});
