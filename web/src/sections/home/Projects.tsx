import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { HorizontalRail } from "@/components/HorizontalRail/HorizontalRail";
import { ProjectCard } from "@/components/ProjectCard/ProjectCard";
import { Arrow } from "@/components/Button/Button";
import { getProjects, getSeriesCategories } from "@/data/api";
import { ProjectsSlider } from "./ProjectsSlider";
import styles from "./Projects.module.css";

// Остальные — на /proekty. Какие попадут на главную, решает порядок в админке
const HOME_COUNT = 6;

const intro = (
  <>
    <span className={styles.count}>
      15&nbsp;600+ <span className={styles.countLabel}>проектов</span>
    </span>
    Не студийная съёмка: под фото — радиаторы, которые стоят в этом интерьере.
  </>
);

// Портфолио на главной. Компьютер и планшет — лента едет вбок при прокрутке; телефон — по одному проекту
// со стрелками и списком радиаторов из него. Якорь #projects — на обёртке, чтобы он был один.
export async function Projects() {
  const projects = (await getProjects()).slice(0, HOME_COUNT);
  // Нет проектов в админке — нет и блока: иначе остаётся пустая лента с одной карточкой «Все проекты»
  if (projects.length === 0) return null;
  const found = await getSeriesCategories(projects.flatMap((p) => p.series));
  const seriesLinks = Object.fromEntries(
    Object.entries(found).map(([slug, s]) => [slug, { name: s.name, href: `/catalog/${s.category}/${slug}` }]),
  );
  return (
    <div id="projects">
      <div className={styles.wide}>
        <Section labelledBy="projects-title" flush className={styles.section}>
          <Container>
            <HorizontalRail
              head={<SectionHead titleId="projects-title" title="Реальные дома после установки" intro={intro} />}
            >
              {projects.map((p) => (
                <div key={p.slug} className={styles.slide}>
                  <ProjectCard project={p} />
                </div>
              ))}
              <Link href="/proekty" className={styles.all}>
                <span className={styles.allTitle}>Все проекты</span>
                <span className={styles.allText}>Квартиры, дома и жилые комплексы — с фильтром по типу объекта</span>
                <Arrow className={styles.allArrow} />
              </Link>
            </HorizontalRail>
          </Container>
        </Section>
      </div>
      <div className={styles.phone}>
        <Section labelledBy="projects-phone-title">
          <Container>
            <SectionHead titleId="projects-phone-title" title="Реальные дома после установки" intro={intro} />
            <ProjectsSlider projects={projects} seriesLinks={seriesLinks} />
          </Container>
        </Section>
      </div>
    </div>
  );
}
