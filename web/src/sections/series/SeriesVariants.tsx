"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/Button/Button";
import { Container } from "@/components/Container/Container";
import { FacetFilter, FacetCharacteristics } from "@/components/FacetFilter/FacetFilter";
import { splitFacetControls, toggleFacetValue } from "@/lib/facet-controls";
import { PipeChips } from "@/components/PipeChips/PipeChips";
import { queryWithExecution, tablePrice } from "@/lib/series-selection";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { SizeDrawing } from "@/components/SizeDrawing/SizeDrawing";
import type { Variants } from "@/data/catalog-map";
import type { CatalogField, SeriesDetail, VariantRow } from "@/data/types";
import { type CatalogQuery } from "@/lib/catalog-query";
import { CONNECTION_LABEL } from "@/lib/connections";
import { cx, formatPrice, plural } from "@/lib/format";
import { facetValueLabel } from "@/lib/facet-labels";
import { pickColor } from "@/lib/series-color";
import { OPEN_FILTERS_EVENT } from "./scroll";
import { SeriesRangeInput } from "./SeriesRangeInput";
import { SeriesSelectionBar } from "./SeriesSelectionBar";
import styles from "./SeriesVariants.module.css";

type Props = {
  series: SeriesDetail;
  loaded: Variants & { all: boolean; key: string };
  query: CatalogQuery;
  selected: VariantRow | null;
  stale: "pending" | "failed" | null;
  pending: boolean;
  quiet: boolean; // сменился только цвет: строки не затемняем
  loading: boolean;
  failed: boolean;
  onQuery: (next: CatalogQuery) => void;
  onShowAll: () => void;
  onRetry: () => void;
  onReset: () => void;
};

const ORIENTATION = { h: "горизонтальный", v: "вертикальный" } as const;
const MOUNT = { wall: "настенный", floor: "напольный" } as const;
const PRICE_COLUMN: CatalogField = { key: "price", label: "Цена", kind: "range", unit: "BYN", column: true, filter: false };

const STEP = 20; // строк за раз; больше, чем на странице, подгружаем целиком

const num = (n: number | null) => (n == null ? "—" : String(n));
// Значение атрибута: булевы — Да/Нет, коды (water, bottom_left) — по-русски, остальное как есть
const flag = (v: string | number | boolean | undefined) =>
  v === undefined || v === "" ? "—" : v === true ? "Да" : v === false ? "Нет" : typeof v === "string" ? facetValueLabel("", v) : String(v);

function cellValue(row: VariantRow, key: string): string {
  switch (key) {
    case "height": return num(row.heightMm);
    case "width": return num(row.widthMm);
    case "depth": return num(row.depthMm);
    case "length": return num(row.lengthMm);
    case "axis": return num(row.axisMm);
    case "power": return num(row.powerW);
    case "area": return num(row.areaM2);
    case "sections": return num(row.sections);
    case "tubes": return num(row.tubes);
    case "connection": return row.connection ? CONNECTION_LABEL[row.connection] : "—";
    case "thermovalve": return row.thermovalve == null ? "—" : row.thermovalve ? "Да" : "Нет";
    case "orientation": return row.orientation ? ORIENTATION[row.orientation] : "—";
    case "mount": return row.mount ? MOUNT[row.mount] : "—";
    default: return flag(row.attrs[key]);
  }
}

// Таблица вариантов серии с фильтрами и чертежом выбранного размера. Клик по строке — ?v=<артикул>.
export function SeriesVariants({ series, loaded, query, selected, stale, pending, quiet, loading, failed, onQuery, onShowAll, onRetry, onReset }: Props) {
  const tableRef = useRef<HTMLDivElement>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  // чип «от — до» в шапке серии раскрывает фильтры (scroll.ts, focusSeriesFilter)
  useEffect(() => {
    const open = () => setFiltersOpen(true);
    window.addEventListener(OPEN_FILTERS_EVENT, open);
    return () => window.removeEventListener(OPEN_FILTERS_EVENT, open);
  }, []);
  // сколько строк открыто; смена выборки (фильтры, цвет, исполнение) возвращает к первым
  const [shown, setShown] = useState({ key: loaded.key, n: STEP });
  const visible = shown.key === loaded.key ? shown.n : STEP;
  const pageRows = loaded.results.slice(0, visible);
  // Цвет меняет состав первых строк: выбранный артикул оставляем видимым, даже если он загружен отдельно.
  const rows = selected && !(pending && !quiet) && !pageRows.some((row) => row.article === selected.article)
    ? [selected, ...pageRows]
    : pageRows;
  const drawingRow = selected ?? loaded.results[0] ?? null;
  const more = () => {
    setShown({ key: loaded.key, n: visible + STEP });
    if (visible + STEP > loaded.results.length && !loaded.all && loaded.results.length < loaded.count) onShowAll();
  };
  const picked = pickColor(series.colorGroups, query.color);
  // колонку, где у всех строк текущей выборки прочерк, не показываем (пока строк нет — оставляем как есть)
  const columns = useMemo(() => {
    const all = series.columns.some((c) => c.key === "price") ? series.columns : [...series.columns, PRICE_COLUMN];
    return loaded.results.length ? all.filter((c) => c.key === "price" || loaded.results.some((r) => cellValue(r, c.key) !== "—")) : all;
  }, [series.columns, loaded.results]);
  const filterKeys = new Set(series.filters.map((f) => f.key));
  const executionFields = new Set(["mount"]);
  if (series.executions.some((execution) => execution.tubes > 0)) executionFields.add("tubes");
  if (series.executions.some((execution) => execution.connection)) {
    executionFields.add("connection");
    executionFields.add("thermovalve");
  }
  const rawFacets = loaded.facets.filter((f) => filterKeys.has(f.key) && !(series.factory_orientation && f.key === "orientation") && f.kind !== "colors" && !executionFields.has(f.key));
  const { controls: facets, constants } = splitFacetControls(rawFacets, query);
  const active = Object.keys(query.ranges).length + Object.values(query.lists).reduce((n, v) => n + v.length, 0);
  const editions = series.editions ?? [];
  const byPosition = Boolean(series.factory_orientation) && editions.every((edition) => edition.orientation);
  const editionLabel = byPosition ? "Положение" : "Модель";
  const orderedEditions = byPosition ? editions : editions.toSorted((a, b) => a.label.localeCompare(b.label, "ru", { numeric: true }));

  const toggleList = (key: string, value: string) => {
    const list = query.lists[key] ?? [];
    onQuery({ ...query, lists: { ...query.lists, [key]: toggleFacetValue(list, value) } });
  };
  const setRange = (key: string, bound: 0 | 1, raw: string, limit: number | null) => {
    const n = raw.trim() === "" ? undefined : Number(raw);
    const [min, max] = query.ranges[key] ?? [];
    const pair: [number?, number?] = bound === 0 ? [n, max] : [min, n];
    const ranges = { ...query.ranges };
    if (n === undefined || !Number.isFinite(n) || n === limit) pair[bound] = undefined;
    if (pair[0] === undefined && pair[1] === undefined) delete ranges[key];
    else ranges[key] = pair;
    onQuery({ ...query, ranges });
  };
  const select = (row: VariantRow) => onQuery({ ...query, v: row.article === selected?.article ? undefined : row.article });

  const priceCell = (row: VariantRow) => {
    const price = tablePrice(row.price, stale, Boolean(picked?.anyRal));
    return stale === "pending" ? "Обновляем…" : stale === "failed" ? "Не удалось обновить" : price == null ? "по запросу" : formatPrice(price);
  };

  return (
    <>
    <Section tone="white" id="variants" labelledBy="variants-title">
      <Container>
        <SectionHead titleId="variants-title" title="Варианты исполнения" />
        {(editions.length > 1 || byPosition) && (
          <nav className={styles.editions} aria-label={editionLabel}>
            <span className={styles.editionLabel}>{editionLabel}</span>
            {orderedEditions.length > 1 ? orderedEditions.map((edition) => (
              <Link key={edition.slug} href={`/catalog/${series.category}/${edition.slug}`} aria-current={edition.slug === series.slug ? "page" : undefined} className={styles.editionLink}>{edition.label}</Link>
            )) : <span>{series.factory_orientation === "h" ? "Горизонтальный" : "Вертикальный"}</span>}
          </nav>
        )}
        {series.executions.length > 0 && (
          <div id="series-pipes" className={styles.pipes}>
            <PipeChips executions={series.executions} selected={query.execution ?? ""} onSelect={(execution) => onQuery(queryWithExecution(query, execution))} />
          </div>
        )}

        {constants.length > 0 && <div className={styles.characteristics}><FacetCharacteristics facets={constants} /></div>}
        {facets.length > 0 && (
          <>
          <Button variant="secondary" className={styles.filterToggle} aria-expanded={filtersOpen} aria-controls="series-filters" onClick={() => setFiltersOpen((o) => !o)}>
            Фильтры{active ? ` · ${active}` : ""}
          </Button>
          <div id="series-filters" className={cx(styles.filters, filtersOpen && styles.filtersOpen)} role="group" aria-label="Фильтры">
            {facets.map((facet) => <fieldset key={facet.key} id={`series-filter-${facet.key}`} className={styles.group}>
              <legend className={styles.legend}>{facet.unit ? `${facet.label}, ${facet.unit}` : facet.label}</legend>
              <FacetFilter facet={facet} query={query} onToggleList={toggleList} renderRange={(f) => (
                <div className={styles.rangeFields}>
                  {([0, 1] as const).map((bound) => {
                    const current = query.ranges[f.key]?.[bound];
                    const opposite = query.ranges[f.key]?.[bound === 0 ? 1 : 0];
                    const minimum = f.min ?? undefined;
                    const maximum = f.max ?? undefined;
                    return <SeriesRangeInput key={`${f.key}-${bound}-${current ?? ""}`}
                      label={`${f.label}: ${bound === 0 ? "от" : "до"}`}
                      placeholder={(bound === 0 ? f.min : f.max) ?? undefined}
                      min={bound === 1 && opposite !== undefined ? Math.max(minimum ?? -Infinity, opposite) : minimum}
                      max={bound === 0 && opposite !== undefined ? Math.min(maximum ?? Infinity, opposite) : maximum}
                      value={current} steps={series.rangeSteps?.[f.key]}
                      onCommit={(raw) => setRange(f.key, bound, raw, bound === 0 ? f.min : f.max)} />;
                  })}
                </div>
              )} />
            </fieldset>)}
            {active > 0 && <Button variant="ghost" onClick={onReset}>Сбросить фильтры</Button>}
          </div>
          </>
        )}

        <div className={styles.layout}>
          <div className={cx(styles.table, selected && styles.tableSelected)}>
            <p className={styles.found} aria-live="polite">
              {plural(loaded.count, "конфигурация", "конфигурации", "конфигураций")}
            </p>
            {failed && (
              <p className={styles.error}>
                Не удалось обновить таблицу.{" "}
                <Button variant="ghost" onClick={onRetry}>
                  Повторить
                </Button>
              </p>
            )}

            <div ref={tableRef} className={cx(styles.scroll, pending && !quiet && styles.pending)} aria-busy={pending && !quiet} tabIndex={0} role="region" aria-label="Таблица вариантов">
              <table className={styles.grid}>
                <thead>
                  <tr>
                    <th scope="col">Арт.</th>
                    {columns.map((c) => (
                      <th key={c.key} scope="col" className={c.key === "price" ? styles.price : undefined}>
                        {c.label}
                        {c.unit && c.key !== "price" ? `, ${c.unit}` : ""}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const on = row.article === selected?.article;
                    return (
                      <tr key={`${row.article}-${row.connection ?? ""}`} className={cx(styles.row, on && styles.rowOn)} onClick={() => select(row)}>
                        <th scope="row">
                          <button type="button" className={styles.pick} aria-pressed={on} onClick={(e) => (e.stopPropagation(), select(row))}>
                            {row.article}
                          </button>
                        </th>
                        {columns.map((c) =>
                          c.key === "price" ? (
                            <td key={c.key} className={styles.price}>
                              {priceCell(row)}
                            </td>
                          ) : (
                            <td key={c.key}>{cellValue(row, c.key)}</td>
                          ),
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {rows.length === 0 && !pending && <p className={styles.empty}>Под такие параметры вариантов нет. Сбросьте фильтры или смените подключение.</p>}
            </div>

            {(visible < loaded.results.length || (!loaded.all && loaded.results.length < loaded.count)) && (
              <div className={styles.more}>
                <Button variant="secondary" onClick={more} disabled={loading || pending}>
                  {loading ? "Загружаем…" : `Показать ещё (${Math.min(STEP, loaded.count - visible)})`}
                </Button>
              </div>
            )}
            {loaded.all && loaded.results.length < loaded.count && visible >= loaded.results.length && (
              <p className={styles.hint}>
                Показаны первые {loaded.results.length} из {loaded.count} — уточните фильтры, чтобы увидеть остальные.
              </p>
            )}
            <p className={styles.hint}>Цена — за выбранный цвет. Точную цену и срок менеджер назовёт по звонку.</p>
          </div>

          <div className={styles.drawing}>
            <SizeDrawing row={drawingRow} />
          </div>
        </div>
      </Container>
    </Section>
    <SeriesSelectionBar series={series} row={pending && !quiet ? null : selected} color={query.color} stale={stale} tableRef={tableRef} />
    </>
  );
}
