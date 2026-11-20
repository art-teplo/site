"use client";

import { useRef, type ReactNode } from "react";
import { cx } from "@/lib/format";
import styles from "./ParameterChoices.module.css";

export function ParameterChoices({ label, value, items, onSelect, render, className }: {
  label: string;
  value: string | null;
  items: { value: string; label: string; disabled?: boolean }[];
  onSelect: (value: string) => void;
  render?: (value: string) => ReactNode;
  className?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  if (!items.length) return null;
  if (items.length === 1) return <div className={cx(styles.single, className)}>{render?.(items[0].value) ?? items[0].label}</div>;
  const enabled = items.filter((item) => !item.disabled);
  const selected = enabled.some((item) => item.value === value) ? value : enabled[0]?.value;
  return <div role="radiogroup" aria-label={label} className={styles.row}>
    {items.map((item, i) => <button key={item.value} type="button" role="radio" aria-checked={value === item.value}
      aria-label={item.label} disabled={item.disabled} tabIndex={selected === item.value ? 0 : -1}
      className={cx(styles.choice, className)} ref={(el) => { refs.current[i] = el; }}
      onClick={() => onSelect(item.value)} onKeyDown={(event) => {
        const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 0;
        if (!step || !enabled.length) return;
        event.preventDefault();
        const next = enabled[(enabled.findIndex((e) => e.value === item.value) + step + enabled.length) % enabled.length];
        refs.current[items.findIndex((e) => e.value === next.value)]?.focus();
        onSelect(next.value);
      }}>{render?.(item.value) ?? item.label}</button>)}
  </div>;
}

// Несколько независимых значений: Tab обходит варианты, Enter/Space включает и снимает выбор.
export function ParameterMultipleChoices({ label, values, items, onToggle, render, className }: {
  label: string;
  values: string[];
  items: { value: string; label: string; disabled?: boolean }[];
  onToggle: (value: string) => void;
  render?: (value: string) => ReactNode;
  className?: string;
}) {
  if (!items.length) return null;
  return <div role="group" aria-label={label} className={styles.row}>
    {items.map((item) => <button key={item.value} type="button" aria-pressed={values.includes(item.value)}
      aria-label={item.label} disabled={item.disabled} className={cx(styles.choice, className)}
      onClick={() => onToggle(item.value)}>{render?.(item.value) ?? item.label}</button>)}
  </div>;
}
