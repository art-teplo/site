import { ProjectCard } from "@/components/ProjectCard/ProjectCard";
import { Reveal } from "@/components/Reveal/Reveal";
import type { Project } from "@/data/types";
import styles from "./ProjectsBrowser.module.css";

// Все проекты сеткой. Без фильтра по типу объекта: среди проектов клиники и отели, деление «квартира / дом / ЖК» не работает.
export function ProjectsBrowser({ projects, seriesLinks = {} }: { projects: Project[]; seriesLinks?: Record<string, { name: string; href: string }> }) {
  // В админке может не быть ни одного проекта — тогда без пустой сетки, как в блоге
  if (projects.length === 0) return <p className={styles.note}>Проектов пока нет.</p>;

  return (
    <ul className={styles.grid}>
      {projects.map((p, i) => (
        <Reveal as="li" key={p.slug} index={i}>
          <ProjectCard
            project={p}
            sizes="(max-width: 767px) 100vw, (max-width: 1023px) 50vw, 33vw"
            stands={p.series.flatMap((slug) => (seriesLinks[slug] ? [seriesLinks[slug]] : []))}
          />
        </Reveal>
      ))}
    </ul>
  );
}
