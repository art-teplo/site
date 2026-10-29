import Link from "next/link";
import styles from "./Breadcrumbs.module.css";

type Crumb = { href?: string; label: string };

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Навигационная цепочка" className={styles.nav}>
      <ol className={styles.list}>
        {items.map((item) => (
          <li key={item.label} className={styles.item}>
            {item.href ? (
              <Link href={item.href} className={styles.link}>
                {item.label}
              </Link>
            ) : (
              <span aria-current="page">{item.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
