import assert from 'node:assert/strict';
import { test } from 'node:test';
import { adjacentRangeValue } from '../src/lib/range-step.ts';
import { variantSize } from '../src/lib/variant-size.ts';

test('steps through irregular available sizes in both directions', () => {
  const sizes = [121, 181, 241, 501];
  assert.equal(adjacentRangeValue(sizes, 121, 1), 181);
  assert.equal(adjacentRangeValue(sizes, 241, 1), 501);
  assert.equal(adjacentRangeValue(sizes, 241, -1), 181);
});

test('arbitrary typed bounds move to the nearest value in the chosen direction', () => {
  assert.equal(adjacentRangeValue([121, 181, 241], 170, 1), 181);
  assert.equal(adjacentRangeValue([121, 181, 241], 170, -1), 121);
});

test('clamps at the available endpoints and respects the opposite bound', () => {
  assert.equal(adjacentRangeValue([121, 181, 241], 241, 1), 241);
  assert.equal(adjacentRangeValue([121, 181, 241], 121, -1), 121);
  assert.equal(adjacentRangeValue([121, 181, 241], 121, 1, 100, 150), 121);
  assert.equal(adjacentRangeValue([121, 181, 241], 241, -1, 200, 300), 241);
});

test('empty available values preserve a manually entered value', () => {
  assert.equal(adjacentRangeValue([], 170, 1), 170);
  assert.equal(adjacentRangeValue([121, 181], 170, 1, 200, 300), 170);
});

test('selected summary includes convector length and uses the same size as the hero', () => {
  assert.equal(variantSize({ heightMm: null, lengthMm: 1000, widthMm: 250 }), '1000×250 мм');
  assert.equal(variantSize({ heightMm: 121, lengthMm: null, widthMm: 833 }), '833×121 мм');
  assert.equal(variantSize({ heightMm: null, lengthMm: null, widthMm: null }), '');
});
