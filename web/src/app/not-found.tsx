import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Button } from "@/components/Button/Button";
import styles from "./not-found.module.css";

// 404 и разделы, которые ещё не сделаны (Услуги, Проекты, Блог как отдельные страницы).
export default function NotFound() {
  return (
    <Section tone="dark" className={styles.page}>
      <Container className={styles.inner}>
        <p className={styles.code}>404</p>
        <h1 className={styles.title}>Здесь пока холодно</h1>
        <p className={styles.text}>Страница не найдена или ещё в работе. Начните с каталога или оставьте заявку.</p>
        <div className={styles.actions}>
          <Button href="/catalog" arrow>
            Каталог
          </Button>
          <Button href="/#lead" variant="secondary">
            Заявка
          </Button>
        </div>
      </Container>
    </Section>
  );
}
