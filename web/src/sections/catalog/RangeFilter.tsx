"use client";

import { useState } from "react";
import { RangeSlider } from "@/components/RangeSlider/RangeSlider";
import styles from "./CatalogBrowser.module.css";

type Props = {
  label: string;
  unit: string;
  min: number; // границы фасета
  max: number;
  value: [number?, number?]; // применённый фильтр
  onApply: (value: [number?, number?]) => void;
};

const clamp = (n: number, lo: number, hi: number) => Math.min(Math.max(n, lo), hi);

// Диапазон: компактные «от / до» в одной рамке и двойной ползунок под ними.
// Поля применяются по Enter и уходу из поля, ползунок — при отпускании.
export function RangeFilter({ label, unit, min, max, value, onApply }: Props) {
  const lo = Math.floor(min);
  const hi = Math.ceil(max);
  const step = hi - lo >= 10 ? 1 : 0.1;
  const current: [number, number] = [clamp(value[0] ?? lo, lo, hi), clamp(value[1] ?? hi, lo, hi)];
  const [text, setText] = useState<[string, string]>([String(current[0]), String(current[1])]);

  // Применённое значение изменилось снаружи (сброс, ссылка) — поля берут его
  const sync = `${current[0]}-${current[1]}`;
  const [synced, setSynced] = useState(sync);
  if (synced !== sync) {
    setSynced(sync);
    setText([String(current[0]), String(current[1])]);
  }

  const apply = ([a, b]: [number, number]) => {
    const from = Math.min(a, b);
    const to = Math.max(a, b);
    onApply([from <= lo ? undefined : from, to >= hi ? undefined : to]);
  };
  const fromText = (index: 0 | 1) => {
    const n = Number(text[index].replace(",", "."));
    if (!text[index].trim() || !Number.isFinite(n)) return setText([String(current[0]), String(current[1])]);
    const next: [number, number] = [...current];
    next[index] = clamp(n, lo, hi);
    apply(next);
  };
  const field = (index: 0 | 1, prefix: string) => (
    <label className={styles.rangeField}>
      <span className={styles.rangePrefix}>{prefix}</span>
      <input
        type="text"
        inputMode="decimal"
        className={styles.rangeInput}
        aria-label={`${label}: ${prefix}${unit ? `, ${unit}` : ""}`}
        value={text[index]}
        onChange={(e) => setText((t) => (index === 0 ? [e.target.value, t[1]] : [t[0], e.target.value]))}
        onBlur={() => fromText(index)}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
      />
    </label>
  );

  return (
    <div className={styles.range}>
      <div className={styles.rangeFields}>
        {field(0, "от")}
        <span className={styles.rangeDivider} aria-hidden="true" />
        {field(1, "до")}
      </div>
      <RangeSlider
        min={lo}
        max={hi}
        step={step}
        label={label}
        value={current}
        onChange={(v) => setText([String(v[0]), String(v[1])])}
        onCommit={apply}
      />
    </div>
  );
}
