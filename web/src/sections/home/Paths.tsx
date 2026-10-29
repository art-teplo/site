import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Reveal } from "@/components/Reveal/Reveal";
import { Arrow } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { LeadDialog } from "@/components/LeadDialog/LeadDialog";
import { paths } from "@/data/content";
import styles from "./Paths.module.css";

// Три пути к заявке. Карточка открывает форму поверх страницы — без прыжка вниз к #lead.
export function Paths() {
  return (
    <Section id="paths" tone="white" labelledBy="paths-title">
      <Container>
        <SectionHead
          titleId="paths-title"
          title="С чего начнём?"
          intro="Неважно, где вы сейчас: голые стены или готовая спецификация. Выберите свой случай — дальше ведём мы."
        />
        <ol className={styles.list}>
          {paths.map((p, i) => (
            <Reveal as="li" key={p.id} id={p.id} index={i} className={styles.item}>
              <LeadDialog
                className={styles.card}
                title={`${p.title}\u00a0— ${p.action.toLowerCase()}`}
                text={p.ask}
                source="home:paths"
                context={p.title}
              >
                <span className={styles.icon}>
                  <Icon name={p.icon} />
                </span>
                <span className={styles.title}>{p.title}</span>
                <span className={styles.text}>{p.text}</span>
                <span className={styles.action}>
                  {p.action}
                  <Arrow className={styles.arrow} />
                </span>
              </LeadDialog>
            </Reveal>
          ))}
        </ol>
      </Container>
    </Section>
  );
}
