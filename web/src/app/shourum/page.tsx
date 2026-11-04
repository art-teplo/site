import type { Metadata } from "next";
import { getShowroom } from "@/data/api";
import { PageIntro, AnchorNav } from "@/sections/page/PageIntro";
import { Gallery } from "@/sections/page/Gallery";
import { Showroom } from "@/sections/home/Showroom";
import { Facts } from "@/sections/home/Facts";
import { Reviews } from "@/sections/home/Reviews";
import { Brands } from "@/sections/home/Brands";
import { LeadSection } from "@/sections/home/LeadSection";

export const metadata: Metadata = {
  title: "О нас и шоурум",
  description: "Шоурум радиаторов на Леонида Беды, 39 в Минске. Работаем с 2000 года, официальный представитель КЗТО в Беларуси.",
};

// Шоурум: где и когда, как выглядит зал, затем о компании и брендах.
export default async function ShourumPage() {
  const showroomHall = await getShowroom();
  return (
    <>
      <PageIntro
        title="О нас и шоурум"
        intro="С 2000 года подбираем отопление в Минске. Официальный представитель КЗТО в Беларуси. Продаём радиаторы, которые сами поставили бы себе домой."
      >
        <AnchorNav
          items={[
            { href: "#showroom", label: "Адрес и часы" },
            { href: "#zal", label: "Зал" },
            { href: "#lead", label: "Договориться о визите" },
          ]}
        />
      </PageIntro>
      <Showroom />
      <Gallery
        id="zal"
        title="Как выглядит зал"
        images={showroomHall}
      />
      <Facts withMore={false} />
      <Brands />
      <Reviews />
      <LeadSection source="shourum" title="Договориться о визите" text="Оставьте телефон — подберём время и подготовим нужные модели к вашему приезду." />
    </>
  );
}
