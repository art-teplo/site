import type { CSSProperties, ReactNode } from "react";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import type { ImageAsset } from "@/data/types";
import { cx } from "@/lib/format";
import styles from "./Gallery.module.css";

type Props = {
  id: string;
  title: string;
  intro?: ReactNode;
  images: ImageAsset[]; // первая — крупным кадром
  tone?: "light" | "white" | "dark";
};

// Галерея внутренней страницы. Горизонтальные фото: первый кадр крупно, остальные плиткой рядом и ниже.
// Вертикальные (больше половины — зал снимают под вертикальный контент): колонки кадров 3:4 со сдвигом — средняя ниже,
// при прокрутке плывёт быстрее крайних (CSS scroll-driven, без JS). Фото тут не рассматривают — важна атмосфера зала.
export function Gallery({ id, title, intro, images, tone = "light" }: Props) {
  const tall =
    images.filter((im) => im.height > im.width).length * 2 > images.length;
  return (
    <Section id={id} tone={tone} labelledBy={`${id}-title`}>
      <Container>
        <SectionHead titleId={`${id}-title`} title={title} intro={intro} />
        {tall ? (
          <ul
            className={cx(
              styles.tallGrid,
              images.length >= 3 && styles.stagger,
            )}
            style={{ "--cols": Math.min(images.length, 3) } as CSSProperties}
          >
            {images.map((image, i) => (
              <Reveal
                as="li"
                key={image.src}
                index={i}
                className={styles.tallTile}
              >
                <Picture
                  image={image}
                  sizes="(max-width: 767px) 50vw, 33vw"
                  fit="smart"
                  frame={3 / 4}
                />
              </Reveal>
            ))}
          </ul>
        ) : (
          <ul className={styles.grid}>
            {images.map((image, i) => (
              <Reveal as="li" key={image.src} index={i} className={styles.tile}>
                <Picture
                  image={image}
                  sizes={
                    i === 0
                      ? "(max-width: 767px) 100vw, 66vw"
                      : "(max-width: 767px) 50vw, 33vw"
                  }
                  fit="smart"
                  frame={4 / 3}
                />
              </Reveal>
            ))}
          </ul>
        )}
      </Container>
    </Section>
  );
}
