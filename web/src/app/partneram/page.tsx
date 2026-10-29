import type { Metadata } from "next";
import { partnerOffers } from "@/data/content";
import { PageIntro, AnchorNav } from "@/sections/page/PageIntro";
import { InfoGrid } from "@/sections/page/InfoGrid";
import { LeadSection } from "@/sections/home/LeadSection";

export const metadata: Metadata = {
  title: "Дизайнерам и строителям",
  description: "Подбор радиаторов под проект, спецификации и сроки для дизайнеров интерьера, архитекторов и строительных компаний.",
};

// ЧЕРНОВИК: условия сотрудничества (скидки, вознаграждение) — вопрос 4 к заказчику.
export default function PartneramPage() {
  return (
    <>
      <PageIntro
        title="Дизайнерам и строителям"
        intro="Подбираем радиаторы под проект, готовим спецификации и держим сроки объекта. Условия сотрудничества обсуждаем лично."
      >
        <AnchorNav
          items={[
            { href: "#dizajneram", label: "Дизайнерам и архитекторам" },
            { href: "#stroitelyam", label: "Строительным компаниям" },
            { href: "#anketa", label: "Анкета партнёра" },
          ]}
        />
      </PageIntro>
      <InfoGrid id="dizajneram" title="Дизайнерам и архитекторам" items={partnerOffers.designers} tone="white" />
      <InfoGrid id="stroitelyam" title="Строительным компаниям" items={partnerOffers.builders} />
      <LeadSection
        id="anketa"
        source="partneram"
        partner
        title="Стать партнёром"
        text="Расскажите о студии или компании — свяжемся, обсудим условия и пригласим в шоурум."
      />
    </>
  );
}
