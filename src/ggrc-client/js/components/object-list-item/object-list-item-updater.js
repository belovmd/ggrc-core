/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canMap from 'can-map';
import canComponent from 'can-component';
import '../object-list-item/business-object-list-item';
import '../read-more/read-more';
import RefreshQueue from '../../models/refresh_queue';

export default canComponent.extend({
  tag: 'object-list-item-updater',
  leakScope: true,
  viewModel: canMap.extend({
    define: {
      targetInstance: {
        set: function (value) {
          this.attr('instanceUpdated', false);

          if (value.isNeedRefresh) {
            this.updateInstance(value);
            return;
          }

          this.attr('instance', value);
          this.attr('instanceUpdated', true);
        },
      },
    },
    instance: {},
    instanceUpdated: false,
    updateInstance: function (instance) {
      new RefreshQueue().enqueue(instance)
        .trigger().then(function (refreshedInstances) {
          this.attr('instance', refreshedInstances[0]);
          this.attr('instanceUpdated', true);
        }.bind(this));
    },
  }),
});
