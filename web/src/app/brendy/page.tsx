import type { Metadata } from "next";
import { PageIntro } from "@/sections/page/PageIntro";
import { Brands } from "@/sections/home/Brands";
import { LeadSection } from "@/sections/home/LeadSection";

export const metadata: Metadata = {
  title: "Бренды",
  description: "КЗТО, Guardo, Радимакс, Royal Thermo, Nova, Carisa, SR Rubinetterie — бренды в шоуруме АртТепло.",
};

export default function BrendyPage() {
  return (
    <>
      <PageIntro title="Бренды" intro="Работаем с заводами, за которые можем поручиться. КЗТО — официально, как представитель в Беларуси." />
      <Brands withHead={false} />
      <LeadSection source="brendy" />
    </>
  );
}
