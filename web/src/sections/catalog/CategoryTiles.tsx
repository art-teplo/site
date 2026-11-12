import Link from "next/link";
import { Arrow } from "@/components/Button/Button";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import type { Category } from "@/data/types";
import { cx, plural } from "@/lib/format";
import styles from "./CategoryTiles.module.css";

// Страница «Каталог / Все»: бенто из тёмных плиток разной формы. Раскладка привязана к позиции в списке
// (1-я — большая, 2-я — широкая, остальные — малые), а не к slug. Название, число моделей и типы-ссылки слева, товар без фона — на краю.
const SHAPES = [styles.big, styles.wide, styles.small, styles.small];

export function CategoryTiles({ categories }: { categories: Category[] }) {
  return (
    <ul className={styles.list}>
      {categories.map((c, i) => {
        const types = c.types ?? [];
        return (
          <Reveal as="li" key={c.slug} index={i} className={cx(styles.item, SHAPES[i] ?? styles.small)}>
            <article className={styles.tile}>
              <div className={styles.body}>
                <h3 className={styles.name}>
                  {/* ссылка растянута на всю плитку; типы поверх неё */}
                  <Link href={`/catalog/${c.slug}`} className={styles.link}>
                    {c.name}
                  </Link>
                </h3>
                <p className={styles.count}>{c.seriesCount > 0 ? plural(c.seriesCount, "модель", "модели", "моделей") : "скоро в каталоге"}</p>
                {types.length > 0 && (
                  <ul className={styles.types} aria-label={`${c.name}: типы`}>
                    {types.map((t) => (
                      <li key={t.slug}>
                        <Link href={`/catalog/${c.slug}?type=${t.slug}`} className={styles.type}>
                          {t.name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <Picture image={c.image} fit="contain" sizes="(max-width: 767px) 80vw, 45vw" className={styles.img} />
              <Arrow className={styles.arrow} />
            </article>
          </Reveal>
        );
      })}
    </ul>
  );
}
