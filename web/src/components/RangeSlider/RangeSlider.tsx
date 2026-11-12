"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./RangeSlider.module.css";

type Props = {
  min: number;
  max: number;
  value: [number, number]; // применённые значения
  step?: number;
  label: string;
  onChange?: (value: [number, number]) => void; // пока тянут
  onCommit: (value: [number, number]) => void; // отпустили
};

// Двойной ползунок: два прозрачных input[type=range] друг над другом. Значения меняются при перетаскивании,
// в фильтр уходят только при отпускании — без запроса на каждый пиксель.
export function RangeSlider({ min, max, value, step = 1, label, onChange, onCommit }: Props) {
  const [draft, setDraft] = useState<[number, number]>(value);
  const latest = useRef(draft);
  const dragging = useRef(false);

  // Внешнее значение (сброс, переход по ссылке) побеждает, если не тянем
  useEffect(() => {
    if (dragging.current) return;
    latest.current = value;
    setDraft(value);
  }, [value[0], value[1]]); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (next: [number, number]) => {
    latest.current = next;
    setDraft(next);
    onChange?.(next);
  };
  const commit = () => {
    dragging.current = false;
    onCommit(latest.current);
  };

  const span = max - min || 1;
  const from = ((draft[0] - min) / span) * 100;
  const to = ((draft[1] - min) / span) * 100;

  const common = {
    type: "range" as const,
    min,
    max,
    step,
    className: styles.input,
    onPointerDown: () => {
      dragging.current = true;
    },
    onPointerUp: commit,
    onKeyUp: commit,
    onBlur: () => dragging.current && commit(),
  };

  return (
    <div className={styles.slider} style={{ "--from": `${from}%`, "--to": `${to}%` } as React.CSSProperties}>
      <div className={styles.track} aria-hidden="true">
        <div className={styles.fill} />
      </div>
      <input
        {...common}
        aria-label={`${label}: от`}
        value={draft[0]}
        onChange={(e) => set([Math.min(Number(e.target.value), draft[1]), draft[1]])}
      />
      <input
        {...common}
        aria-label={`${label}: до`}
        value={draft[1]}
        onChange={(e) => set([draft[0], Math.max(Number(e.target.value), draft[0])])}
      />
    </div>
  );
}
