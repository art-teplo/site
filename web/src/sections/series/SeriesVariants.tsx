"use client";

import { useState } from "react";
import { Button } from "@/components/Button/Button";
import { Container } from "@/components/Container/Container";
import { PipeChips } from "@/components/PipeChips/PipeChips";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { SizeDrawing } from "@/components/SizeDrawing/SizeDrawing";
import type { Variants } from "@/data/catalog-map";
import type { CatalogField, SeriesDetail, VariantRow } from "@/data/types";
import { type CatalogQuery } from "@/lib/catalog-query";
import { CONNECTION_LABEL } from "@/lib/connections";
import { cx, formatPrice, plural } from "@/lib/format";
import { pickColor } from "@/lib/series-color";
import styles from "./SeriesVariants.module.css";

type Props = {
  series: SeriesDetail;
  loaded: Variants & { all: boolean };
  query: CatalogQuery;
  selected: VariantRow | null;
  pending: boolean;
  loading: boolean;
  failed: boolean;
  onQuery: (next: CatalogQuery) => void;
  onShowAll: () => void;
  onReset: () => void;
};

const ORIENTATION = { h: "горизонтальный", v: "вертикальный" } as const;
const MOUNT = { wall: "настенный", floor: "напольный" } as const;
const PRICE_COLUMN: CatalogField = { key: "price", label: "Цена", kind: "range", unit: "BYN", column: true, filter: false };

const num = (n: number | null) => (n == null ? "—" : String(n));
const flag = (v: string | number | boolean | undefined) => (v === undefined || v === "" ? "—" : v === true ? "Да" : v === false ? "Нет" : String(v));

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
    case "thermovalve": return row.thermovalve ? "Да" : "Нет";
    case "orientation": return row.orientation ? ORIENTATION[row.orientation] : "—";
    case "mount": return row.mount ? MOUNT[row.mount] : "—";
    default: return flag(row.attrs[key]);
  }
}

// Таблица вариантов серии с фильтрами и чертежом выбранного размера. Клик по строке — ?v=<артикул>.
export function SeriesVariants({ series, loaded, query, selected, pending, loading, failed, onQuery, onShowAll, onReset }: Props) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const picked = pickColor(series.colorGroups, query.color);
  const columns = series.columns.some((c) => c.key === "price") ? series.columns : [...series.columns, PRICE_COLUMN];
  const filterKeys = new Set(series.filters.map((f) => f.key));
  const facets = loaded.facets.filter((f) => filterKeys.has(f.key) && f.kind !== "colors" && f.key !== "connection" && f.key !== "tubes");
  const active = Object.keys(query.ranges).length + Object.values(query.lists).reduce((n, v) => n + v.length, 0);

  const toggleList = (key: string, value: string) => {
    const list = query.lists[key] ?? [];
    onQuery({ ...query, lists: { ...query.lists, [key]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value] } });
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

  const priceCell = (row: VariantRow) => (picked?.anyRal || row.price == null ? "по запросу" : formatPrice(row.price));

  return (
    <Section tone="white" labelledBy="variants-title">
      <Container>
        <SectionHead titleId="variants-title" title="Варианты" />
        {series.executions.length > 0 && (
          <div className={styles.pipes}>
            <PipeChips executions={series.executions} selected={query.execution ?? ""} onSelect={(execution) => onQuery({ ...query, execution })} />
          </div>
        )}

        <div className={styles.layout}>
          <div className={styles.table}>
            {facets.length > 0 && (
              <>
              <Button variant="secondary" className={styles.filterToggle} aria-expanded={filtersOpen} aria-controls="series-filters" onClick={() => setFiltersOpen((o) => !o)}>
                Фильтры{active ? ` · ${active}` : ""}
              </Button>
              <div id="series-filters" className={cx(styles.filters, filtersOpen && styles.filtersOpen)} role="group" aria-label="Фильтры">
                {facets.map((f) =>
                  f.kind === "range" ? (
                    f.min == null || f.max == null || f.min === f.max ? null : (
                      <fieldset key={f.key} className={styles.group}>
                        <legend className={styles.legend}>
                          {f.unit ? `${f.label}, ${f.unit}` : f.label}
                        </legend>
                        <div className={styles.rangeFields}>
                          {([0, 1] as const).map((bound) => {
                            const current = query.ranges[f.key]?.[bound];
                            return (
                              <input
                                key={`${f.key}-${bound}-${current ?? ""}`}
                                type="number"
                                inputMode="numeric"
                                className={styles.numberInput}
                                aria-label={`${f.label}: ${bound === 0 ? "от" : "до"}`}
                                placeholder={String(bound === 0 ? f.min : f.max)}
                                min={f.min ?? undefined}
                                max={f.max ?? undefined}
                                defaultValue={current ?? ""}
                                onBlur={(e) => setRange(f.key, bound, e.target.value, bound === 0 ? f.min : f.max)}
                                onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                              />
                            );
                          })}
                        </div>
                      </fieldset>
                    )
                  ) : f.values.length < 2 && !(query.lists[f.key]?.length) ? null : (
                    <fieldset key={f.key} className={styles.group}>
                      <legend className={styles.legend}>{f.label}</legend>
                      <div className={styles.options}>
                        {f.values.map(({ value, label, count }) => (
                          <label key={value} className={styles.option}>
                            <input
                              type="checkbox"
                              className={styles.optionInput}
                              checked={query.lists[f.key]?.includes(value) ?? false}
                              onChange={() => toggleList(f.key, value)}
                            />
                            <span className={styles.optionLabel}>
                              {label}
                              <span className={styles.optionCount}>{count}</span>
                            </span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  ),
                )}
                {active > 0 && (
                  <Button variant="ghost" onClick={onReset}>
                    Сбросить фильтры
                  </Button>
                )}
              </div>
              </>
            )}

            <p className={styles.found} aria-live="polite">
              {plural(loaded.count, "вариант", "варианта", "вариантов")}
            </p>
            {failed && <p className={styles.error}>Не удалось обновить таблицу. Попробуйте ещё раз или откройте страницу заново.</p>}

            <div className={cx(styles.scroll, pending && styles.pending)} aria-busy={pending} tabIndex={0} role="region" aria-label="Таблица вариантов">
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
                  {loaded.results.map((row) => {
                    const on = row.article === selected?.article;
                    return (
                      <tr key={`${row.article}-${row.connection ?? ""}`} className={cx(styles.row, on && styles.rowOn)} onClick={() => select(row)}>
                        <th scope="row">
                          <button type="button" className={styles.pick} aria-pressed={on} onClick={(e) => (e.stopPropagation(), select(row))}>
                            {row.article}
                          </button>
                        </th>
                        {columns.map((c) =>
                          c.kind === "colors" ? (
                            <td key={c.key}>
                              {picked && !picked.anyRal ? (
                                <span className={styles.color}>
                                  <span className={styles.dot} style={{ background: picked.hex }} aria-hidden="true" />
                                  {picked.name}
                                </span>
                              ) : (
                                <span className={styles.muted}>{picked ? picked.name : "на выбор"}</span>
                              )}
                            </td>
                          ) : c.key === "price" ? (
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
              {loaded.results.length === 0 && !pending && <p className={styles.empty}>Под такие параметры вариантов нет. Сбросьте фильтры или смените подключение.</p>}
            </div>

            {loaded.results.length < loaded.count && (
              <div className={styles.more}>
                <Button variant="secondary" onClick={onShowAll} disabled={loading}>
                  {loading ? "Загружаем…" : `Показать все (${loaded.count})`}
                </Button>
              </div>
            )}
            <p className={styles.hint}>Цена — за выбранный цвет. Точную цену и срок менеджер назовёт по звонку.</p>
          </div>

          <div className={styles.drawing}>
            <SizeDrawing row={selected} ranges={series.ranges} />
          </div>
        </div>
      </Container>
    </Section>
  );
}
