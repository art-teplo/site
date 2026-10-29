import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Reveal } from "@/components/Reveal/Reveal";
import { steps } from "@/data/content";
import styles from "./Steps.module.css";

// Как проходит подбор. Номера здесь по делу — это последовательность шагов.
export function Steps() {
  return (
    <Section labelledBy="steps-title">
      <Container>
        <SectionHead titleId="steps-title" title="Как проходит подбор" intro="От первого звонка до тёплой комнаты. Шоурум — по желанию, всё можно решить удалённо." />
        <ol className={styles.list}>
          {steps.map((s, i) => (
            <Reveal as="li" key={s.title} index={i} className={styles.item}>
              <span className={styles.num}>{i + 1}</span>
              <h3 className={styles.title}>{s.title}</h3>
              <p className={styles.text}>{s.text}</p>
            </Reveal>
          ))}
        </ol>
      </Container>
    </Section>
  );
}
