"use client";

import { Lightbox } from "@/components/Lightbox/Lightbox";
import { Picture } from "@/components/Picture/Picture";
import type { SeriesImage } from "@/data/types";
import styles from "./SchemeGallery.module.css";

type Props = { images: SeriesImage[]; title: string };

// Схемы подключений и размеров: чертёж целиком, без обрезки, на белом; по клику — на весь экран
export function SchemeGallery({ images, title }: Props) {
  return (
    <Lightbox images={images} title={title}>
      {(open) => (
        <ul className={styles.grid}>
          {images.map((im, i) => (
            <li key={im.src}>
              <button type="button" className={styles.tile} aria-haspopup="dialog" aria-label={`${title}: ${im.alt}`} onClick={() => open(i)}>
                <Picture image={im} sizes="(max-width: 767px) 100vw, 50vw" fit="contain" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Lightbox>
  );
}
