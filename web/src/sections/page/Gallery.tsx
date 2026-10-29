import type { ReactNode } from "react";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import type { ImageAsset } from "@/data/types";
import styles from "./Gallery.module.css";

type Props = {
  id: string;
  title: string;
  intro?: ReactNode;
  images: ImageAsset[]; // первая — крупным кадром
  tone?: "light" | "white" | "dark";
};

// Галерея внутренней страницы: первый кадр крупно, остальные плиткой рядом и ниже.
export function Gallery({ id, title, intro, images, tone = "light" }: Props) {
  return (
    <Section id={id} tone={tone} labelledBy={`${id}-title`}>
      <Container>
        <SectionHead titleId={`${id}-title`} title={title} intro={intro} />
        <ul className={styles.grid}>
          {images.map((image, i) => (
            <Reveal as="li" key={image.src} index={i} className={styles.tile}>
              <Picture image={image} sizes={i === 0 ? "(max-width: 767px) 100vw, 58vw" : "(max-width: 767px) 50vw, 30vw"} />
            </Reveal>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
