import type { Metadata } from "next";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { site } from "@/data/site";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Политика обработки персональных данных" };

// ЧЕРНОВИК структуры. Текст политики не юридически проверен (docs/brief.md, «Юридическое»).
export default function PrivacyPage() {
  return (
    <Section className={styles.page} labelledBy="privacy-title">
      <Container className={styles.layout}>
        <h1 id="privacy-title" className={styles.title}>
          Политика обработки персональных данных
        </h1>
        <div className={styles.body}>
          <p className={styles.draft}>Черновик. Текст будет подготовлен по Закону Республики Беларусь № 99-З «О защите персональных данных» и проверен юристом.</p>
          <h2>Оператор</h2>
          <p>
            {site.legalName}, УНП {site.unp}. Адрес: {site.city}, {site.address}. Почта для обращений: {site.email}.
          </p>
          <h2>Какие данные собираем</h2>
          <p>Имя, телефон, способ связи, комментарий и файлы, которые вы прикладываете к заявке (план, проект, спецификация).</p>
          <h2>Зачем</h2>
          <p>Чтобы связаться с вами, рассчитать стоимость и подобрать оборудование по вашей заявке.</p>
          <h2>Где хранятся и сколько</h2>
          <p>
            Заявка и файл хранятся на сервере сайта 12 месяцев с даты отправки, затем удаляются автоматически. Чтобы менеджер
            быстро перезвонил, заявка уходит в закрытую рабочую группу в Telegram. Серверы Telegram находятся за пределами
            Беларуси — это трансграничная передача данных, на которую вы соглашаетесь отметкой под формой.
          </p>
          <p className={styles.draft}>[Уточнить у заказчика: где размещён сервер сайта]</p>
          <h2>Ваши права</h2>
          <p>Вы можете отозвать согласие, запросить сведения о своих данных или их удаление, написав на {site.email}.</p>
        </div>
      </Container>
    </Section>
  );
}
