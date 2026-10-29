import type { Metadata } from "next";
import type { Product } from "@/data/types";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Accordion } from "@/components/Accordion/Accordion";
import { brands, products } from "@/data/catalog";
import { delivery, faq, LEAD_TIMES_UPDATED, payment } from "@/data/content";
import { formatDate } from "@/lib/format";
import { PageIntro, AnchorNav } from "@/sections/page/PageIntro";
import { InfoGrid } from "@/sections/page/InfoGrid";
import { DataTable } from "@/sections/page/DataTable";
import { LeadSection } from "@/sections/home/LeadSection";

export const metadata: Metadata = {
  title: "Клиентам: доставка, оплата, сроки, гарантия",
  description: "Доставка по Минску и Беларуси, оплата, сроки изготовления по сериям и гарантия производителей.",
};

// Ориентир по серии; наличие на сайте не показываем — его уточняет менеджер
const leadTime = (p: Product) => (p.leadDays ? `до ${p.leadDays} дней` : "уточнит менеджер");

export default function KlientamPage() {
  const warranty = brands
    .map((b) => {
      const own = products.filter((p) => p.brand === b.slug);
      return own.length ? [b.name, b.country === "—" ? "—" : b.country, `${Math.max(...own.map((p) => p.warrantyYears))} лет`] : null;
    })
    .filter((row): row is string[] => row !== null);

  return (
    <>
      <PageIntro title="Клиентам" intro="Как привезём, как оплатить, сколько ждать и что с гарантией. Если ответа нет — спросите менеджера.">
        <AnchorNav
          items={[
            { href: "#dostavka", label: "Доставка и оплата" },
            { href: "#sroki", label: "Сроки изготовления" },
            { href: "#garantiya", label: "Гарантия" },
            { href: "#faq", label: "Вопрос-ответ" },
          ]}
        />
      </PageIntro>

      <InfoGrid id="dostavka" title="Доставка и оплата" items={[...delivery, ...payment]} tone="white" />

      <Section id="sroki" labelledBy="sroki-title">
        <Container>
          <SectionHead
            titleId="sroki-title"
            title="Сроки изготовления"
            intro="Ориентировочный срок изготовления под заказ. Наличие и точный срок для вашего размера и цвета уточнит менеджер."
          />
          <DataTable
            head={["Модель", "Срок изготовления"]}
            rows={products.map((p) => [p.name, leadTime(p)])}
            note={`Обновлено ${formatDate(LEAD_TIMES_UPDATED)}. Демо-данные — заменятся таблицей из админки.`}
          />
        </Container>
      </Section>

      <Section id="garantiya" tone="white" labelledBy="garantiya-title">
        <Container>
          <SectionHead titleId="garantiya-title" title="Гарантия" intro="Гарантию даёт производитель. Срок зависит от бренда и серии — точный указан в паспорте изделия." />
          <DataTable head={["Бренд", "Страна", "Гарантия до"]} rows={warranty} />
        </Container>
      </Section>

      <Section id="faq" labelledBy="faq-page-title">
        <Container>
          <SectionHead titleId="faq-page-title" title="Вопрос-ответ" />
          <Accordion items={faq} />
        </Container>
      </Section>

      <LeadSection source="klientam" title="Не нашли ответ" text="Задайте вопрос — ответим в мессенджере или перезвоним." />
    </>
  );
}
