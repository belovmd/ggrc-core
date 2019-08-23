/*
  Copyright (C) 2019 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import {getComponentVM} from '../../../../js_specs/spec_helpers';
import Component from './download-template';
import * as Utils from '../../../plugins/utils/import-export-utils';
import {backendGdriveClient} from '../../../plugins/ggrc-gapi-client';
import * as ModalsUtils from '../../../plugins/utils/modals';

describe('download-template component', () => {
  let vm;

  beforeEach(() => {
    vm = getComponentVM(Component);
  });

  describe('showExtraFields property', () => {
    it('should be truthy when Assessments are selected', () => {
      vm.attr('selected', [{
        name: 'Assessment',
      }]);
      expect(vm.attr('showExtraFields')).toBe(true);

      vm.attr('selected', [{
        name: 'Program',
      }, {
        name: 'Assessment',
      }, {
        name: 'Audit',
      }]);
      expect(vm.attr('showExtraFields')).toBe(true);
    });

    it('should be falsy when Assessments are not selected', () => {
      vm.attr('selected', [{
        name: 'Program',
      }, {
        name: 'AssessmentTemplate',
      }]);
      expect(vm.attr('showExtraFields')).toBe(false);
    });
  });

  describe('selectItems() method', () => {
    it('should fill selected array from event', () => {
      vm.selectItems({
        selected: [{name: 'Foo'}, {name: 'Bar'}, {name: 'Baz'}],
      });

      let selected = Array.from(vm.attr('selected').map(({name}) => name));

      expect(selected.length).toEqual(3);
      expect(selected).toEqual(['Foo', 'Bar', 'Baz']);
    });

    it('should reset selected array after uncheck all items', () => {
      vm.attr('selected', ['Foo', 'Bar', 'Baz']);

      vm.selectItems({
        selected: [],
      });

      expect(vm.attr('selected').length).toEqual(0);
    });

    it('should reset selected array if event does not contain data', () => {
      vm.attr('selected', ['Foo', 'Bar', 'Baz']);

      vm.selectItems({});

      expect(vm.attr('selected').length).toEqual(0);
    });
  });

  describe('downloadCSV() method', () => {
    it('should do ajax call in proper format', (done) => {
      spyOn(Utils, 'downloadTemplate')
        .and.returnValue($.Deferred().resolve('FooBar'));
      spyOn(Utils, 'download');

      vm.attr('selected', [{name: 'Foo'}, {name: 'Bar'}, {name: 'Baz'}]);

      vm.downloadCSV().then(() => {
        expect(Utils.downloadTemplate)
          .toHaveBeenCalledWith({
            data: {
              objects: [
                {object_name: 'Foo'},
                {object_name: 'Bar'},
                {object_name: 'Baz'},
              ],
              export_to: 'csv',
            },
          });
        expect(Utils.download)
          .toHaveBeenCalledWith('import_template.csv', 'FooBar');
        expect(vm.attr('modalState.open')).toEqual(false);

        done();
      });
    });

    it('should not download CSV and should close the modal after error during' +
      '"downloadTemplate" phase', (done) => {
      spyOn(Utils, 'downloadTemplate')
        .and.returnValue($.Deferred().reject());
      spyOn(Utils, 'download');

      vm.attr('selected', [1, 2, 3]);

      vm.downloadCSV().fail(() => {
        expect(Utils.downloadTemplate).toHaveBeenCalled();
        expect(Utils.download).not.toHaveBeenCalled();
        expect(vm.attr('modalState.open')).toEqual(false);

        done();
      });
    });
  });

  describe('downloadSheet() method', () => {
    let downloadSpy;

    beforeEach(() => {
      spyOn(backendGdriveClient, 'withAuth').and.callFake((callback) => {
        return callback();
      });
      spyOn(ModalsUtils, 'confirm');
      downloadSpy = spyOn(Utils, 'downloadTemplate');
    });

    it('should do ajax call in proper format', (done) => {
      downloadSpy.and.returnValue($.Deferred().resolve('FooBar'));

      vm.attr('selected', [{name: 'Foo'}, {name: 'Bar'}, {name: 'Baz'}]);

      vm.downloadSheet().then(() => {
        expect(backendGdriveClient.withAuth).toHaveBeenCalled();
        expect(Utils.downloadTemplate)
          .toHaveBeenCalledWith({
            data: {
              objects: [
                {object_name: 'Foo'},
                {object_name: 'Bar'},
                {object_name: 'Baz'},
              ],
              export_to: 'gdrive',
            },
          });
        expect(ModalsUtils.confirm).toHaveBeenCalled();
        expect(vm.attr('modalState.open')).toEqual(false);

        done();
      });
    });

    it('should not download Sheet and should close the modal after error' +
      'during "downloadTemplate" phase', (done) => {
      downloadSpy.and.returnValue($.Deferred().reject());

      vm.attr('selected', [1, 2, 3]);

      vm.downloadSheet().fail(() => {
        expect(backendGdriveClient.withAuth).toHaveBeenCalled();
        expect(Utils.downloadTemplate).toHaveBeenCalled();
        expect(ModalsUtils.confirm).not.toHaveBeenCalled();
        expect(vm.attr('modalState.open')).toEqual(false);

        done();
      });
    });
  });

  describe('addTemplate() method', () => {
    it('should add an empty template', () => {
      vm.attr('templates', []);
      vm.addTemplate();

      const templates = vm.attr('templates');

      expect(templates[0].serialize()).toEqual({
        id: null,
        value: null,
        isDuplicate: false,
      });
    });
  });

  describe('removeTemplate() method', () => {
    it('should remove particular template', () => {
      vm.attr('templates', [{
        id: 1,
      }, {
        id: 2,
      }, {
        id: 3,
      }]);
      vm.removeTemplate(1);

      const templates = vm.attr('templates');

      expect(templates.length).toBe(2);
      expect(templates[0].id).toBe(1);
      expect(templates[1].id).toBe(3);
    });

    it('should call recalculation of duplicates', () => {
      spyOn(vm, 'updateDuplicatesAfterRemove');
      vm.attr('templates', [{
        id: 1,
      }, {
        id: 2,
      }, {
        id: 3,
      }]);

      vm.removeTemplate(1);
      expect(vm.updateDuplicatesAfterRemove).toHaveBeenCalled();
    });
  });

  describe('selectTemplate() method', () => {
    it('should select a template', () => {
      vm.attr('templates', [{
        id: null,
        value: null,
      }]);
      const selectedItem = {
        id: 321,
        title: 'Mock Template',
      };

      vm.selectTemplate(selectedItem, 0);

      const templates = vm.attr('templates');

      expect(templates[0].id).toBe(321);
      expect(templates[0].value).toBe('Mock Template');
      expect(selectedItem.value).toBe(selectedItem.title);
    });

    it('should call recalculation of duplicates', () => {
      spyOn(vm, 'updateDuplicatesAfterSelect');
      const selectedItem = {};
      vm.attr('templates', [{}]);

      vm.selectTemplate(selectedItem, 0);
      expect(vm.updateDuplicatesAfterSelect).toHaveBeenCalled();
    });
  });

  describe('updateDuplicatesAfterSelect() method', () => {
    it('should not mark new item as duplicate if it is unique', () => {
      vm.attr('templates', [{
        id: 91,
        value: 'Mock91',
        isDuplicate: false,
      }, {
        id: 92,
        value: 'Mock92',
        isDuplicate: false,
      }, {
        id: 81,
        value: 'Mock81',
      }]);

      const newTemplateId = 81;
      const selectIndex = 2;

      vm.updateDuplicatesAfterSelect(newTemplateId, selectIndex);

      const templates = vm.attr('templates');

      expect(templates[0].isDuplicate).toBe(false);
      expect(templates[1].isDuplicate).toBe(false);
      expect(templates[2].isDuplicate).not.toBe(true);
    });

    it('should mark new item as duplicate if it repeats other', () => {
      vm.attr('templates', [{
        id: 92,
        value: 'Mock92',
      }, {
        id: 92,
        value: 'Mock92',
      }, {
        id: 991,
        value: 'Mock91',
      }]);

      const newTemplateId = 92;
      const selectIndex = 0;

      vm.updateDuplicatesAfterSelect(newTemplateId, selectIndex);

      const templates = vm.attr('templates');

      expect(templates[0].isDuplicate).toBe(true);
      expect(templates[1].isDuplicate).not.toBe(true);
    });
  });

  describe('updateDuplicatesAfterRemove() method', () => {
    it('should mark as non duplicate first item with same id', () => {
      vm.attr('templates', [{
        id: 91,
        value: 'Mock91',
        isDuplicate: true,
      }, {
        id: 91,
        value: 'Mock91',
        isDuplicate: true,
      }, {
        id: 91,
        value: 'Mock91',
        isDuplicate: false,
      }, {
        id: 92,
        value: 'Mock92',
        isDuplicate: false,
      }]);

      const targetInd = 2;
      const [removedTemplate] = vm.attr('templates').splice(targetInd, 1);

      vm.updateDuplicatesAfterRemove(removedTemplate.id);

      const templates = vm.attr('templates');

      expect(templates[0].isDuplicate).toBe(false);
      expect(templates[1].isDuplicate).toBe(true);
      expect(templates[2].isDuplicate).toBe(false);
    });
  });

  describe('prepareTemplateIds() method', () => {
    it('should extract ids and remove duplicates', () => {
      vm.attr('templates', [{
        id: 91,
        value: 'Mock91',
      }, {
        id: 92,
        value: 'Mock92',
      }, {
        id: null,
        value: null,
      }, {
        id: null,
        value: null,
      }]);

      const preparedObject = {};
      vm.prepareTemplateIds(preparedObject);

      expect(preparedObject.template_ids).toEqual([91, 92]);
    });
  });
});
