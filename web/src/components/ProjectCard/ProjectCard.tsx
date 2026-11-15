import { Frame } from "@/components/Frame/Frame";
import { Lightbox } from "@/components/Lightbox/Lightbox";
import { Picture } from "@/components/Picture/Picture";
import { ratioValue } from "@/lib/ratio";
import Link from "next/link";
import type { Project } from "@/data/types";
import styles from "./ProjectCard.module.css";

// Проект: вертикальный кадр интерьера (заказчица снимает под вертикальные ролики), место, название и серии из него.
type Props = {
  project: Project;
  ratio?: string;
  sizes?: string;
  stands?: { name: string; href: string }[]; // серии, которые стоят в проекте
};

export function ProjectCard({ project, ratio = "4 / 5", sizes = "(max-width: 767px) 80vw, 30vw", stands = [] }: Props) {
  const frame = (
    <Frame ratio={ratio}>
      <Picture image={project.image} sizes={sizes} fit="smart" frame={ratioValue(ratio)} />
    </Frame>
  );
  return (
    <figure className={styles.card}>
      {/* Одно фото — просто кадр; несколько или есть видео — по клику галерея на весь экран, видео в ней вторым */}
      {project.photos.length > 0 || project.videoUrl ? (
        <Lightbox images={[project.image, ...project.photos]} title={project.title} video={project.videoUrl || undefined}>
          {frame}
        </Lightbox>
      ) : (
        frame
      )}
      <figcaption className={styles.caption}>
        {project.place && <span className={styles.meta}>{project.place}</span>}
        <span className={styles.title}>{project.title}</span>
        {stands.length > 0 && (
          <span className={styles.stands}>
            <span className={styles.standsLabel}>Что стоит в проекте</span>
            <span className={styles.standsList}>
              {stands.map((s) => (
                <Link key={s.href} href={s.href} className={styles.stand}>
                  {s.name}
                </Link>
              ))}
            </span>
          </span>
        )}
      </figcaption>
    </figure>
  );
}
