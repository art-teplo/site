import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Accordion } from "@/components/Accordion/Accordion";
import { Reveal } from "@/components/Reveal/Reveal";
import { Button } from "@/components/Button/Button";
import { getFaq } from "@/data/api";
import styles from "./FaqSection.module.css";

// Вопрос-ответ на главной: четыре самых частых вопроса, остальные — на странице «Клиентам».

export async function FaqSection() {
  const faq = (await getFaq()).filter((item) => item.onHome);
  return (
    <Section id="faq" labelledBy="faq-title">
      <Container className={styles.layout}>
        <Reveal className={styles.side}>
          <h2 id="faq-title" className={styles.title}>
            Вопрос-ответ
          </h2>
          <p className={styles.text}>Не нашли ответ? Спросите — ответим в мессенджере или перезвоним.</p>
          <Button href="/#lead" variant="secondary" arrow>
            Задать вопрос
          </Button>
        </Reveal>
        <Reveal className={styles.main} index={1}>
          <Accordion items={faq} />
          <Link href="/klientam#faq" className={styles.more}>
            Все вопросы и ответы
          </Link>
        </Reveal>
      </Container>
    </Section>
  );
}
