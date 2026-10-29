import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Reveal } from "@/components/Reveal/Reveal";
import { brands, products } from "@/data/catalog";
import styles from "./Brands.module.css";

// Бренды: логотип сверху, под ним страна и что берём у завода (как у российских конкурентов).
// Логотипы приглушены в монохроме и проявляются в цвете при наведении. Нет логотипа — название набором.
export function Brands({ withHead = true }: { withHead?: boolean }) {
  return (
    <Section tone="white" labelledBy={withHead ? "brands-title" : undefined}>
      <Container>
        {withHead && <SectionHead titleId="brands-title" title="Заводы, за которые ручаемся" />}
        <ul className={styles.grid}>
          {brands.map((b, i) => {
            const count = products.filter((p) => p.brand === b.slug).length;
            return (
              <Reveal as="li" key={b.slug} index={i % 4}>
                <Link href={`/catalog?brand=${b.slug}`} className={styles.brand}>
                  <span className={styles.logoBox}>
                    {b.logo ? (
                      // eslint-disable-next-line @next/next/no-img-element -- SVG/PNG логотипы без оптимизации
                      <img src={b.logo.src} width={b.logo.width} height={b.logo.height} alt={b.name} loading="lazy" className={styles.logo} />
                    ) : (
                      <span className={styles.wordmark}>{b.name}</span>
                    )}
                  </span>
                  <span className={styles.meta}>
                    <span className={styles.name}>
                      {b.name}
                      {b.country !== "—" && <span className={styles.country}> · {b.country}</span>}
                    </span>
                    <span>{b.note}</span>
                    {count > 0 && <span className={styles.count}>{count} в каталоге</span>}
                  </span>
                </Link>
              </Reveal>
            );
          })}
        </ul>
      </Container>
    </Section>
  );
}
