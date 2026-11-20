"use client";

import { useState } from "react";
import { RangeSlider } from "@/components/RangeSlider/RangeSlider";
import styles from "./CatalogBrowser.module.css";

type Props = {
  label: string;
  unit: string;
  min: number | null;
  max: number | null;
  value: [number?, number?];
  onApply: (value: [number?, number?]) => void;
};

const clamp = (n: number, lo: number, hi: number) => Math.min(Math.max(n, lo), hi);
const display = (value: number | undefined) => value === undefined ? "" : String(value);

// Применённые границы остаются редактируемыми даже при пустой выдаче; пустое поле снимает границу.
export function RangeFilter({ label, unit, min, max, value, onApply }: Props) {
  const lo = min == null ? null : Math.floor(min);
  const hi = max == null ? null : Math.ceil(max);
  const [text, setText] = useState<[string, string]>([display(value[0]), display(value[1])]);
  const sync = `${value[0]}-${value[1]}`;
  const [synced, setSynced] = useState(sync);
  if (synced !== sync) {
    setSynced(sync);
    setText([display(value[0]), display(value[1])]);
  }

  const fromText = (index: 0 | 1) => {
    const raw = text[index].trim();
    const n = raw === "" ? undefined : Number(raw.replace(",", "."));
    if (n !== undefined && !Number.isFinite(n)) {
      setText([display(value[0]), display(value[1])]);
      return;
    }
    const next: [number?, number?] = [...value];
    next[index] = n;
    if (next[0] !== undefined && next[1] !== undefined && next[0] > next[1]) next.reverse();
    onApply(next);
  };
  const field = (index: 0 | 1, prefix: string) => (
    <label className={styles.rangeField}>
      <span className={styles.rangePrefix}>{prefix}</span>
      <input type="text" inputMode="decimal" className={styles.rangeInput}
        aria-label={`${label}: ${prefix}${unit ? `, ${unit}` : ""}`}
        placeholder={String((index === 0 ? lo : hi) ?? "")}
        value={text[index]} onChange={(e) => setText((t) => index === 0 ? [e.target.value, t[1]] : [t[0], e.target.value])}
        onBlur={() => fromText(index)} onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()} />
    </label>
  );

  return <div className={styles.range}>
    <div className={styles.rangeFields}>
      {field(0, "от")}<span className={styles.rangeDivider} aria-hidden="true" />{field(1, "до")}
    </div>
    {lo != null && hi != null && lo < hi && <RangeSlider min={lo} max={hi} step={hi - lo >= 10 ? 1 : 0.1}
      label={label} value={[clamp(value[0] ?? lo, lo, hi), clamp(value[1] ?? hi, lo, hi)]}
      onChange={(pair) => setText([String(pair[0]), String(pair[1])])}
      onCommit={([a, b]) => onApply([a <= lo ? undefined : a, b >= hi ? undefined : b])} />}
  </div>;
}
