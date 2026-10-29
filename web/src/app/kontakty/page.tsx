import type { Metadata } from "next";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Button } from "@/components/Button/Button";
import { Reveal } from "@/components/Reveal/Reveal";
import { site } from "@/data/site";
import { PageIntro } from "@/sections/page/PageIntro";
import { LeadSection } from "@/sections/home/LeadSection";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Контакты",
  description: `Шоурум АртТепло: ${site.city}, ${site.address}. Телефон ${site.phone}, Viber, Telegram.`,
};

export default function KontaktyPage() {
  return (
    <>
      <PageIntro title="Контакты" intro="Звоните, пишите в мессенджер или приезжайте — радиаторы лучше выбирать вживую." />
      <Section tone="white">
        <Container className={styles.grid}>
          <Reveal className={styles.block}>
            <h2 className={styles.label}>Телефон</h2>
            <a href={site.phoneHref} className={styles.big}>
              {site.phone}
            </a>
            <div className={styles.row}>
              <a href={site.viber}>Viber</a>
              <a href={site.telegram}>Telegram</a>
            </div>
          </Reveal>
          <Reveal className={styles.block} index={1}>
            <h2 className={styles.label}>Шоурум</h2>
            <p className={styles.big}>
              {site.city}, {site.address}
            </p>
            <Button href={site.mapUrl} target="_blank" rel="noopener noreferrer" variant="secondary" arrow>
              Открыть в Яндекс.Картах
            </Button>
          </Reveal>
          <Reveal className={styles.block} index={2}>
            <h2 className={styles.label}>Часы работы</h2>
            <ul className={styles.hours}>
              {site.hours.map((h) => (
                <li key={h.days}>
                  <span>{h.days}</span>
                  <span>{h.time}</span>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal className={styles.block} index={3}>
            <h2 className={styles.label}>Почта и соцсети</h2>
            <a href={`mailto:${site.email}`} className={styles.link}>
              {site.email}
            </a>
            <a href={site.instagram} target="_blank" rel="noopener noreferrer" className={styles.link}>
              Instagram {site.instagramHandle}
            </a>
          </Reveal>
          <p className={styles.legal}>
            {site.legalName}, УНП {site.unp}
          </p>
        </Container>
      </Section>
      <LeadSection source="kontakty" title="Напишите нам" text="Оставьте телефон — перезвоним и ответим на вопросы." />
    </>
  );
}
