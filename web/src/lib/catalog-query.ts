import type { CatalogField, Connection } from "@/data/types";
import { CONNECTION_LABEL } from "./connections";

// Параметры адреса каталога. Формат тот же, что у бэка (apps/catalog/filters.py):
// диапазон — <key>_min / <key>_max, список — <key>=a,b; brand, color, execution тоже через запятую.
// ВАЖНО для страницы серии: один артикул может быть в серии дважды с разным подключением (повёрнутый радиатор).
// Поэтому выбранный ?v, оставшийся за первой страницей таблицы, грузят вместе с подключением из исполнения
// (executionConnection): /api/variants/<артикул>/?series=…&connection=….
export type CatalogQuery = {
  brand?: string;
  type?: string;
  color?: string;
  execution?: string;
  v?: string;
  sort?: Sort;
  page?: number | "all";
  ranges: Record<string, [number?, number?]>;
  lists: Record<string, string[]>;
};

export type Sort = "price" | "-price";
export const SORT_LABEL: Record<"" | Sort, string> = { "": "Популярные", price: "Сначала дешевле", "-price": "Сначала дороже" };

export const RESERVED = new Set(["brand", "type", "color", "execution", "v", "page", "sort"]);
export const PAGE_SIZE_CARDS = 24;
export const PAGE_SIZE_ROWS = 20;

const toNumber = (raw: string | null): number | undefined => {
  if (raw == null || raw.trim() === "") return undefined;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
};
export const csv = (raw: string | null) => (raw ?? "").split(",").map((x) => x.trim()).filter(Boolean);

// Не число и неизвестный ключ пропускаются, поэтому ?height_min=abc — без фильтра
export function parseCatalogQuery(params: URLSearchParams, fields: CatalogField[]): CatalogQuery {
  const query: CatalogQuery = { ranges: {}, lists: {} };
  const brand = params.get("brand")?.trim();
  if (brand) query.brand = brand;
  const type = params.get("type")?.trim();
  if (type) query.type = type;
  const color = params.get("color")?.trim();
  if (color) query.color = color;
  const execution = params.get("execution")?.trim();
  if (execution) query.execution = execution;
  const v = params.get("v")?.trim();
  if (v) query.v = v;
  const sort = params.get("sort");
  if (sort === "price" || sort === "-price") query.sort = sort;
  const page = params.get("page");
  if (page === "all") query.page = "all";
  else {
    const n = toNumber(page);
    if (n !== undefined && Number.isInteger(n) && n >= 1) query.page = n;
  }
  for (const field of fields) {
    if (RESERVED.has(field.key)) continue;
    if (field.kind === "range") {
      const min = toNumber(params.get(`${field.key}_min`));
      const max = toNumber(params.get(`${field.key}_max`));
      if (min !== undefined || max !== undefined) query.ranges[field.key] = [min, max];
    } else if (field.kind === "list") {
      const values = csv(params.get(field.key));
      if (values.length) query.lists[field.key] = values;
    }
  }
  return query;
}

export function serializeCatalogQuery(q: CatalogQuery): string {
  const params = new URLSearchParams();
  if (q.brand) params.set("brand", q.brand);
  if (q.type) params.set("type", q.type);
  if (q.color) params.set("color", q.color);
  if (q.execution) params.set("execution", q.execution);
  if (q.v) params.set("v", q.v);
  if (q.sort) params.set("sort", q.sort);
  if (q.page !== undefined && q.page !== 1) params.set("page", String(q.page));
  for (const [key, [min, max]] of Object.entries(q.ranges)) {
    if (min !== undefined) params.set(`${key}_min`, String(min));
    if (max !== undefined) params.set(`${key}_max`, String(max));
  }
  for (const [key, values] of Object.entries(q.lists)) {
    if (values.length) params.set(key, values.join(","));
  }
  // запятые оставляем как есть: так читаемее адрес, и бэк их разбирает одинаково
  return params.toString().replace(/%2C/g, ",");
}

// Подключение из исполнения '<трубы>-<подключение>'; у исполнения без подключения ('0-') его нет
export function executionConnection(execution: string | undefined): Connection | undefined {
  if (!execution) return undefined;
  const connection = execution.slice(execution.indexOf("-") + 1);
  return connection in CONNECTION_LABEL ? (connection as Connection) : undefined;
}
