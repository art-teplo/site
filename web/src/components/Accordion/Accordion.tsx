import type { Faq } from "@/data/types";
import styles from "./Accordion.module.css";

// Вопрос-ответ на нативных <details>: работает без JS, доступен с клавиатуры.
export function Accordion({ items }: { items: Faq[] }) {
  return (
    <div className={styles.list}>
      {items.map((item) => (
        <details key={item.q} className={styles.item} name="faq">
          <summary className={styles.summary}>
            <span className={styles.q}>{item.q}</span>
            <span className={styles.icon} aria-hidden="true" />
          </summary>
          <p className={styles.a}>{item.a}</p>
        </details>
      ))}
    </div>
  );
}
