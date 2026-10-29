import type { Metadata } from "next";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Reveal } from "@/components/Reveal/Reveal";
import { SplitText } from "@/components/SplitText/SplitText";
import { Button } from "@/components/Button/Button";
import { serviceDetails, services } from "@/data/content";
import { PageIntro, AnchorNav } from "@/sections/page/PageIntro";
import { LeadSection } from "@/sections/home/LeadSection";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Услуги: расчёт, замена, монтаж, покраска",
  description: "Тепловой расчёт, замена радиаторов с согласованием, монтаж и покраска в любой цвет RAL.",
};

export default function UslugiPage() {
  return (
    <>
      <PageIntro
        title="Услуги"
        intro="Берём на себя всё вокруг радиатора: расчёт, документы, монтаж и цвет. Можно заказать что-то одно или всё вместе."
      >
        <AnchorNav items={services.map((s) => ({ href: `#${s.slug}`, label: s.title }))} />
      </PageIntro>
      {services.map((s, i) => {
        const d = serviceDetails[s.slug];
        return (
          <Section key={s.slug} id={s.slug} tone={i % 2 ? "white" : "light"} labelledBy={`${s.slug}-title`}>
            <Container className={styles.service}>
              <Reveal effect="mask" className={styles.head}>
                <h2 id={`${s.slug}-title`} className={styles.title}>
                  <SplitText>{s.title}</SplitText>
                </h2>
              </Reveal>
              <Reveal className={styles.body} index={2}>
                <p className={styles.lead}>{d.lead}</p>
                <ul className={styles.points}>
                  {d.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
                <Button href="#lead" variant="secondary" arrow>
                  Заказать
                </Button>
              </Reveal>
            </Container>
          </Section>
        );
      })}
      <LeadSection source="uslugi" title="Нужна услуга" text="Опишите задачу — назовём стоимость и сроки." />
    </>
  );
}
