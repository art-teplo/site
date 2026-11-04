import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { HorizontalRail } from "@/components/HorizontalRail/HorizontalRail";
import { ProjectCard } from "@/components/ProjectCard/ProjectCard";
import { Arrow } from "@/components/Button/Button";
import { getProjects } from "@/data/api";
import styles from "./Projects.module.css";

// Остальные — на /proekty. Какие попадут на главную, решает порядок в админке
const HOME_COUNT = 6;

// Портфолио на главной: лента проектов едет вбок при прокрутке. Под каждым кадром — радиаторы из него.
export async function Projects() {
  const projects = (await getProjects()).slice(0, HOME_COUNT);
  return (
    <Section id="projects" labelledBy="projects-title" flush className={styles.section}>
      <Container>
        <HorizontalRail
          head={
            <SectionHead
              titleId="projects-title"
              title="Реальные дома после установки"
              intro={
                <>
                  <span className={styles.count}>
                    15&nbsp;600+ <span className={styles.countLabel}>проектов</span>
                  </span>
                  Не студийная съёмка: под фото — радиаторы, которые стоят в этом интерьере.
                </>
              }
            />
          }
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
  );
}
