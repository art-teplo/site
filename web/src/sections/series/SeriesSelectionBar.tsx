"use client";

import { useEffect, useState, type RefObject } from "react";
import { Button } from "@/components/Button/Button";
import { Container } from "@/components/Container/Container";
import { Icon } from "@/components/Icon/Icon";
import type { SeriesDetail, VariantRow } from "@/data/types";
import { formatPrice } from "@/lib/format";
import { pickColor } from "@/lib/series-color";
import { variantSize } from "@/lib/variant-size";
import { purchaseSectionId, scrollToSection } from "./scroll";
import styles from "./SeriesSelectionBar.module.css";

type Props = {
  series: SeriesDetail;
  row: VariantRow | null;
  color: string | undefined;
  stale: "pending" | "failed" | null;
  tableRef: RefObject<HTMLDivElement | null>;
};

// Сводка выбора видна у таблицы; к цене возвращаем только отдельным нажатием.
export function SeriesSelectionBar({ series, row, color, stale, tableRef }: Props) {
  const [visible, setVisible] = useState(false);
  const hasSelection = row !== null;

  useEffect(() => {
    const table = tableRef.current;
    const purchase = document.getElementById(purchaseSectionId(series.slug));
    if (!table || !hasSelection) return;
    let tableVisible = false;
    let purchaseVisible = false;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === table) tableVisible = entry.isIntersecting && entry.intersectionRect.height > 0;
        if (entry.target === purchase) purchaseVisible = entry.isIntersecting;
      }
      setVisible(tableVisible && !purchaseVisible);
    });
    observer.observe(table);
    if (purchase) observer.observe(purchase);
    return () => observer.disconnect();
  }, [hasSelection, tableRef, series.slug]);

  if (!row || !visible) return null;
  const size = variantSize(row);
  const picked = pickColor(series.colorGroups, color);
  const price = picked?.anyRal || stale === "failed" || row.price == null
    ? "Цена по запросу"
    : stale === "pending" ? "Обновляем цену…" : formatPrice(row.price);

  return (
    <div className={styles.bar} data-tone="white" role="region" aria-label="Выбранный радиатор">
      <Container>
        <div className={styles.content}>
          <div className={styles.details}>
            <span className={styles.name}>{series.name}{size ? ` · ${size}` : ""}</span>
            <span className={styles.article}>Арт. {row.article}</span>
          </div>
          <span className={styles.price} aria-live="polite">{price}</span>
          <Button className={styles.action} onClick={() => scrollToSection(purchaseSectionId(series.slug))}>
            К цене и заявке
            <Icon name="arrowUp" className={styles.arrow} />
          </Button>
        </div>
      </Container>
    </div>
  );
}
