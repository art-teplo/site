"use client";

import { useEffect, useRef, useState } from "react";
import { Container } from "@/components/Container/Container";
import { cx } from "@/lib/format";
import { scrollToSection } from "./scroll";
import styles from "./SeriesTabs.module.css";

export type SeriesTab = { id: string; label: string; count?: number };

// Липкая навигация по разделам страницы серии: клик прокручивает к разделу, при прокрутке подсвечивается текущий.
export function SeriesTabs({ tabs }: { tabs: SeriesTab[] }) {
  const [active, setActive] = useState(tabs[0]?.id ?? "");
  const listRef = useRef<HTMLUListElement>(null);
  const ids = tabs.map((t) => t.id).join("|");

  useEffect(() => {
    const list = ids.split("|");
    let frame = 0;
    const update = () => {
      frame = 0;
      const header = document.querySelector("header")?.getBoundingClientRect().height ?? 0;
      const bar = document.getElementById("series-tabs")?.getBoundingClientRect().height ?? 0;
      const line = header + bar + 24;
      // последний раздел, чей верх уже выше линии; у конца страницы — последний
      const atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
      let current = list[0];
      for (const id of list) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= line) current = id;
      }
      setActive(atEnd ? list[list.length - 1] : current);
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [ids]);

  // Активная вкладка не уезжает за край полосы на узком экране
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>("[aria-current='true']");
    const list = listRef.current;
    if (!el || !list) return;
    list.scrollTo({ left: el.offsetLeft - (list.clientWidth - el.offsetWidth) / 2, behavior: "smooth" });
  }, [active]);

  return (
    <nav id="series-tabs" className={styles.bar} aria-label="Разделы страницы">
      <Container>
        <ul ref={listRef} className={styles.list}>
          {tabs.map((t) => (
            <li key={t.id}>
              <button
                type="button"
                className={cx(styles.tab, t.id === active && styles.active)}
                aria-current={t.id === active ? "true" : undefined}
                onClick={() => {
                  setActive(t.id);
                  scrollToSection(t.id);
                }}
              >
                {t.label}
                {t.count ? <span className={styles.count}>{t.count}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      </Container>
    </nav>
  );
}
