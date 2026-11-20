"use client";

import type { Execution } from "@/data/types";
import { PIPE_GROUPS, pipeGroup, type PipeGroup } from "@/lib/connections";
import { chooseExecution } from "@/lib/series-selection";
import { ParameterChoices } from "@/components/ParameterChoices/ParameterChoices";
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

const countLabel = (n: number) => `${n} ${n % 10 === 1 && n % 100 !== 11 ? "конфигурация" : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? "конфигурации" : "конфигураций"}`;
const valveKey = (e: Execution) => e.thermovalve == null ? "unknown" : String(e.thermovalve);

export function PipeChips({ executions, selected, onSelect }: {
  executions: Execution[]; selected: string; onSelect: (key: string) => void;
}) {
  const current = executions.find((e) => e.key === selected) ?? executions[0];
  if (!current) return null;
  const depths = [...new Set(executions.map((e) => e.tubes))].sort((a, b) => a - b);
  const showDepth = depths.some((n) => n > 0);
  const atDepth = showDepth ? executions.filter((e) => e.tubes === current?.tubes) : executions;
  const groupOf = (e: Execution): PipeGroup | null => e.connection ? pipeGroup(e.connection) : null;
  const present = (Object.keys(PIPE_GROUPS) as PipeGroup[]).filter((g) => atDepth.some((e) => groupOf(e) === g));
  const activeGroup = groupOf(current);
  const inGroup = present.length ? atDepth.filter((e) => groupOf(e) === activeGroup) : atDepth;
  const connected = inGroup.filter((e) => Boolean(e.connection));
  const valves = [...new Set(connected.map(valveKey))];
  const chips = connected.filter((e) => valveKey(e) === valveKey(current));
  const pick = (pool: Execution[], change: Partial<Pick<Execution, "tubes" | "mount" | "thermovalve">>) => {
    const match = chooseExecution(pool, current, change);
    if (match) onSelect(match.key);
  };
  return <div className={styles.wrap}>
    {showDepth && <div className={styles.block}>
      <p className={styles.title}>Рядов труб в глубину</p>
      <ParameterChoices label="Рядов труб в глубину" value={String(current?.tubes)}
        items={depths.map((n) => ({ value: String(n), label: n ? String(n) : "Уточняется" }))}
        onSelect={(n) => pick(executions, { tubes: Number(n) })} />
    </div>}
    {present.length > 0 && <div className={styles.block}>
      <p className={styles.title}>Как подведены трубы у вас сейчас?</p>
      <ParameterChoices label="Подведение труб" value={activeGroup} className={styles.group}
        items={present.map((g) => ({ value: g, label: `${PIPE_GROUPS[g].label}, ${countLabel(atDepth.filter((e) => groupOf(e) === g).reduce((n,e) => n + e.count,0))}` }))}
        onSelect={(g) => pick(atDepth.filter((e) => groupOf(e) === g), {})}
        render={(g) => <><Schematic group={g as PipeGroup} /><span className={styles.groupName}>{PIPE_GROUPS[g as PipeGroup].label}</span>
          <span className={styles.count}>{countLabel(atDepth.filter((e) => groupOf(e) === g).reduce((n,e) => n + e.count,0))}</span></>} />
    </div>}
    {valves.some((v) => v !== "unknown") && <div className={styles.block}>
      <p className={styles.title}>Встроенный термоклапан</p>
      <ParameterChoices label="Встроенный термоклапан" value={valveKey(current)}
        items={valves.map((value) => ({ value, label: value === "true" ? "Есть" : value === "false" ? "Нет" : "Уточняется" }))}
        onSelect={(v) => pick(inGroup, { thermovalve: v === "unknown" ? null : v === "true" })} />
    </div>}
    {chips.length > 0 && <div className={styles.block}>
      <p className={styles.title}>Вариант подключения</p>
      <ParameterChoices label="Вариант подключения" value={selected}
        items={chips.map((e) => ({ value: e.key, label: e.label }))} onSelect={onSelect} />
    </div>}
  </div>;
}
