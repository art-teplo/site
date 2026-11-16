import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Button } from "@/components/Button/Button";
import { Reveal } from "@/components/Reveal/Reveal";
import { SplitText } from "@/components/SplitText/SplitText";
import { getSite } from "@/data/api";
import { cx } from "@/lib/format";
import styles from "./Reviews.module.css";
import { ReviewsWidget } from "./ReviewsWidget";

// 10 · Отзывы. Своих отзывов не пишем (brief.md) — виджет Яндекс.Карт как есть.
// Карточка — «id организации» в настройках сайта. Пусто — без виджета, только ссылка на карту.
// Виджет грузится, только когда до него докрутили; Яндекс недоступен — заглушка (ReviewsWidget)
export async function Reviews() {
  const site = await getSite();
  const orgId = site.yandexOrgId;
  const reviewsUrl = orgId ? `https://yandex.by/maps/org/${orgId}/reviews/` : site.mapUrl;
  return (
    <Section tone="white" labelledBy="reviews-title">
      <Container className={styles.layout}>
        <div className={cx(styles.aside, !orgId && styles.asideOnly)}>
          <Reveal effect="mask">
            <h2 id="reviews-title" className={styles.title}>
              <SplitText>Что говорят на Яндекс.Картах</SplitText>
            </h2>
          </Reveal>
          <Reveal className={styles.text} index={2}>
            <p className={styles.intro}>Отзывы подтягиваются с Яндекс.Карт как есть — мы их не редактируем.</p>
            <Button href={reviewsUrl} target="_blank" rel="noopener noreferrer" variant="secondary" arrow>
              Все отзывы на Яндекс.Картах
            </Button>
          </Reveal>
        </div>
        {orgId ? (
          <Reveal className={styles.widget} index={3}>
            <ReviewsWidget orgId={orgId} reviewsUrl={reviewsUrl} />
          </Reveal>
        ) : null}
      </Container>
    </Section>
  );
}
