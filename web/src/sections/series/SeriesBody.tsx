"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { mapVariants, type ApiVariants, type Variants } from "@/data/catalog-map";
import type { SeriesDetail } from "@/data/types";
import { serializeCatalogQuery, type CatalogQuery } from "@/lib/catalog-query";
import { colorForApi } from "@/lib/series-color";
import { seriesQuery, withoutHeight } from "@/lib/series-query";
import { SeriesHero } from "./SeriesHero";
import { SeriesVariants } from "./SeriesVariants";

type Loaded = Variants & { key: string; color: string | undefined; dropped: boolean; all: boolean };
type Props = {
  series: SeriesDetail;
  initial: Variants & { dropped: boolean };
  breadcrumbs: ReactNode;
  topClassName: string;
};

// Строки таблицы: на бэк по /api/series/<slug>/variants/, в демо — те же правила из src/data (грузим только там)
async function fetchVariants(slug: string, raw: CatalogQuery, signal: AbortSignal): Promise<Variants> {
  const query = { ...raw, color: colorForApi(raw.color) };
  if (process.env.NEXT_PUBLIC_DEMO === "1") {
    const { demoVariants } = await import("@/data/catalog-demo");
    return demoVariants(slug, query);
  }
  const q = serializeCatalogQuery({ ...query, brand: undefined, v: undefined });
  const response = await fetch(`/api/series/${encodeURIComponent(slug)}/variants/?${q}`, { signal });
  if (!response.ok) throw new Error(String(response.status));
  return mapVariants((await response.json()) as ApiVariants);
}

// Состояние страницы серии живёт в адресе: ?execution, ?color, ?v, фильтры. Ссылку можно отправить менеджеру.
function Body({ series, initial, breadcrumbs, topClassName }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  // всё, что влияет на строки (кроме v и page): цвет меняет цену, остальное — выборку
  const key = useMemo(() => {
    const p = new URLSearchParams(params.toString());
    p.delete("v");
    p.delete("page");
    return p.toString();
  }, [params]);
  const parsed = useMemo(() => seriesQuery(new URLSearchParams(params.toString()), series), [params, series]);
  // color — с каким цветом загружены строки: от него зависят цены в них
  const [loaded, setLoaded] = useState<Loaded>({ ...initial, key, color: parsed.query.color, all: false });
  const [attempt, setAttempt] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const allController = useRef<AbortController | null>(null);
  const triedAll = useRef<string | null>(null);

  // если по ?h строк нет — работаем без высоты, пока пользователь сам не задаст фильтр
  const dropH = parsed.fromH && loaded.dropped && loaded.key === key;
  const query: CatalogQuery = useMemo(() => (dropH ? withoutHeight(parsed.query) : parsed.query), [dropH, parsed]);
  const pending = key !== loaded.key;
  const stale = loaded.color !== query.color ? (failed ? "failed" : "pending") : null;

  useEffect(() => {
    if (key === loaded.key) return;
    controller.current?.abort();
    allController.current?.abort(); // «Показать все» относится к прежнему запросу
    const c = new AbortController();
    controller.current = c;
    (async () => {
      setFailed(false);
      let data = await fetchVariants(series.slug, { ...parsed.query, page: 1 }, c.signal);
      let dropped = false;
      if (parsed.fromH && data.count === 0) {
        dropped = true;
        data = await fetchVariants(series.slug, { ...withoutHeight(parsed.query), page: 1 }, c.signal);
      }
      if (c.signal.aborted) return;
      setLoaded({ ...data, key, color: parsed.query.color, dropped, all: false });
    })().catch((e) => !c.signal.aborted && (console.error(e), setFailed(true)));
    return () => c.abort();
  }, [key, loaded.key, parsed, series.slug, attempt]);

  const showAll = useCallback(async () => {
    allController.current?.abort();
    const c = new AbortController();
    allController.current = c;
    try {
      setLoading(true);
      const data = await fetchVariants(series.slug, { ...query, page: "all" }, c.signal);
      if (c.signal.aborted) return;
      setFailed(false);
      setLoaded((prev) => (prev.key === key ? { ...prev, ...data, all: true } : prev));
    } catch (e) {
      if (!c.signal.aborted) {
        console.error(e);
        setFailed(true);
      }
    } finally {
      if (allController.current === c) setLoading(false);
    }
  }, [key, query, series.slug]);

  const retry = useCallback(() => {
    if (pending) setAttempt((n) => n + 1);
    else void showAll();
  }, [pending, showAll]);

  const replace = useCallback(
    (next: CatalogQuery) => {
      const q = serializeCatalogQuery({ ...next, page: undefined });
      router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  // Выбранный вариант: ?v=<артикул> среди строк текущего исполнения. Нет такого — выбор молча сбрасывается.
  const article = query.v;
  const selected = article ? (loaded.results.find((r) => r.article === article) ?? null) : null;
  useEffect(() => {
    if (!article || pending || selected || loading) return;
    // строки обрезаны первой страницей — артикул мог остаться за ней, тогда один раз загружаем все (на пару запрос + артикул)
    const attemptKey = `${key}|${article}`;
    if (loaded.results.length < loaded.count && !loaded.all && triedAll.current !== attemptKey) {
      triedAll.current = attemptKey;
      const timer = setTimeout(() => void showAll()); // не синхронно в теле эффекта
      return () => clearTimeout(timer);
    }
    replace({ ...query, v: undefined });
  }, [article, key, pending, loading, selected, loaded, query, replace, showAll]);

  return (
    <>
      <Section className={topClassName} labelledBy="series-title">
        <Container>
          {breadcrumbs}
          <SeriesHero series={series} row={selected} rows={loaded.results} color={query.color} stale={stale} onColor={(color) => replace({ ...query, color })} />
        </Container>
      </Section>
      <SeriesVariants
        series={series}
        loaded={loaded}
        query={query}
        selected={selected}
        pending={pending}
        loading={loading}
        failed={failed}
        onQuery={replace}
        onShowAll={showAll}
        onRetry={retry}
        onReset={() => replace({ lists: {}, ranges: {}, execution: query.execution, color: query.color, v: query.v })}
      />
    </>
  );
}

export function SeriesBody(props: Props) {
  // useSearchParams — только в Suspense; без JS и до гидрации остаётся заголовок и таблица первого экрана
  return (
    <Suspense fallback={<SeriesFallback {...props} />}>
      <Body {...props} />
    </Suspense>
  );
}

function SeriesFallback({ series, breadcrumbs, topClassName }: Props) {
  return (
    <Section className={topClassName} labelledBy="series-title">
      <Container>
        {breadcrumbs}
        <h1 id="series-title">{series.name}</h1>
      </Container>
    </Section>
  );
}
