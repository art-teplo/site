import type { ReactNode } from "react";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Reveal } from "@/components/Reveal/Reveal";
import styles from "./InfoGrid.module.css";

type Props = {
  id: string;
  title: string;
  intro?: ReactNode;
  items: { title: string; text: string }[];
  tone?: "light" | "white" | "dark";
  children?: ReactNode; // дополнительный блок под сеткой (таблица, кнопка)
};

// Раздел внутренней страницы: заголовок и короткие пункты «заголовок + текст» на волосяных линиях.
export function InfoGrid({ id, title, intro, items, tone = "light", children }: Props) {
  return (
    <Section id={id} tone={tone} labelledBy={`${id}-title`}>
      <Container>
        <SectionHead titleId={`${id}-title`} title={title} intro={intro} />
        {items.length > 0 && (
          <ul className={styles.list}>
            {items.map((item, i) => (
              <Reveal as="li" key={item.title} index={i % 3} className={styles.item}>
                <h3 className={styles.title}>{item.title}</h3>
                <p className={styles.text}>{item.text}</p>
              </Reveal>
            ))}
          </ul>
        )}
        {children && <div className={styles.extra}>{children}</div>}
      </Container>
    </Section>
  );
}
