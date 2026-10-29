import Link from "next/link";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import { getProduct } from "@/data/catalog";
import type { Project } from "@/data/types";
import styles from "./ProjectCard.module.css";

const KIND: Record<Project["kind"], string> = { квартира: "Квартира", дом: "Дом", ЖК: "Жилой комплекс" };

// Проект: кадр интерьера в уголках видоискателя, подпись и радиаторы, которые в нём стоят.
export function ProjectCard({ project, ratio = "4 / 5", sizes = "(max-width: 767px) 80vw, 30vw" }: { project: Project; ratio?: string; sizes?: string }) {
  return (
    <figure className={styles.card}>
      <Frame ratio={ratio} corners>
        <Picture image={project.image} sizes={sizes} />
      </Frame>
      <figcaption className={styles.caption}>
        <span className={styles.meta}>
          {KIND[project.kind]} · {project.place}
        </span>
        <span className={styles.title}>{project.title}</span>
        {project.products.length > 0 && (
          <span className={styles.products}>
            {project.products.map((slug) => {
              const product = getProduct(slug);
              return product ? (
                <Link key={slug} href={`/catalog/${product.category}/${slug}`} className={styles.chip}>
                  {product.name}
                </Link>
              ) : null;
            })}
          </span>
        )}
      </figcaption>
    </figure>
  );
}
