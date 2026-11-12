"use client";

import { useRef, useState } from "react";
import type { ColorGroup } from "@/data/types";
import { colorNote } from "@/lib/price";
import { colorLabel } from "@/lib/series-color";
import styles from "./ColorSwatches.module.css";

type Item = { code: string; name: string; hex: string; note: string; anyRal: boolean };

// Кружки цветов с реальным оттенком и надбавкой под ними; радиогруппа со стрелками.
export function ColorSwatches({
  groups,
  selected,
  onSelect,
  size = "m",
  compact = false,
  limit,
}: {
  groups: ColorGroup[];
  selected?: string;
  onSelect?: (code: string) => void;
  size?: "s" | "m";
  compact?: boolean; // только кружки, название и надбавка — в подсказке и в подписи выбранного
  limit?: number; // сколько кружков видно, остальные — за кнопкой «+N»
}) {
  const [open, setOpen] = useState(false);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const items: Item[] = groups.flatMap<Item>((g) =>
    g.colors.length > 0
      ? g.colors.map((c) => ({ code: c.code, name: colorLabel(c.name, c.code), hex: c.hex, note: colorNote(g), anyRal: false }))
      : g.anyRal
        ? [{ code: `any-${g.id}`, name: g.name || "Любой цвет RAL", hex: "", note: colorNote(g), anyRal: true }]
        : [],
  );
  if (items.length === 0) return null;
  const current = items.findIndex((i) => i.code === selected);
  // выбранный цвет не прячем за «+N»
  const shown = limit != null && !open && items.length > limit + 1 && current < limit ? items.slice(0, limit) : items;
  const hidden = items.length - shown.length;
  const tabIndexOf = (i: number) => (current === -1 ? (i === 0 ? 0 : -1) : i === current ? 0 : -1);

  function onKey(e: React.KeyboardEvent, i: number) {
    const step = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = (i + step + shown.length) % shown.length;
    refs.current[next]?.focus();
    onSelect?.(shown[next].code);
  }

  return (
    <div className={styles.list} role="radiogroup" aria-label="Цвет" data-size={size} data-compact={compact || undefined}>
      {shown.map((it, i) => {
        const label = `${it.name}, ${it.note}`;
        return (
          <button
            key={it.code}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={it.code === selected}
            aria-label={label}
            tabIndex={tabIndexOf(i)}
            className={styles.item}
            title={compact ? label : undefined}
            onClick={() => onSelect?.(it.code)}
            onKeyDown={(e) => onKey(e, i)}
          >
            <span className={styles.dot} data-any={it.anyRal || undefined} style={it.anyRal ? undefined : { background: it.hex }} />
            <span className={styles.name}>
              {it.name}
            </span>
            <span className={styles.note}>{it.note}</span>
          </button>
        );
      })}
      {hidden > 0 && (
        <button type="button" className={styles.more} aria-label={`Показать ещё ${hidden} цветов`} onClick={() => setOpen(true)}>
          +{hidden}
        </button>
      )}
    </div>
  );
}
