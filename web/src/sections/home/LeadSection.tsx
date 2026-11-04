import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { LeadForm } from "@/components/LeadForm/LeadForm";
import { Reveal } from "@/components/Reveal/Reveal";
import { getSite } from "@/data/api";
import styles from "./LeadSection.module.css";

type Props = {
  source?: string;
  id?: string;
  title?: string;
  text?: string;
  partner?: boolean;
};

// Главная форма заявки внизу страниц. Сюда ведут все кнопки «Заявка».
export async function LeadSection({
  source = "home",
  id = "lead",
  title = "Остались вопросы",
  text = "Оставьте телефон или пришлите план — посчитаем мощность и подберём 2–3 варианта. Бесплатно и ни к чему не обязывает.",
  partner,
}: Props) {
  const site = await getSite();
  return (
    <Section id={id} tone="dark" labelledBy={`${id}-title`}>
      <Container className={styles.layout}>
        <Reveal className={styles.side}>
          <h2 id={`${id}-title`} className={styles.title}>
            {title}
            <span className={styles.dot}>{title === "Остались вопросы" ? "?" : "."}</span>
          </h2>
          <p className={styles.text}>{text}</p>
          <p className={styles.direct}>
            Или сразу: <a href={site.phoneHref}>{site.phone}</a>
          </p>
        </Reveal>
        <Reveal className={styles.form} index={1}>
          <LeadForm source={source} partner={partner} submitLabel={partner ? "Отправить анкету" : undefined} />
        </Reveal>
      </Container>
    </Section>
  );
}
