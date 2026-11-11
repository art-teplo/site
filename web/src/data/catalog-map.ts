import type { Facet, ModelTile, ShowcaseCard } from "./types";

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
