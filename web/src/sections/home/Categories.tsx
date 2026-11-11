import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import { Arrow, Button } from "@/components/Button/Button";
import { getCategories } from "@/data/api";
import { plural } from "@/lib/format";
import styles from "./Categories.module.css";

// 02 · Категории — тёмные плитки цвета наших тёмных блоков, товар без фона в углу. На телефоне — 2×2.
export async function Categories() {
  const categories = await getCategories();
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
                <Picture image={c.image} fit="contain" sizes="(max-width: 767px) 40vw, 20vw" className={styles.img} />
                <span className={styles.caption}>
                  <span className={styles.name}>{c.name}</span>
                  <span className={styles.short}>
                    <span className={styles.desc}>{c.short} · </span>
                    {plural(c.seriesCount, "модель", "модели", "моделей")}
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
