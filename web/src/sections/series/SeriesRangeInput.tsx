"use client";

import { useId, useRef, useState } from "react";
import { Icon } from "@/components/Icon/Icon";
import { adjacentRangeValue } from "@/lib/range-step";
import styles from "./SeriesRangeInput.module.css";

type Props = {
  label: string;
  value: number | undefined;
  placeholder?: number;
  min?: number;
  max?: number;
  steps?: number[];
  onCommit: (raw: string) => void;
};

// Свободный ввод диапазона; стрелки размеров перебирают значения всей серии.
export function SeriesRangeInput({ label, value, placeholder, min, max, steps, onCommit }: Props) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState(value == null ? "" : String(value));
  const discrete = !!steps?.length;
  const step = (direction: 1 | -1) => {
    const base = placeholder ?? steps?.[0] ?? 0;
    const current = draft.trim() === "" ? base : Number(draft);
    const next = adjacentRangeValue(steps ?? [], Number.isFinite(current) ? current : base, direction, min, max);
    setDraft(String(next));
    input.current?.focus({ preventScroll: true });
  };

  return (
    <div className={styles.field} onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) onCommit(input.current?.value ?? draft);
    }}>
      <input
        id={id}
        ref={input}
        type="number"
        inputMode="numeric"
        className={discrete ? `${styles.input} ${styles.discrete}` : styles.input}
        aria-label={label}
        placeholder={placeholder == null ? undefined : String(placeholder)}
        min={min}
        max={max}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") event.currentTarget.blur();
          else if (discrete && (event.key === "ArrowUp" || event.key === "ArrowDown")) {
            event.preventDefault();
            step(event.key === "ArrowUp" ? 1 : -1);
          }
        }}
      />
      {discrete && (
        <span className={styles.steppers}>
          <button type="button" className={styles.step} aria-label={`${label}: следующее значение`} aria-controls={id} onMouseDown={(event) => event.preventDefault()} onClick={() => step(1)}>
            <Icon name="chevronUp" />
          </button>
          <button type="button" className={styles.step} aria-label={`${label}: предыдущее значение`} aria-controls={id} onMouseDown={(event) => event.preventDefault()} onClick={() => step(-1)}>
            <Icon name="chevronDown" />
          </button>
        </span>
      )}
    </div>
  );
}
