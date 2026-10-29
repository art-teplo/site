// Логика фильтров каталога: чистые функции, состояние живёт в URL (?type=…&hmin=…).
// Когда появится API, тот же формат параметров уйдёт на бэкенд (django-filter).
import type { Product } from "@/data/types";

export type Facet = { key: FacetKey; label: string; values: { value: string; count: number }[] };
export type FacetKey = "type" | "position" | "connection" | "material" | "heating" | "color" | "brand";
export type RangeKey = "height" | "width" | "axis" | "power" | "area" | "price";
export type Range = { key: RangeKey; label: string; unit: string; min: number; max: number; step: number };

const FACET_LABELS: Record<FacetKey, string> = {
  type: "Тип",
  position: "Положение",
  connection: "Подключение",
  material: "Материал",
  heating: "Нагрев",
  color: "Цвет",
  brand: "Бренд",
};

const SIDE_CONNECTION = "боковое (диагональное)";

// Площадь обогрева — по правилу заказчика: 100 Вт на м²
export const WATTS_PER_M2 = 100;

const valuesOf = (p: Product, key: FacetKey): string[] => {
  switch (key) {
    case "type":
      return [p.type];
    case "position":
      return p.position ? [p.position] : [];
    case "connection":
      // Боковое и диагональное в фильтре — одно значение (как в таблице заказчика)
      return p.connections.map((c) => (c === "боковое" || c === "диагональное" ? SIDE_CONNECTION : c));
    case "material":
      return [p.material];
    case "heating":
      return [p.heating];
    case "color":
      return p.colors.map((c) => c.name);
    case "brand":
      return [p.brand];
  }
};

// Межосевое расстояние задано на товар, остальное — на вариант
const variantValue = (p: Product, v: Product["variants"][number], key: RangeKey): number | undefined => {
  switch (key) {
    case "height":
      return v.heightMm;
    case "width":
      return v.widthMm;
    case "axis":
      return p.axisMm;
    case "power":
      return v.powerW;
    case "area":
      return Math.round((v.powerW / WATTS_PER_M2) * 10) / 10;
    case "price":
      return v.priceByn;
  }
};

export function buildFacets(products: Product[]): Facet[] {
  return (Object.keys(FACET_LABELS) as FacetKey[])
    .map((key) => {
      const counts = new Map<string, number>();
      for (const p of products) for (const v of new Set(valuesOf(p, key))) counts.set(v, (counts.get(v) ?? 0) + 1);
      const values = [...counts].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count);
      return { key, label: FACET_LABELS[key], values };
    })
    .filter((f) => f.values.length > 1);
}

export function buildRanges(products: Product[]): Range[] {
  const defs: Array<Omit<Range, "min" | "max">> = [
    { key: "height", label: "Высота", unit: "мм", step: 50 },
    { key: "width", label: "Ширина", unit: "мм", step: 50 },
    { key: "axis", label: "Межосевое расстояние", unit: "мм", step: 50 },
    { key: "power", label: "Мощность", unit: "Вт", step: 50 },
    { key: "area", label: "Площадь обогрева", unit: "м²", step: 1 },
    { key: "price", label: "Цена", unit: "BYN", step: 50 },
  ];
  return defs
    .map((d) => {
      const all = products.flatMap((p) => p.variants.map((v) => variantValue(p, v, d.key) ?? 0)).filter((n) => n > 0);
      if (!all.length) return null;
      const min = Math.floor(Math.min(...all) / d.step) * d.step;
      const max = Math.ceil(Math.max(...all) / d.step) * d.step;
      return min === max ? null : { ...d, min, max };
    })
    .filter((r): r is Range => r !== null);
}

const RANGE_KEYS: RangeKey[] = ["height", "width", "axis", "power", "area", "price"];

export type FilterState = {
  facets: Partial<Record<FacetKey, string[]>>;
  ranges: Partial<Record<RangeKey, [number, number]>>;
  sort: "default" | "price-asc" | "price-desc";
};

export function parseFilters(params: URLSearchParams): FilterState {
  const facets: FilterState["facets"] = {};
  for (const key of Object.keys(FACET_LABELS) as FacetKey[]) {
    const all = params.getAll(key);
    if (all.length) facets[key] = all;
  }
  const ranges: FilterState["ranges"] = {};
  for (const key of RANGE_KEYS) {
    const min = Number(params.get(`${key}_min`));
    const max = Number(params.get(`${key}_max`));
    if (params.has(`${key}_min`) || params.has(`${key}_max`)) ranges[key] = [min || 0, max || Infinity];
  }
  const sort = (params.get("sort") as FilterState["sort"]) || "default";
  return { facets, ranges, sort };
}

export function applyFilters(products: Product[], state: FilterState): Product[] {
  const result = products.filter((p) => {
    for (const [key, selected] of Object.entries(state.facets) as [FacetKey, string[]][]) {
      if (selected.length && !valuesOf(p, key).some((v) => selected.includes(v))) return false;
    }
    const rangeEntries = Object.entries(state.ranges) as [RangeKey, [number, number]][];
    if (!rangeEntries.length) return true;
    // Подходит, если хотя бы один вариант влезает во все диапазоны сразу
    return p.variants.some((v) => rangeEntries.every(([key, [min, max]]) => {
      const value = variantValue(p, v, key);
      return value !== undefined && value >= min && value <= max;
    }));
  });
  const price = (p: Product) => Math.min(...p.variants.map((v) => v.priceByn));
  if (state.sort === "price-asc") result.sort((a, b) => price(a) - price(b));
  if (state.sort === "price-desc") result.sort((a, b) => price(b) - price(a));
  return result;
}

export const activeCount = (state: FilterState) =>
  Object.values(state.facets).reduce((n, v) => n + (v?.length ?? 0), 0) + Object.keys(state.ranges).length;
