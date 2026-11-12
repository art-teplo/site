"use client";

import { useState } from "react";
import { ProjectCard } from "@/components/ProjectCard/ProjectCard";
import type { Project } from "@/data/types";
import { cx } from "@/lib/format";
import styles from "./ProjectsBrowser.module.css";

const FILTERS: { id: "all" | Project["kind"]; label: string }[] = [
  { id: "all", label: "Все" },
  { id: "квартира", label: "Квартиры" },
  { id: "дом", label: "Дома" },
  { id: "ЖК", label: "Жилые комплексы" },
];

// Проекты с фильтром по типу объекта (как «квартиры и дома / ЖК» на kztoradiator.by).
export function ProjectsBrowser({ projects, seriesLinks = {} }: { projects: Project[]; seriesLinks?: Record<string, { name: string; href: string }> }) {
  const [kind, setKind] = useState<(typeof FILTERS)[number]["id"]>("all");
  const shown = kind === "all" ? projects : projects.filter((p) => p.kind === kind);

  return (
    <>
      <div className={styles.filters} role="group" aria-label="Тип объекта">
        {FILTERS.map((f) => {
          const count = f.id === "all" ? projects.length : projects.filter((p) => p.kind === f.id).length;
          return (
            <button
              key={f.id}
              type="button"
              className={cx(styles.filter, kind === f.id && styles.active)}
              aria-pressed={kind === f.id}
              onClick={() => setKind(f.id)}
              disabled={count === 0}
            >
              {f.label} <span className={styles.count}>{count}</span>
            </button>
          );
        })}
      </div>
      <ul className={styles.grid} aria-live="polite">
        {shown.map((p) => (
          <li key={p.slug} className={styles.item}>
            <ProjectCard
              project={p}
              ratio="4 / 3"
              sizes="(max-width: 767px) 100vw, (max-width: 1023px) 50vw, 33vw"
              stands={p.series.flatMap((slug) => (seriesLinks[slug] ? [seriesLinks[slug]] : []))}
            />
          </li>
        ))}
      </ul>
    </>
  );
}
