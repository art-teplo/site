"use client";

import { useId, useState, type ReactNode } from "react";
import styles from "./CatalogBrowser.module.css";

// Группа фильтра: заголовок-кнопка с шевроном; счётчик выбранного виден и в свёрнутом виде.
export function FilterGroup({ title, defaultOpen, selected, children }: { title: string; defaultOpen: boolean; selected: number; children: ReactNode }) {
  const [toggled, setToggled] = useState<boolean | null>(null);
  const id = useId();
  // Пока пользователь не трогал — по умолчанию; активный фильтр всегда раскрывает группу
  const open = toggled ?? (defaultOpen || selected > 0);
  return (
    <section className={styles.group}>
      <h3 className={styles.groupHead}>
        <button type="button" className={styles.groupButton} aria-expanded={open} aria-controls={id} onClick={() => setToggled(!open)}>
          <span className={styles.groupTitle}>{title}</span>
          {selected > 0 && <span className={styles.badge}>{selected}</span>}
          <svg className={styles.chevron} viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="m5 8 5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </h3>
      <div id={id} className={styles.groupBody} hidden={!open}>
        {children}
      </div>
    </section>
  );
}
