import type { Execution } from "@/data/types";
import type { CatalogQuery } from "./catalog-query";

export function chooseExecution(executions: Execution[], current: Execution | undefined, change: Partial<Pick<Execution, "tubes" | "mount" | "thermovalve" | "connection">>) {
  const entries = Object.entries(change);
  const candidates = executions.filter((e) => entries.every(([key, value]) => (e[key as keyof Execution] ?? null) === (value ?? null)));
  const score = (e: Execution) => Number(Boolean(current?.sourceId) && e.sourceId === current?.sourceId) * 8
    + Number(e.connection === current?.connection) * 4 + Number(e.thermovalve === current?.thermovalve) * 2 + Number(e.mount === current?.mount);
  return candidates.reduce<Execution | undefined>((best, e) => !best || score(e) > score(best) ? e : best, undefined);
}

export function queryWithExecution(query: CatalogQuery, execution: string): CatalogQuery {
  const lists = { ...query.lists };
  for (const key of ["tubes", "connection", "mount", "thermovalve"]) delete lists[key];
  return { ...query, execution, lists };
}

export function executionAtDepth(executions: Execution[], current: Execution | undefined, depth: number) {
  return chooseExecution(executions, current, { tubes: depth });
}

export function seriesPrice({ anyRal, stale, selectedPrice, priceFrom }: {
  anyRal: boolean;
  stale: "pending" | "failed" | null;
  selectedPrice?: number | null;
  priceFrom?: number | null;
}): number | null {
  if (anyRal || stale !== null) return null;
  return selectedPrice === undefined ? priceFrom ?? null : selectedPrice;
}

export function shouldFetchSelected({ article, pending, inRows }: { article?: string; pending: boolean; inRows: boolean }) {
  return Boolean(article && !pending && !inRows);
}

export function initialExecution(query: CatalogQuery, fallback: string | undefined, executions: Execution[]): string | undefined {
  if (query.execution) return query.execution;
  const keys = ["tubes", "connection", "mount", "thermovalve"];
  if (keys.some((key) => query.lists[key]?.length)) {
    return executions.find((e) => keys.every((key) => !query.lists[key]?.length || query.lists[key].includes(String(e[key as keyof Execution] ?? ""))))?.key;
  }
  return query.v ? undefined : fallback;
}

export function offerNavigation(raw: string): URLSearchParams {
  const params = new URLSearchParams(raw);
  for (const key of [...params.keys()]) if (["page", "sort", "v", "o", "brand", "type"].includes(key) || /^(utm_.+|yclid|gclid|fbclid|_openstat)$/.test(key)) params.delete(key);
  return params;
}

export function tablePrice(price: number | null | undefined, stale: "pending" | "failed" | null, anyRal: boolean): number | null {
  return stale || anyRal ? null : price ?? null;
}

export function showcaseQuery(raw: string, article?: string): URLSearchParams {
  const params = offerNavigation(raw);
  if (article) params.set("v", article);
  return params;
}
