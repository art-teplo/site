import type { Metadata } from "next";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { getProjects, getSeriesCategories } from "@/data/api";
import { PageIntro } from "@/sections/page/PageIntro";
import { ProjectsBrowser } from "@/sections/page/ProjectsBrowser";
import { LeadSection } from "@/sections/home/LeadSection";

export const metadata: Metadata = {
  title: "Проекты",
  description: "Квартиры, дома, клиники и отели с нашими радиаторами — реальные фото и видео после установки.",
};

export default async function ProektyPage() {
  const projects = await getProjects();
  // Ссылки «Что стоит в проекте»: адрес серии — /catalog/<категория>/<серия>, категорию берём из самой серии
  const found = await getSeriesCategories(projects.flatMap((p) => p.series));
  const seriesLinks = Object.fromEntries(
    Object.entries(found).map(([slug, s]) => [slug, { name: s.name, href: `/catalog/${s.category}/${slug}` }]),
  );
  return (
    <>
      <PageIntro
        title="Проекты"
        intro="Больше 15 600 проектов. Здесь — реальные интерьеры после установки, а не студийная съёмка. Под каждым фото — радиаторы, которые там стоят."
      />
      <Section>
        <Container>
          <ProjectsBrowser projects={projects} seriesLinks={seriesLinks} />
        </Container>
      </Section>
      <LeadSection source="proekty" title="Хотите так же" text="Пришлите план или фото комнаты — подберём радиаторы под ваш интерьер." />
    </>
  );
}
