import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Button } from "@/components/Button/Button";
import { Reveal } from "@/components/Reveal/Reveal";
import { SplitText } from "@/components/SplitText/SplitText";
import styles from "./Reviews.module.css";

// Карточка шоурума на Яндекс.Картах. Пока это «Плаг Сити» — живая, с отзывами; заказчица её переименует.
// У карточки «ArtTeplo» (16890731657) по тому же адресу два отзыва и не подтверждён владелец (решение 120)
const YANDEX_ORG_ID = "141315425329";
const REVIEWS_URL = `https://yandex.by/maps/org/${YANDEX_ORG_ID}/reviews/`;

// 10 · Отзывы. Своих отзывов не пишем (brief.md) — виджет Яндекс.Карт как есть.
// loading="lazy": iframe грузится, только когда до него докрутили, и не тормозит первый экран (решение 16)
export function Reviews() {
  return (
    <Section tone="white" labelledBy="reviews-title">
      <Container className={styles.layout}>
        <div className={styles.aside}>
          <Reveal effect="mask">
            <h2 id="reviews-title" className={styles.title}>
              <SplitText>Что говорят на Яндекс.Картах</SplitText>
            </h2>
          </Reveal>
          <Reveal className={styles.text} index={2}>
            <p className={styles.intro}>Отзывы подтягиваются с Яндекс.Карт как есть — мы их не редактируем.</p>
            <Button href={REVIEWS_URL} target="_blank" rel="noopener noreferrer" variant="secondary" arrow>
              Все отзывы на Яндекс.Картах
            </Button>
          </Reveal>
        </div>
        <Reveal className={styles.widget} index={3}>
          <iframe
            className={styles.frame}
            src={`https://yandex.ru/maps-reviews-widget/${YANDEX_ORG_ID}?comments`}
            title="Отзывы о шоуруме на Яндекс.Картах"
            loading="lazy"
          />
        </Reveal>
      </Container>
    </Section>
  );
}
