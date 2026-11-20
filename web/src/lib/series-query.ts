import { initialExecution } from "./series-selection";
import type { SeriesDetail } from "@/data/types";
import { parseCatalogQuery, type CatalogQuery } from "./catalog-query";

// Запрос таблицы серии из адреса. Один и тот же разбор на сервере (первая страница) и в браузере,
// чтобы после гидрации не было лишнего запроса.
// - исполнение: из адреса, если оно есть у серии, иначе самое частое (default_execution);
// - ?h=<высота> из старой ссылки — стартовый фильтр по высоте, пока своего фильтра высоты нет.
export function seriesQuery(params: URLSearchParams, series: SeriesDetail): { query: CatalogQuery; fromH: boolean } {
  const query = parseCatalogQuery(params, series.filters);
  query.execution = initialExecution(query, series.defaultExecution ?? undefined, series.executions);
  const h = Number(params.get("h"));
  const fromH = !query.ranges.height && Number.isInteger(h) && h > 0;
  if (fromH) query.ranges.height = [h, h];
  return { query, fromH };
}

export const withoutHeight = (query: CatalogQuery): CatalogQuery => {
  const ranges = { ...query.ranges };
  delete ranges.height;
  return { ...query, ranges };
};
