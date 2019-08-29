/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canStache from 'can-stache';
import canMap from 'can-map';
import canComponent from 'can-component';
import {formatDate} from '../../plugins/utils/date-utils';
import {
  getUserSystemRoles,
  getUserObjectRoles,
} from '../../plugins/utils/user-utils';
import template from './templates/tree-item-attr.stache';
import {convertMarkdownToHtml} from '../../plugins/utils/markdown-utils';
import {getOnlyAnchorTags} from '../../plugins/ggrc_utils';

// attribute names considered "default" and representing a date
const DATE_ATTRS = new Set([
  'end_date',
  'due_date',
  'finished_date',
  'start_date',
  'created_at',
  'updated_at',
  'verified_date',
  'last_deprecated_date',
  'last_assessment_date',
  'last_submitted_at',
  'last_verified_at',
]);

// attribute names considered "default" and representing rich text fields
const RICH_TEXT_ATTRS = new Set([
  'notes',
  'description',
  'test_plan',
  'risk_type',
  'threat_source',
  'threat_event',
  'vulnerability',
]);

// attribute names considered "default" and representing fields which contain
// at least "email" field
const PERSON_ATTRS = new Set([
  'created_by',
  'last_submitted_by',
  'last_verified_by',
]);

export default canComponent.extend({
  tag: 'tree-item-attr',
  view: canStache(template),
  leakScope: true,
  viewModel: canMap.extend({
    instance: null,
    name: '',
    define: {
      // workaround an issue: "instance.is_mega" is not
      // handled properly in template
      isMega: {
        get() {
          return this.attr('instance.is_mega');
        },
      },
      defaultValue: {
        type: String,
        get() {
          return this.getDefaultValue();
        },
      },
      userSystemRoles: {
        type: String,
        get() {
          return getUserSystemRoles(this.attr('instance')).join(', ');
        },
      },
      userObjectRoles: {
        type: String,
        get() {
          return getUserObjectRoles(this.attr('instance')).join(', ');
        },
      },
    },
    /**
     * Transforms Rich text attribute value.
     *
     * @param {String} value - Rich text attribute value from DB.
     * @return {String} - the transformed rich text attribute value.
     */
    getConvertedRichTextAttr(value) {
      let result = value;

      if (this.isMarkdown()) {
        result = convertMarkdownToHtml(result);
      }
      return getOnlyAnchorTags(result);
    },
    /**
     * Retrieve the string value of an attribute.
     *
     * The method only supports instance attributes categorized as "default",
     * and does not support (read: not work for) nested object references.
     *
     * If the attribute does not exist or is not considered
     * to be a "default" attribute, an empty string is returned.
     *
     * If the attribute represents a date information, it is returned in the
     * MM/DD/YYYY format.
     *
     * @return {String} - the retrieved attribute's value
     */
    getDefaultValue() {
      let attrName = this.attr('name');
      let instance = this.attr('instance');

      let result = instance.attr(attrName);

      if (result !== undefined && result !== null) {
        if (PERSON_ATTRS.has(attrName)) {
          return result.attr('email');
        }

        if (DATE_ATTRS.has(attrName)) {
          return formatDate(result, true);
        }

        if (RICH_TEXT_ATTRS.has(attrName)) {
          return this.getConvertedRichTextAttr(result);
        }
        return String(result);
      }
      return '';
    },
    isMarkdown() {
      return !!this.attr('instance').constructor.isChangeableExternally;
    },
  }),
});
