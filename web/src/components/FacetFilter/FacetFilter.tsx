"use client";

import type { ReactNode } from "react";
import type { Facet } from "@/data/types";
import type { CatalogQuery } from "@/lib/catalog-query";
import { facetValueLabel } from "@/lib/facet-labels";
import { colorLabel } from "@/lib/series-color";
import { ParameterMultipleChoices } from "@/components/ParameterChoices/ParameterChoices";
import styles from "./FacetFilter.module.css";

type RangeFacet = Extract<Facet, { kind: "range" }>;

// Вид поля определяется схемой, включая будущие attrs; диапазон получает управление своей страницы.
export function FacetFilter({ facet, query, onToggleList, onToggleColor, renderRange }: {
  facet: Facet;
  query: Pick<CatalogQuery, "lists" | "ranges" | "color">;
  onToggleList: (key: string, value: string) => void;
  onToggleColor?: (value: string) => void;
  renderRange: (facet: RangeFacet) => ReactNode;
}) {
  if (facet.kind === "range") return renderRange(facet);
  if (facet.kind === "colors") return <div className={styles.swatches} role="group" aria-label={facet.label}>
    {facet.values.map((item) => <button key={item.value} type="button" className={styles.swatch}
      style={{ background: item.hex }} title={colorLabel(item.label, item.value)}
      aria-label={colorLabel(item.label, item.value)} aria-pressed={(query.color ?? "").split(",").includes(item.value)}
      onClick={() => onToggleColor?.(item.value)} />)}
  </div>;
  return <ParameterMultipleChoices label={facet.label} values={query.lists[facet.key] ?? []}
    items={facet.values.map((item) => ({ value: item.value, label: facetValueLabel(item.label, item.value) }))}
    className={styles.textChoice} onToggle={(value) => onToggleList(facet.key, value)}
    render={(value) => {
      const item = facet.values.find((item) => item.value === value)!;
      return <>{facetValueLabel(item.label, value)}<span className={styles.count}>{item.count}</span></>;
    }} />;
}

export function FacetCharacteristics({ facets }: { facets: Facet[] }) {
  if (!facets.length) return null;
  return <dl className={styles.characteristics} aria-label="Характеристики">
    {facets.map((facet) => <div key={facet.key} className={styles.characteristic}>
      <dt>{facet.label}</dt>
      <dd>{facet.kind === "range" ? `${facet.min}${facet.unit ? ` ${facet.unit}` : ""}`
        : facet.values.map((item) => facetValueLabel(item.label, item.value)).join(", ")}</dd>
    </div>)}
  </dl>;
}
