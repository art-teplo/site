import type { ColorGroup } from "@/data/types";

// Те же правила, что apps/catalog/pricing.py и выдача бэка: целые BYN, half-up
const roundHalfUp = (value: number) => Math.floor(Math.round(value * 1e6) / 1e6 + 0.5);

// Цена в группе цветов: наценка группы в процентах; «Любой RAL» — по запросу
export function priceInColor(priceByn: number | null, group: ColorGroup): number | null {
  if (priceByn == null || group.anyRal) return null;
  return roundHalfUp(priceByn * (1 + group.percent / 100));
}

export type PriceSource = { priceByn: number | null; colorGroups: number[] };

// Цена строки как у бэка (демо считает её сам). colorGroups пуст — доступны все группы серии.
// С color: группа, где есть этот цвет, среди доступных; нет такой — null.
// Без color: базовая группа, если она доступна, иначе самая дешёвая не «Любой RAL», иначе null.
// Серия без групп — priceByn с округлением. color одно значение (у списка берут первый код).
export function rowPrice(row: PriceSource, groups: ColorGroup[], color?: string): number | null {
  if (row.priceByn == null) return null;
  if (groups.length === 0) return roundHalfUp(row.priceByn);
  const available = row.colorGroups.length ? groups.filter((g) => row.colorGroups.includes(g.id)) : groups;
  if (color) {
    const group = available.find((g) => g.colors.some((c) => c.code === color));
    return group ? priceInColor(row.priceByn, group) : null;
  }
  const base = available.find((g) => g.isBase);
  if (base) return priceInColor(row.priceByn, base);
  const prices = available.filter((g) => !g.anyRal).map((g) => priceInColor(row.priceByn, g));
  const valid = prices.filter((p): p is number => p != null);
  return valid.length ? Math.min(...valid) : null;
}
