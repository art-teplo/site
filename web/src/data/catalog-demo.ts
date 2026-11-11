// Демо без бэка: фильтры, фасеты и страницы теми же правилами, что API.
// Отдельно от catalog-query.ts, чтобы клиентские компоненты не тянули демо-данные.
import { catalogFields, demoCards, demoSeries, demoSource, publicRow, type DemoVariant } from "@/data/catalog";
import type { CatalogField, ColorGroup, Connection, Facet, FacetValue, ModelTile, ShowcaseCard, VariantRow } from "@/data/types";
import { CONNECTION_LABEL } from "@/lib/connections";
import { PAGE_SIZE_CARDS, PAGE_SIZE_ROWS, RESERVED, csv, type CatalogQuery } from "@/lib/catalog-query";
import { rowPrice } from "@/lib/price";
// --- Демо: фильтрация теми же правилами, что на бэке ---

type Item = { row: DemoVariant; groups: ColorGroup[]; brand: string; brandName: string; series: string };

const itemsOf = (category?: string): Item[] =>
  demoSeries
    .filter((s) => !category || s.category === category)
    .flatMap((s) =>
      demoSource(s.slug).map((row) => ({ row, groups: s.colorGroups, brand: s.brand.slug, brandName: s.brand.name, series: s.slug })),
    );

const rangeValue = (row: DemoVariant, key: string): number | null => {
  switch (key) {
    case "price": return row.priceByn;
    case "height": return row.heightMm;
    case "width": return row.widthMm;
    case "depth": return row.depthMm;
    case "length": return row.lengthMm;
    case "axis": return row.axisMm;
    case "power": return row.powerW;
    case "area": return row.areaM2;
    case "sections": return row.sections;
    default: return null;
  }
};

const listValue = (item: Item, key: string): string | null => {
  const { row } = item;
  switch (key) {
    case "brand": return item.brand;
    case "tubes": return row.tubes == null ? null : String(row.tubes);
    case "connection": return row.connection;
    case "orientation": return row.orientation || null;
    default: return key in row.attrs ? String(row.attrs[key]) : null;
  }
};

// Цвета, доступные строке: явные группы или все группы серии; «Любой RAL» цветов не даёт
const colorsOf = (item: Item): ColorGroup["colors"] => {
  const groups = item.row.colorGroups.length ? item.groups.filter((g) => item.row.colorGroups.includes(g.id)) : item.groups;
  return groups.flatMap((g) => g.colors);
};

const knownCodes = (codes: string[]) => {
  const all = new Set(demoSeries.flatMap((s) => s.colorGroups.flatMap((g) => g.colors.map((c) => c.code))));
  return codes.filter((code) => all.has(code));
};

type Execution = { tubes: number; connection: string | null };
const parseExecutions = (raw: string | undefined): Execution[] | null => {
  if (!raw) return null;
  const list: Execution[] = [];
  for (const part of csv(raw)) {
    const at = part.indexOf("-");
    const tubes = Number(part.slice(0, at));
    const connection = part.slice(at + 1);
    if (at < 1 || !Number.isInteger(tubes) || tubes < 0) continue;
    if (connection !== "" && !(connection in CONNECTION_LABEL)) continue;
    list.push({ tubes, connection: connection === "" ? null : connection });
  }
  return list; // пустой — ничего не подходит
};

type Options = { skip?: string[]; ignoreBrand?: boolean; singleColor?: boolean };

function matches(item: Item, q: CatalogQuery, fields: CatalogField[], { skip = [], ignoreBrand, singleColor }: Options = {}): boolean {
  const { row } = item;
  if (q.brand && !ignoreBrand && !skip.includes("brand") && !csv(q.brand).includes(item.brand)) return false;
  if (q.color && !skip.includes("color")) {
    const codes = knownCodes(singleColor ? csv(q.color).slice(0, 1) : csv(q.color));
    if (codes.length) {
      const own = new Set(colorsOf(item).map((c) => c.code));
      if (!codes.some((code) => own.has(code))) return false;
    }
  }
  if (q.execution && !skip.includes("execution")) {
    const list = parseExecutions(q.execution) ?? [];
    if (!list.some((e) => e.tubes === (row.tubes ?? 0) && e.connection === row.connection)) return false;
  }
  for (const field of fields) {
    if (skip.includes(field.key) || RESERVED.has(field.key)) continue;
    if (field.kind === "range" && q.ranges[field.key]) {
      const [min, max] = q.ranges[field.key];
      const value = rangeValue(row, field.key);
      if (value == null || (min !== undefined && value < min) || (max !== undefined && value > max)) return false;
    }
    if (field.kind === "list" && q.lists[field.key]?.length) {
      const value = listValue(item, field.key);
      if (value == null || !q.lists[field.key].includes(value)) return false;
    }
  }
  return true;
}

const ORIENTATION_LABEL: Record<string, string> = { h: "горизонтальный", v: "вертикальный" };
const ATTR_LABEL: Record<string, string> = { true: "да", false: "нет", water: "водяной", electric: "электрический", combined: "комбинированный" };
const CONNECTION_ORDER = Object.keys(CONNECTION_LABEL);

function facetLabel(key: string, value: string, item: Item): string {
  if (key === "brand") return item.brandName;
  if (key === "connection") return CONNECTION_LABEL[value as Connection] ?? value;
  if (key === "orientation") return ORIENTATION_LABEL[value] ?? value;
  if (key === "tubes") return value;
  return ATTR_LABEL[value] ?? value;
}

function buildFacets(pool: Item[], q: CatalogQuery, fields: CatalogField[], options: Options = {}): Facet[] {
  const facets: Facet[] = [];
  for (const field of fields) {
    if (!field.filter) continue;
    if (options.ignoreBrand && field.key === "brand") continue;
    const base = { key: field.key, label: field.label };
    if (field.kind === "range") {
      const values = pool.map((i) => rangeValue(i.row, field.key)).filter((v): v is number => v != null);
      const decimals = field.key === "area";
      facets.push({
        ...base,
        kind: "range",
        unit: field.unit,
        min: values.length ? (decimals ? Math.min(...values) : Math.floor(Math.min(...values))) : null,
        max: values.length ? (decimals ? Math.max(...values) : Math.ceil(Math.max(...values))) : null,
      });
      continue;
    }
    // свой фильтр в своём счётчике не учитывается; тип и подключение — ещё и исполнение
    const skip = [...(options.skip ?? []), field.key, ...(field.key === "tubes" || field.key === "connection" ? ["execution"] : [])];
    const visible = pool.filter((i) => matches(i, q, fields, { ...options, skip }));
    const counts = new Map<string, FacetValue>();
    if (field.kind === "colors") {
      for (const item of visible) {
        for (const color of colorsOf(item)) {
          const found = counts.get(color.code);
          if (found) found.count += 1;
          else counts.set(color.code, { value: color.code, label: color.name, hex: color.hex, count: 1 });
        }
      }
      const values = [...counts.values()].sort((a, b) => a.value.localeCompare(b.value, "ru"));
      facets.push({ ...base, kind: "colors", values });
      continue;
    }
    for (const item of visible) {
      const value = listValue(item, field.key);
      if (value == null) continue;
      const found = counts.get(value);
      if (found) found.count += 1;
      else counts.set(value, { value, label: facetLabel(field.key, value, item), count: 1 });
    }
    const values = [...counts.values()];
    values.sort((a, b) => {
      if (field.key === "connection") return CONNECTION_ORDER.indexOf(a.value) - CONNECTION_ORDER.indexOf(b.value);
      if (field.key === "orientation") return a.value.localeCompare(b.value);
      const [x, y] = [Number(a.value), Number(b.value)];
      return Number.isFinite(x) && Number.isFinite(y) ? x - y : a.label.localeCompare(b.label, "ru");
    });
    facets.push({ ...base, kind: "list", unit: field.unit, values });
  }
  return facets;
}

const pageOf = <T,>(all: T[], page: CatalogQuery["page"], size: number): T[] => {
  if (page === "all") return all;
  const last = Math.max(1, Math.ceil(all.length / size));
  const n = Math.min(Math.max(typeof page === "number" ? page : 1, 1), last); // вне диапазона — последняя
  return all.slice((n - 1) * size, n * size);
};

export function demoShowcases(
  category: string,
  query: CatalogQuery,
): { count: number; results: ShowcaseCard[]; facets: Facet[]; modelRange: ModelTile[] } {
  const fields = catalogFields(category);
  const pool = itemsOf(category);
  const kept = pool.filter((item) => matches(item, query, fields));
  const cards = demoCards(category, (slug) => kept.filter((i) => i.series === slug).map((i) => i.row));
  const brands = csv(query.brand ?? "");
  const modelRange = brands.length
    ? demoSeries
        .filter((s) => s.category === category && brands.includes(s.brand.slug))
        .map((s) => ({ series: s.slug, name: s.name, image: s.images[0] ?? null }))
    : [];
  return {
    count: cards.length,
    results: pageOf(cards, query.page, PAGE_SIZE_CARDS),
    facets: buildFacets(pool, query, fields),
    modelRange,
  };
}

export function demoVariants(
  slug: string,
  query: CatalogQuery,
): { count: number; results: VariantRow[]; facets: Facet[] } {
  const series = demoSeries.find((s) => s.slug === slug);
  if (!series) return { count: 0, results: [], facets: [] };
  const fields = catalogFields(series.category);
  const pool = itemsOf(series.category).filter((i) => i.series === slug);
  const options: Options = { ignoreBrand: true, singleColor: true };
  const rows = pool.filter((i) => matches(i, query, fields, options));
  const color = knownCodes(csv(query.color ?? "").slice(0, 1))[0];
  const results = pageOf(rows, query.page, PAGE_SIZE_ROWS).map((i) => publicRow(i.row, rowPrice(i.row, i.groups, color)));
  return { count: rows.length, results, facets: buildFacets(pool, query, fields, options) };
}
