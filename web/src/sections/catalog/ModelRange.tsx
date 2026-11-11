import Link from "next/link";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import type { ModelTile } from "@/data/types";
import styles from "./ModelRange.module.css";

// Модельный ряд выбранных брендов: плитки серий с фото, ведут на страницу серии.
export function ModelRange({ tiles, category }: { tiles: ModelTile[]; category: string }) {
  if (!tiles.length) return null;
  return (
    <section className={styles.range} aria-label="Модельный ряд">
      <h2 className={styles.title}>Модельный ряд</h2>
      <ul className={styles.list}>
        {tiles.map((t) => (
          <li key={t.series}>
            <Link href={`/catalog/${category}/${t.series}`} className={styles.tile}>
              <span className={styles.media}>
                {t.image ? (
                  <Picture image={t.image} sizes="(max-width: 767px) 40vw, 160px" fit="contain" />
                ) : (
                  <Frame ratio="1 / 1" rounded={false}>
                    <span className={styles.placeholder} />
                  </Frame>
                )}
              </span>
              <span className={styles.name}>{t.name}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
