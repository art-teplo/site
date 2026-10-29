import type { ReactNode } from "react";
import { cx } from "@/lib/format";
import styles from "./Section.module.css";

type Props = {
  children: ReactNode;
  id?: string;
  tone?: "light" | "dark" | "white";
  labelledBy?: string;
  className?: string;
  flush?: boolean; // без вертикальных отступов (для полноэкранных полос)
};

// Секция — единица ритма страницы. Тон переключает семантические токены (см. tokens.css).
export function Section({ children, id, tone = "light", labelledBy, className, flush }: Props) {
  return (
    <section
      id={id}
      data-tone={tone}
      aria-labelledby={labelledBy}
      className={cx(styles.section, flush && styles.flush, tone === "dark" && styles.dark, className)}
    >
      {tone === "dark" && <span className={styles.grain} aria-hidden="true" />}
      <div className={styles.inner}>{children}</div>
    </section>
  );
}
