import type { Metadata } from "next";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { getProjects } from "@/data/api";
import { PageIntro } from "@/sections/page/PageIntro";
import { ProjectsBrowser } from "@/sections/page/ProjectsBrowser";
import { LeadSection } from "@/sections/home/LeadSection";

export const metadata: Metadata = {
  title: "Проекты",
  description: "Квартиры, дома и жилые комплексы с нашими радиаторами — реальные фото после установки.",
};

export default async function ProektyPage() {
  const projects = await getProjects();
  return (
    <>
      <PageIntro
        title="Проекты"
        intro="Больше 15 600 проектов. Здесь — реальные интерьеры после установки, а не студийная съёмка. Под каждым фото — радиаторы, которые там стоят."
      />
      <Section>
        <Container>
          <ProjectsBrowser projects={projects} />
        </Container>
      </Section>
      <LeadSection source="proekty" title="Хотите так же" text="Пришлите план или фото комнаты — подберём радиаторы под ваш интерьер." />
    </>
  );
}
