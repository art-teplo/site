import assert from 'node:assert/strict';
import { test } from 'node:test';
import { splitFacetControls, toggleFacetValue } from '../src/lib/facet-controls.ts';

const empty = { lists: {}, ranges: {} };
const custom = { key: 'surface_texture', label: 'Фактура поверхности', kind: 'list', total_values: 2, values: [
  { value: 'smooth', label: 'Гладкая', count: 12 },
  { value: 'ribbed', label: 'Рельефная с продольными рёбрами', count: 4 },
] };

test('a newly registered attribute stays a multiple selector and supports deselection', () => {
  assert.equal(splitFacetControls([custom], empty).controls[0].key, 'surface_texture');
  assert.deepEqual(toggleFacetValue(['smooth'], 'ribbed'), ['smooth', 'ribbed']);
  assert.deepEqual(toggleFacetValue(['smooth', 'ribbed'], 'smooth'), ['ribbed']);
});

test('a context with one remaining value does not make a variable attribute constant', () => {
  const single = { ...custom, values: custom.values.slice(0, 1) };
  assert.equal(splitFacetControls([single], empty).controls.length, 1);
  assert.equal(splitFacetControls([single], empty).constants.length, 0);
});

test('only a confirmed constant without selection becomes a characteristic', () => {
  const constant = { ...custom, total_values: 1, values: custom.values.slice(0, 1) };
  assert.equal(splitFacetControls([constant], empty).constants.length, 1);
  const chosen = splitFacetControls([constant], { ...empty, lists: { surface_texture: ['smooth'] } });
  assert.equal(chosen.controls.length, 1);
  assert.equal(chosen.constants.length, 0);
});

test('selected values missing from the response remain available to deselect', () => {
  const result = splitFacetControls([{ ...custom, values: [] }], { ...empty, lists: { surface_texture: ['ribbed'] } });
  assert.deepEqual(result.controls[0].values, [{ value: 'ribbed', label: 'ribbed', count: 0 }]);
});

test('active fixed or empty ranges remain controls while inactive fixed ranges are characteristics', () => {
  const fixed = { key: 'thickness', label: 'Толщина', kind: 'range', total_values: 1, unit: 'мм', min: 12, max: 12 };
  assert.equal(splitFacetControls([fixed], empty).constants.length, 1);
  assert.equal(splitFacetControls([fixed], { ...empty, ranges: { thickness: [10, 14] } }).controls.length, 1);
  assert.equal(splitFacetControls([{ ...fixed, min: null, max: null }], { ...empty, ranges: { thickness: [10] } }).controls.length, 1);
});

test('a range reduced to one value by another filter remains adjustable', () => {
  const facet = { key: 'custom_range', label: 'Новый диапазон', kind: 'range', total_values: 4, unit: '', min: 12, max: 12 };
  assert.equal(splitFacetControls([facet], empty).controls.length, 1);
});


test('a value known for only some articles is not a series characteristic', () => {
  const facet = { ...custom, total_values: 1, has_unknown: true, values: custom.values.slice(0, 1) };
  const result = splitFacetControls([facet], empty);
  assert.equal(result.constants.length, 0);
  assert.equal(result.controls[0].key, facet.key);
});
