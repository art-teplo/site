import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Button } from "@/components/Button/Button";
import { Reveal } from "@/components/Reveal/Reveal";
import { site } from "@/data/site";
import styles from "./Reviews.module.css";

// 10 · Отзывы. Своих отзывов не пишем (brief.md) — здесь будет виджет Яндекс.Карт.
// TODO: вставить iframe виджета (yandex.ru/sprav/widget/...) с id организации, загрузка по клику.
export function Reviews() {
  return (
    <Section tone="white" labelledBy="reviews-title">
      <Container>
        <SectionHead
          titleId="reviews-title"
          title="Что говорят на Яндекс.Картах"
          intro="Отзывы подтягиваются с Яндекс.Карт как есть — мы их не редактируем."
        />
        <Reveal className={styles.slot}>
          <div className={styles.slotInner}>
            <p className={styles.slotTitle}>Виджет отзывов Яндекс.Карт</p>
            <p className={styles.slotText}>Место под рейтинг и последние отзывы. Подключим, когда будет id организации.</p>
          </div>
          <Button href={site.mapUrl} target="_blank" rel="noopener noreferrer" variant="secondary" arrow>
            Читать на Яндекс.Картах
          </Button>
        </Reveal>
      </Container>
    </Section>
  );
}
