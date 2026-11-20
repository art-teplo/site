import type { Connection, Facet, ModelTile, ShowcaseCard, VariantRow } from "./types";

// Ответ /api/series/ → витрина. Общий для сервера (api.ts) и клиентского списка.
export type ApiCard = Omit<ShowcaseCard, "priceFrom" | "hoverImage"> & {
  price_from: number | null;
  hover_image?: ShowcaseCard["hoverImage"];
};

export const mapCard = ({ price_from, hover_image, ...card }: ApiCard): ShowcaseCard => ({
  ...card,
  priceFrom: price_from,
  hoverImage: hover_image ?? null,
});
export type ApiShowcase = { count: number; results: ApiCard[]; facets?: Facet[]; model_range?: ModelTile[] };
export type Showcase = { count: number; results: ShowcaseCard[]; facets: Facet[]; modelRange: ModelTile[] };

export const mapShowcase = (data: ApiShowcase): Showcase => ({
  count: data.count,
  results: data.results.map(mapCard),
  facets: data.facets ?? [],
  modelRange: data.model_range ?? [],
});

// Строка таблицы серии: ответ /api/series/<slug>/variants/ → VariantRow. Общий для сервера и клиента.
export type ApiRow = {
  configuration_label?: string;
  configuration_key?: string;
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
  thermovalve: boolean | null;
  orientation: VariantRow["orientation"] | null;
  mount: VariantRow["mount"] | null;
  attrs: VariantRow["attrs"];
  price: number | null;
  price_byn?: number | null;
  color_groups?: number[];
};

export const mapRow = (row: ApiRow): VariantRow => ({
  configurationLabel: row.configuration_label,
  configurationKey: row.configuration_key,
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
  priceByn: row.price_byn,
  colorGroups: row.color_groups,
});

export type ApiVariants = { count: number; results: ApiRow[]; facets: Facet[]; price_from?: number | null };
export type Variants = { count: number; results: VariantRow[]; facets: Facet[]; priceFrom?: number | null };
export const mapVariants = (data: ApiVariants): Variants => ({ count: data.count, results: data.results.map(mapRow), facets: data.facets, priceFrom: data.price_from });
