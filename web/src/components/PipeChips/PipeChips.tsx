"use client";

import { useRef } from "react";
import type { Execution } from "@/data/types";
import { PIPE_GROUPS, pipeGroup, type PipeGroup } from "@/lib/connections";
import styles from "./PipeChips.module.css";

// Мини-схемка 64×44: контур радиатора и патрубки (красные) для группы подключений
export function Schematic({ group }: { group: PipeGroup }) {
  const pipes: Record<PipeGroup, [number, number, number, number][]> = {
    side: [
      [4, 12, 12, 12],
      [4, 32, 12, 32],
    ],
    diagonal: [
      [4, 12, 12, 12],
      [60, 32, 52, 32],
    ],
    bottom_edge: [
      [16, 36, 16, 42],
      [24, 36, 24, 42],
    ],
    bottom_ends: [
      [14, 36, 14, 42],
      [50, 36, 50, 42],
    ],
    bottom_center: [
      [27, 36, 27, 42],
      [37, 36, 37, 42],
    ],
  };
  return (
    <svg viewBox="0 0 64 44" width="64" height="44" aria-hidden="true" className={styles.schema}>
      <rect x="12" y="6" width="40" height="30" rx="3" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M22 10v22M32 10v22M42 10v22" stroke="currentColor" strokeWidth="1" opacity="0.4" />
      <g stroke="var(--color-accent)" strokeWidth="3" strokeLinecap="round">
        {pipes[group].map(([x1, y1, x2, y2], i) => (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />
        ))}
      </g>
    </svg>
  );
}

function plural(n: number) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return "вариант";
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return "варианта";
  return "вариантов";
}

function Radio({
  items,
  value,
  onPick,
  label,
  className,
  render,
}: {
  items: { id: string; ariaLabel: string }[];
  value: string | null;
  onPick: (id: string) => void;
  label: string;
  className: string;
  render: (id: string) => React.ReactNode;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const cur = items.findIndex((i) => i.id === value);
  function onKey(e: React.KeyboardEvent, i: number) {
    const step = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const n = (i + step + items.length) % items.length;
    refs.current[n]?.focus();
    onPick(items[n].id);
  }
  return (
    <div role="radiogroup" aria-label={label} className={styles.row}>
      {items.map((it, i) => (
        <button
          key={it.id}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="button"
          role="radio"
          aria-checked={it.id === value}
          aria-label={it.ariaLabel}
          tabIndex={(cur === -1 ? i === 0 : i === cur) ? 0 : -1}
          className={className}
          onClick={() => onPick(it.id)}
          onKeyDown={(e) => onKey(e, i)}
        >
          {render(it.id)}
        </button>
      ))}
    </div>
  );
}

// Выбор исполнения: сначала «как подведены трубы у вас», затем исполнения этой группы.
export function PipeChips({
  executions,
  selected,
  onSelect,
}: {
  executions: Execution[];
  selected: string;
  onSelect: (key: string) => void;
}) {
  const groupOf = (e: Execution): PipeGroup | null => (e.connection ? pipeGroup(e.connection) : null);
  const present = (Object.keys(PIPE_GROUPS) as PipeGroup[]).filter((g) => executions.some((e) => groupOf(e) === g));
  const current = executions.find((e) => e.key === selected);
  const activeGroup = current ? groupOf(current) : null;
  const inGroup = activeGroup ? executions.filter((e) => groupOf(e) === activeGroup) : executions.filter((e) => groupOf(e) === null);
  // Исполнения без группы (электро, без подключения) показываем обычными чипами, если группы не выбрано
  const chips = present.length === 0 ? executions : inGroup;
  // число вариантов, а не исполнений: у исполнения много размеров
  const count = (g: PipeGroup) => executions.filter((e) => groupOf(e) === g).reduce((sum, e) => sum + e.count, 0);
  const loose = present.length > 0 ? executions.filter((e) => groupOf(e) === null) : [];

  return (
    <div className={styles.wrap}>
      {present.length > 0 && (
        <div className={styles.block}>
          <p className={styles.title}>Как подведены трубы у вас сейчас?</p>
          <Radio
            label="Подведение труб"
            className={styles.group}
            value={activeGroup}
            items={present.map((g) => ({ id: g, ariaLabel: `${PIPE_GROUPS[g].label}, ${count(g)} ${plural(count(g))}` }))}
            onPick={(g) => {
              const first = executions.find((e) => groupOf(e) === g);
              if (first) onSelect(first.key);
            }}
            render={(g) => (
              <>
                <Schematic group={g as PipeGroup} />
                <span className={styles.groupName}>{PIPE_GROUPS[g as PipeGroup].label}</span>
                <span className={styles.count}>
                  {count(g as PipeGroup)} {plural(count(g as PipeGroup))}
                </span>
              </>
            )}
          />
        </div>
      )}
      <div className={styles.block}>
        {present.length > 0 && <p className={styles.title}>Исполнение</p>}
        <Radio
          label="Исполнение"
          className={styles.chip}
          value={selected}
          items={[...chips, ...(present.length > 0 && !activeGroup ? [] : loose)].map((e) => ({ id: e.key, ariaLabel: e.label }))}
          onPick={onSelect}
          render={(k) => executions.find((e) => e.key === k)?.label}
        />
      </div>
    </div>
  );
}
