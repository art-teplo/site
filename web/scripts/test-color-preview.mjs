import assert from 'node:assert/strict';
import { test } from 'node:test';
import { colorPreview } from '../src/lib/color-preview.ts';

test('any RAL remains visible alongside the first concrete colours', () => {
  const colors = ['white', 'black', 'silver', 'gold', 'red', 'blue', 'any-ral'].map((code) => ({ code }));
  const result = colorPreview(colors, 5);
  assert.deepEqual(result.visible.map((color) => color.code), ['white', 'black', 'silver', 'gold', 'any-ral']);
  assert.equal(result.extra, 2);
  assert.equal(colors.length, 7);
});

test('ordinary short palettes retain their source order', () => {
  const colors = [{ code: 'white' }, { code: 'black' }];
  assert.deepEqual(colorPreview(colors, 5), { visible: colors, extra: 0 });
});
