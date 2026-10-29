import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Reveal } from "@/components/Reveal/Reveal";
import { facts } from "@/data/content";
import { currentYear } from "@/lib/year";
import styles from "./Facts.module.css";

// Почему мы: четыре коротких причины на тёмной «каминной» полосе. Текстом, без витрины цифр.
export async function Facts({ withMore = true }: { withMore?: boolean }) {
  const year = await currentYear();
  return (
    <Section tone="dark" labelledBy="facts-title">
      <Container>
        <SectionHead
          titleId="facts-title"
          title="Почему АртТепло"
          aside={
            withMore && (
              <Link href="/shourum" className={styles.more}>
                О нас и шоуруме
              </Link>
            )
          }
        />
        <ul className={styles.list}>
          {facts(year).map((f, i) => (
            <Reveal as="li" key={f.title} index={i} className={styles.item}>
              <h3 className={styles.title}>{f.title}</h3>
              <p className={styles.text}>{f.text}</p>
            </Reveal>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
