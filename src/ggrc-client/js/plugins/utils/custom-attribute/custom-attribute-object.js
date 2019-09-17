/*
 Copyright (C) 2019 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import loForEach from 'lodash/forEach';
import canBatch from 'can-event/batch/batch';
import canMap from 'can-map';
import StateValidator from '../state-validator-utils';
import {
  CUSTOM_ATTRIBUTE_TYPE,
  caDefTypeName,
} from './custom-attribute-config';
import {CONTROL_TYPE} from '../control-utils.js';

/**
 * Represents relationships between back-end custom attribute control types
 * and controls which designed for it.
 */
const controlRelationshipType = {
  [caDefTypeName.Text]: CONTROL_TYPE.INPUT,
  [caDefTypeName.RichText]: CONTROL_TYPE.TEXT,
  [caDefTypeName.MapPerson]: CONTROL_TYPE.PERSON,
  [caDefTypeName.Date]: CONTROL_TYPE.DATE,
  [caDefTypeName.Input]: CONTROL_TYPE.INPUT,
  [caDefTypeName.Checkbox]: CONTROL_TYPE.CHECKBOX,
  [caDefTypeName.Multiselect]: CONTROL_TYPE.MULTISELECT,
  [caDefTypeName.Dropdown]: CONTROL_TYPE.DROPDOWN,
};

/**
 * A set of properties which describe minimum information
 * about represented object.
 * @typedef {Object} ObjectStub
 * @property {number} id - object id
 * @property {string} type - object type
 * @example
 * // stub for person
 * const personStub = {
 *  id: 123,
 *  type: "Person",
 * };
 */

/**
 * @class
 * @classdesc
 *  Represents the solid custom attriubte.
 *  Provides access to the value and the definition objects of
 *  the custom attribute. Also it has ability to validate itself.
 */
export default class CustomAttributeObject {
  /**
   * Creates CustomAttributeObject instance.
   * @param {canMap} instance - An instance of some object.
   * @param {canMap} caDefinition - A custom attribute definition owned by instance.
   * @param {canMap} caValue - A custom attribute value owned by instance.
   */
  constructor(
    instance,
    caDefinition,
    caValue = new canMap()
  ) {
    this._instance = instance;
    this._caDefinition = caDefinition;

    this._initCaValue(caValue);
    this._buildStateValidator();
  }

  /**
   * Returns a custom attribute value.
   * @return {string|number|boolean} - The custom attribute value.
   */
  get value() {
    const caDef = this._caDefinition;
    const caValue = this._caValue;
    const attributeType = caDef.attr('attribute_type');

    switch (attributeType) {
      case caDefTypeName.MapPerson:
        return caValue.attr('attribute_object.id') || null;
      case caDefTypeName.Checkbox:
        return Boolean(Number(caValue.attr('attribute_value')));
      default:
        return caValue.attr('attribute_value');
    }
  }

  /**
   * Sets custom attribute value to newValue.
   * Depending on custom attribute definition can be set related to it fields of
   * custom attribute value object.
   * @param {(string|number|boolean)} newValue - The new value.
   */
  set value(newValue) {
    const caValue = this._caValue;
    const attributeObject = this._prepareAttributeObject(newValue);
    const attributeValue = this._prepareAttributeValue(newValue);
    caValue.attr('attribute_object', attributeObject);
    caValue.attr('attribute_value', attributeValue);
  }

  /**
   * Returns the id for the custom attribute value.
   * @return {number} - The id for custom attribute value.
   */
  get customValueId() {
    return this._caValue.attr('id');
  }

  /**
   * Returns the title for the custom attribute.
   * @return {string} - The custom attribute title.
   */
  get title() {
    return this._caDefinition.attr('title');
  }

  /**
   * Returns the placeholder for the custom attribute.
   * @return {string} - the custom attribute placeholder.
   */
  get placeholder() {
    return this._caDefinition.attr('placeholder');
  }

  /**
   * Returns the help text for the custom attribute.
   * @return {string} - The custom attribute help text.
   */
  get helptext() {
    return this._caDefinition.attr('helptext');
  }

  /**
   * Returns an external name for the custom attribute.
   * @return {string} - External name.
   */
  get externalName() {
    return this._caDefinition.attr('external_name');
  }

  /**
   * Returns the custom attribute id.
   * @return {number} - The custom attribute id.
   */
  get customAttributeId() {
    return this._caDefinition.attr('id');
  }

  /**
   * Checks if the custom attribute is mandatory.
   * @return {boolean} - true if the custom attribute is mandatory, else false.
   */
  get mandatory() {
    return Boolean(this._caDefinition.attr('mandatory'));
  }

  /**
   * Returns the custom attribute control type.
   * @return {CONTROL_TYPE} - The control type.
   */
  get attributeType() {
    const caDef = this._caDefinition;
    return controlRelationshipType[caDef.attr('attribute_type')];
  }

  /**
   * Returns the stub for the person who modified the last time the value
   * of the custom attribute.
   * @return {ObjectStub} - The person stub.
   */
  get attributeObject() {
    return this._caValue.attr('attribute_object');
  }

  /**
   * Returns the custom attribute type.
   * @return {CUSTOM_ATTRIBUTE_TYPE} - The custom attribute type.
   */
  get type() {
    const caDef = this._caDefinition;
    const isGlobalCustomAttribute = caDef.attr('definition_id') === null;
    return isGlobalCustomAttribute
      ? CUSTOM_ATTRIBUTE_TYPE.GLOBAL
      : CUSTOM_ATTRIBUTE_TYPE.LOCAL;
  }

  /**
   * Returns the list of multiple choice options.
   * If the custom attribute doesn't have options then returns an empty list.
   * @return {string[]} - The list of multiple choice options.
   */
  get multiChoiceOptions() {
    const options = this._caDefinition.attr('multi_choice_options');
    return (typeof options === 'string')
      ? options.split(',')
      : [];
  }

  /**
   * Returns the custom attribute validator.
   * @return {StateValidator} - The custom attribute validator.
   */
  get validator() {
    return this._validator;
  }

  /**
   * Returns the custom attribute validation state.
   * @return {canMap} - The custom attribute validation state.
   */
  get validationState() {
    return this._validationState;
  }

  /**
   * Updates CAV object entirely through passed CAV
   * object. Use it only in situation, when you want to update
   * each property CAV object.
   * @param {canMap|Object} cav - Custom attribute value.
   * @param {boolean} removeOtherFields - Remove other fields from the current
   * CAV object.
   */
  updateCaValue(cav, removeOtherFields) {
    const caValue = new canMap(cav);
    this._setupCaValue(caValue);
    this._caValue.attr(caValue.attr(), removeOtherFields);
  }

  /**
   * Updates validationState.
   */
  validate() {
    const validator = this.validator;
    validator.validate();
    this._validationState.attr(validator.validationState);
  }

  /**
   * Setups caValue object.
   * For creation the custom attribute value object we must set necessary fields
   * for the back-end.
   * @example
   * Object = Objective
   * Fields:
   *
   * attribute_object -
   *   here there are 2 cases:
   *     1) if we have "Map:Person" custom attribute then set {@link ObjectStub}
   *        of the person.
   *     2) in other cases it must be null.
   * attribute_value - value for custom attribute
   *    for Map:Person - "Person" string
   * context - must be the same as have Object
   * custom_attribute_id - id from appopriate custom_attribute_definitions
   * Above is specified the necessary MINIMUM for the back-end.
   *
   * @private
   * @param {canMap} caValue - The custom attriubte value object.
   */
  _setupCaValue(caValue) {
    const caDefinition = this._caDefinition;
    const instance = this._instance;
    const caAttributeValue = caValue.attr('attribute_value');
    // setup default values for mandatory fields
    const requiredDefaultFields = {
      attribute_object: null,
      attribute_value: this._prepareAttributeValue(caAttributeValue),
      context: instance.attr('context'),
      custom_attribute_id: caDefinition.attr('id'),
    };
    const caValueKeys = canMap.keys(caValue);

    canBatch.start();
    // set for caValue requiered fields if they were missed
    loForEach(requiredDefaultFields, (requiredValue, key) => {
      const hasMissedRequieredField = !caValueKeys.includes(key);
      if (hasMissedRequieredField) {
        caValue.attr(key, requiredValue);
      }
    });
    canBatch.stop();
  }

  /**
   * Initializes caValue property.
   * @param {canMap} caValue - Custom attribute value object.
   */
  _initCaValue(caValue) {
    this._setupCaValue(caValue);
    this._caValue = caValue;
  }

  /**
   * Returns prepared value depending on attribute_type.
   * @private
   * @param {(string|number|boolean)} value - A value for the processing.
   * @return {(string|number)} - A prepared value.
   */
  _prepareAttributeValue(value) {
    const caDef = this._caDefinition;
    const attributeType = caDef.attr('attribute_type');

    switch (attributeType) {
      case caDefTypeName.MapPerson:
        return 'Person';
      case caDefTypeName.Checkbox:
        return (value === true || value === '1')
          ? '1'
          : '0';
      default:
        return value || caDef.attr('default_value');
    }
  }

  /**
   * Returns the prepared attribute object depending on attribute_type.
   * @private
   * @param {string|number} value - The value for the processing.
   * @return {ObjectStub|null} - The prepared object.
   */
  _prepareAttributeObject(value) {
    const caDef = this._caDefinition;
    const attributeType = caDef.attr('attribute_type');

    if (attributeType !== caDefTypeName.MapPerson) {
      return null;
    }

    const personStub = {
      id: value,
      type: 'Person',
    };

    return value ? personStub : caDef.attr('default_value');
  }

  /**
   * Builds the custom attribute validator.
   * @private
   */
  _buildStateValidator() {
    const injected = {
      currentCaObject: this, // injects self into validator
    };
    const validator = new StateValidator(injected);

    this._validator = validator;
    /*
     * We use this property due to template is rerender
     * itself when we use in code attr method. In this case,
     * after each validation, if this property is changed with help
     * attr method then template will update itself.
     */
    this._validationState = new canMap(validator.validationState);
  }
}
