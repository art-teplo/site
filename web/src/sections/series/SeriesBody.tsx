"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Container } from "@/components/Container/Container";
import { Button } from "@/components/Button/Button";
import { Section } from "@/components/Section/Section";
import { mapRow, mapVariants, type ApiRow, type ApiVariants, type Variants } from "@/data/catalog-map";
import type { SeriesDetail, VariantRow } from "@/data/types";
import { executionConnection, serializeCatalogQuery, type CatalogQuery } from "@/lib/catalog-query";
import { rowPrice } from "@/lib/price";
import { colorForApi } from "@/lib/series-color";
import { seriesQuery, withoutHeight } from "@/lib/series-query";
import { shouldFetchSelected } from "@/lib/series-selection";
import { SeriesHero } from "./SeriesHero";
import { SeriesVariants } from "./SeriesVariants";

// Выбранный ?v, которого нет на первой странице таблицы: одна строка с эндпоинта варианта (null — такого нет)
type Extra = { key: string; row: VariantRow | null; failed?: boolean };
type Loaded = Variants & { key: string; color: string | undefined; dropped: boolean; all: boolean };
type Props = {
  series: SeriesDetail;
  initial: Variants & { dropped: boolean };
  breadcrumbs: ReactNode;
  topClassName: string;
  tabs: ReactNode; // липкая полоса разделов: между первым экраном и таблицей
  images: SeriesDetail["images"];
};

// Строки таблицы: на бэк по /api/series/<slug>/variants/, в демо — те же правила из src/data (грузим только там)
async function fetchVariants(slug: string, raw: CatalogQuery, signal: AbortSignal): Promise<Variants> {
  const query = { ...raw };
  if (process.env.NEXT_PUBLIC_DEMO === "1") {
    const { demoVariants } = await import("@/data/catalog-demo");
    return demoVariants(slug, query);
  }
  const q = serializeCatalogQuery({ ...query, brand: undefined, v: undefined });
  const response = await fetch(`/api/series/${encodeURIComponent(slug)}/variants/?${q}`, { signal });
  if (!response.ok) throw new Error(String(response.status));
  return mapVariants((await response.json()) as ApiVariants);
}

// Один вариант: /api/variants/<артикул>/?series=…&connection=…; в демо — из src/data. Нет такого — null
async function fetchVariant(slug: string, article: string, query: CatalogQuery, signal: AbortSignal): Promise<VariantRow | null> {
  const connection = executionConnection(query.execution);
  const color = query.color;
  if (process.env.NEXT_PUBLIC_DEMO === "1") {
    const { demoVariant } = await import("@/data/catalog-demo");
    return demoVariant(slug, article, connection, color);
  }
  const params = new URLSearchParams(serializeCatalogQuery({ ...query, brand: undefined, v: undefined, page: undefined, color }));
  params.set("series", slug);
  if (connection) params.set("connection", connection);
  if (color) params.set("color", color);
  const response = await fetch(`/api/variants/${encodeURIComponent(article)}/?${params}`, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(String(response.status));
  return mapRow((await response.json()) as ApiRow);
}

const withoutColorKey = (k: string) => {
  const p = new URLSearchParams(k);
  p.delete("color");
  return p.toString();
};

// Состояние страницы серии живёт в адресе: ?execution, ?color, ?v, фильтры. Ссылку можно отправить менеджеру.
function Body({ series, initial, breadcrumbs, topClassName, tabs, images }: Props) {
  const pathname = usePathname();
  const params = useSearchParams();
  const [failed, setFailed] = useState(false);
  const [selectionNotice, setSelectionNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // всё, что влияет на строки (кроме v и page): цвет меняет цену, остальное — выборку
  const key = useMemo(() => {
    const p = new URLSearchParams(params.toString());
    p.delete("v");
    p.delete("page");
    p.delete("o");
    return p.toString();
  }, [params]);
  const parsed = useMemo(() => seriesQuery(new URLSearchParams(params.toString()), series), [params, series]);
  // color — с каким цветом загружены строки: от него зависят цены в них
  const [loaded, setLoaded] = useState<Loaded>({ ...initial, key, color: parsed.query.color, all: false });
  const [attempt, setAttempt] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const allController = useRef<AbortController | null>(null);
  const [extra, setExtra] = useState<Extra | null>(null);

  // если по ?h строк нет — работаем без высоты, пока пользователь сам не задаст фильтр
  const dropH = parsed.fromH && loaded.dropped && loaded.key === key;
  const query: CatalogQuery = useMemo(() => (dropH ? withoutHeight(parsed.query) : parsed.query), [dropH, parsed]);
  const pending = key !== loaded.key;
  // сменился только цвет: таблицу не затемняем, старые строки стоят, пока не придут новые (запрос быстрый)
  const colorOnly = pending && withoutColorKey(key) === withoutColorKey(loaded.key);
  // Сменился цвет, а строки ещё со старым: если в них есть цена без цвета — пересчитываем сразу, как бэк
  const repriceable = colorOnly && loaded.color !== query.color && loaded.results.every((r) => r.priceByn !== undefined);
  const reprice = useCallback(
    (row: VariantRow): VariantRow =>
      row.priceByn === undefined ? row : { ...row, price: rowPrice({ priceByn: row.priceByn, colorGroups: row.colorGroups ?? [] }, series.colorGroups, colorForApi(query.color)) },
    [series.colorGroups, query.color],
  );
  const shown: Loaded = useMemo(() => (repriceable ? { ...loaded, results: loaded.results.map(reprice), priceFrom: undefined } : loaded), [repriceable, loaded, reprice]);
  const stale = pending && !repriceable ? (failed ? "failed" : "pending") : null;

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

  // Адрес меняем в истории без перехода: useSearchParams подхватывает его, а сервер страницу не пересобирает
  // (строки браузер и так грузит сам)
  const replace = useCallback(
    (next: CatalogQuery) => {
      const q = serializeCatalogQuery({ ...next, page: undefined });
      window.history.replaceState(null, "", q ? `${pathname}?${q}` : pathname);
    },
    [pathname],
  );

  // Выбранный вариант: ?v=<артикул> среди строк текущего исполнения. Остался за первой страницей — берём его
  // отдельным запросом, а не грузим всю таблицу. Нет такого — выбор молча сбрасывается.
  const article = query.v;
  const attemptKey = article ? `${key}|${article}` : null;
  const inRows = article ? (shown.results.find((r) => r.article === article) ?? null) : null;
  const fetched = extra && extra.key === attemptKey ? extra : null;
  const selected = inRows ?? (fetched?.row ? reprice(fetched.row) : null);
  useEffect(() => {
    if (!shouldFetchSelected({ article, pending, inRows: Boolean(inRows) }) || !article || !attemptKey) return;
    if (fetched) {
      if (!fetched.row && !fetched.failed) replace({ ...query, v: undefined });
      return;
    }
    const c = new AbortController();
    (async () => {
      const row = await fetchVariant(series.slug, article, query, c.signal);
      if (!c.signal.aborted) {
        setExtra({ key: attemptKey, row });
        setSelectionNotice(row ? null : `Артикул ${article} недоступен с выбранными параметрами. Выберите другой размер в таблице.`);
      }
    })().catch((e) => {
      if (c.signal.aborted) return;
      console.error(e);
      setExtra({ key: attemptKey, row: null, failed: true });
    });
    return () => c.abort();
  }, [article, attemptKey, pending, inRows, fetched, query, replace, series.slug]);

  return (
    <>
      <Section className={topClassName} labelledBy="series-title">
        <Container>
          {breadcrumbs}
          <SeriesHero series={series} images={images} row={selected} color={query.color} stale={stale} configurationPriceFrom={shown.priceFrom} onColor={(color) => replace({ ...query, color })} />
          {selectionNotice && <p role="status">{selectionNotice}</p>}
          {fetched?.failed && <p role="status">Не удалось загрузить выбранный артикул. <Button variant="secondary" onClick={() => setExtra(null)}>Повторить</Button></p>}
        </Container>
      </Section>
      {tabs}
      <SeriesVariants
        series={series}
        loaded={shown}
        query={query}
        selected={selected}
        stale={stale}
        pending={pending}
        quiet={colorOnly}
        loading={loading}
        failed={failed}
        onQuery={(next) => { if (next.v) setSelectionNotice(null); replace(next); }}
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
