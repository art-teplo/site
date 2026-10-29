import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import { Arrow, Button } from "@/components/Button/Button";
import { categories, productsIn } from "@/data/catalog";
import styles from "./Categories.module.css";

// 02 · Категории крупными плитками. На мобильном — лента, уходящая за край.
export function Categories() {
  return (
    <Section id="catalog" labelledBy="categories-title">
      <Container>
        <SectionHead
          titleId="categories-title"
          title="Отопление, которое не прячут за решёткой"
          aside={
            <Button href="/catalog" variant="ghost" arrow>
              Весь каталог
            </Button>
          }
        />
      </Container>
      <Container>
        <ul className={styles.list}>
          {categories.map((c, i) => (
            <Reveal as="li" key={c.slug} index={i} className={styles.item}>
              <Link href={`/catalog/${c.slug}`} className={styles.tile}>
                <Picture image={c.image} sizes="(max-width: 767px) 75vw, (max-width: 1023px) 45vw, 25vw" className={styles.img} />
                <span className={styles.shade} aria-hidden="true" />
                <span className={styles.caption}>
                  <span className={styles.name}>{c.name}</span>
                  <span className={styles.short}>
                    {c.short} · {productsIn(c.slug).length} моделей
                  </span>
                </span>
                <Arrow className={styles.arrow} />
              </Link>
            </Reveal>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
