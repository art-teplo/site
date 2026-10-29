import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Reveal } from "@/components/Reveal/Reveal";
import { Arrow } from "@/components/Button/Button";
import { services } from "@/data/content";
import styles from "./Services.module.css";

// Услуги: редакционный список на волосяных линиях, как таблица размеров в карточке.
export function Services() {
  return (
    <Section id="services" labelledBy="services-title">
      <Container>
        <SectionHead
          titleId="services-title"
          title={"Под ключ\u00a0— от\u00a0расчёта до\u00a0опрессовки"}
          mark="Под ключ"
          intro="Оформим все документы для замены радиаторов и сделаем так, чтобы вам не пришлось ни с кем договариваться."
        />
        <ul className={styles.list}>
          {services.map((s, i) => (
            <Reveal as="li" key={s.slug} index={i}>
              <Link href={`/uslugi#${s.slug}`} className={styles.row}>
                <span className={styles.title}>{s.title}</span>
                <span className={styles.text}>{s.text}</span>
                <Arrow className={styles.arrow} />
              </Link>
            </Reveal>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
