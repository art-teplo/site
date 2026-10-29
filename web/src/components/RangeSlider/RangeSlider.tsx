"use client";

import { useState, type CSSProperties } from "react";
import styles from "./RangeSlider.module.css";

type Props = {
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  value: [number, number];
  onCommit: (value: [number, number]) => void;
};

// Ползунок «от–до»: два нативных range поверх одной дорожки. Значение уходит наружу при отпускании.
export function RangeSlider({ label, unit, min, max, step, value, onCommit }: Props) {
  const [local, setLocal] = useState<[number, number]>(value);
  // Сброс фильтров снаружи — подхватываем новое значение без эффекта
  const [prev, setPrev] = useState(value);
  if (prev[0] !== value[0] || prev[1] !== value[1]) {
    setPrev(value);
    setLocal(value);
  }

  const pct = (n: number) => ((n - min) / (max - min)) * 100;
  const commit = () => onCommit(local);

  return (
    <fieldset className={styles.range}>
      <legend className={styles.legend}>
        {label}
        <span className={styles.values}>
          {local[0]}–{local[1]} {unit}
        </span>
      </legend>
      <div className={styles.track} style={{ "--from": `${pct(local[0])}%`, "--to": `${pct(local[1])}%` } as CSSProperties}>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={local[0]}
          aria-label={`${label}, от`}
          onChange={(e) => setLocal([Math.min(Number(e.target.value), local[1] - step), local[1]])}
          onPointerUp={commit}
          onKeyUp={commit}
          className={styles.input}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={local[1]}
          aria-label={`${label}, до`}
          onChange={(e) => setLocal([local[0], Math.max(Number(e.target.value), local[0] + step)])}
          onPointerUp={commit}
          onKeyUp={commit}
          className={styles.input}
        />
      </div>
    </fieldset>
  );
}
