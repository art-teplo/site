// Следующий реальный размер; ручная граница может лежать между размерами.
export function adjacentRangeValue(
  values: readonly number[],
  current: number,
  direction: 1 | -1,
  min = -Infinity,
  max = Infinity,
): number {
  const available = values.filter((value) => value >= min && value <= max);
  if (!available.length) return current;
  if (direction === 1) return available.find((value) => value > current) ?? available[available.length - 1];
  return available.findLast((value) => value < current) ?? available[0];
}
