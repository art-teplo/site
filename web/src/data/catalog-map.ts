import type { Connection, Facet, ModelTile, ShowcaseCard, VariantRow } from "./types";

// Ответ /api/series/ → витрина. Общий для сервера (api.ts) и клиентского списка.
type ApiCard = Omit<ShowcaseCard, "heightMm" | "priceFrom"> & { height_mm: number | null; price_from: number | null };
export type ApiShowcase = { count: number; results: ApiCard[]; facets: Facet[]; model_range: ModelTile[] };
export type Showcase = { count: number; results: ShowcaseCard[]; facets: Facet[]; modelRange: ModelTile[] };

export const mapShowcase = (data: ApiShowcase): Showcase => ({
  count: data.count,
  results: data.results.map(({ height_mm, price_from, ...card }) => ({ ...card, heightMm: height_mm, priceFrom: price_from })),
  facets: data.facets,
  modelRange: data.model_range,
});

// Строка таблицы серии: ответ /api/series/<slug>/variants/ → VariantRow. Общий для сервера и клиента.
export type ApiRow = {
  article: string;
  height_mm: number | null;
  width_mm: number | null;
  depth_mm: number | null;
  length_mm: number | null;
  axis_mm: number | null;
  sections: number | null;
  power_w: number | null;
  area_m2: number | null;
  tubes: number | null;
  connection: Connection | "" | null;
  thermovalve: boolean;
  orientation: VariantRow["orientation"] | null;
  mount: VariantRow["mount"] | null;
  attrs: VariantRow["attrs"];
  price: number | null;
};

export const mapRow = (row: ApiRow): VariantRow => ({
  article: row.article,
  heightMm: row.height_mm,
  widthMm: row.width_mm,
  depthMm: row.depth_mm,
  lengthMm: row.length_mm,
  axisMm: row.axis_mm,
  sections: row.sections,
  powerW: row.power_w,
  areaM2: row.area_m2,
  tubes: row.tubes,
  connection: row.connection || null,
  thermovalve: row.thermovalve,
  orientation: row.orientation ?? "",
  mount: row.mount ?? "",
  attrs: row.attrs ?? {},
  price: row.price,
});

export type ApiVariants = { count: number; results: ApiRow[]; facets: Facet[] };
export type Variants = { count: number; results: VariantRow[]; facets: Facet[] };
export const mapVariants = (data: ApiVariants): Variants => ({ count: data.count, results: data.results.map(mapRow), facets: data.facets });
