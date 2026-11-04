import type { Metadata } from "next";
import { getBrands } from "@/data/api";
import { PageIntro } from "@/sections/page/PageIntro";
import { Brands } from "@/sections/home/Brands";
import { LeadSection } from "@/sections/home/LeadSection";

export async function generateMetadata(): Promise<Metadata> {
  const names = (await getBrands()).map((b) => b.name).join(", ");
  return { title: "Бренды", description: `${names} — бренды в шоуруме АртТепло.` };
}

export default function BrendyPage() {
  return (
    <>
      <PageIntro title="Бренды" intro="Работаем с заводами, за которые можем поручиться. КЗТО — официально, как представитель в Беларуси." />
      <Brands withHead={false} />
      <LeadSection source="brendy" />
    </>
  );
}
