"use client";

import { Lightbox } from "@/components/Lightbox/Lightbox";
import { Picture } from "@/components/Picture/Picture";
import type { SeriesImage } from "@/data/types";
import { cx } from "@/lib/format";
import styles from "./InteriorGallery.module.css";

const MAX_TILES = 5; // на раскладке «большое + сетка» видно не больше пяти плиток

// Фото в интерьере на всю ширину: раскладка зависит от числа фото, «+N» — только на последней плитке и только если есть скрытые.
export function InteriorGallery({ images, title }: { images: SeriesImage[]; title: string }) {
  const shown = images.slice(0, MAX_TILES);
  const hidden = images.length - shown.length;
  const layout = Math.min(images.length, 4); // 4 — «4 и больше»; из 4 фото плиток 4, из 5 и больше — 5

  return (
    <Lightbox images={images} title={title}>
      {(open) => (
        <div className={styles.mosaic} data-layout={layout} data-tiles={shown.length}>
          {shown.map((im, i) => (
            <button
              key={im.src}
              type="button"
              className={cx(styles.tile, i === 0 && styles.main)}
              aria-haspopup="dialog"
              aria-label={`${title}: фото ${i + 1} из ${images.length}`}
              onClick={() => open(i)}
            >
              <Picture image={im} sizes={i === 0 ? "(max-width: 767px) 100vw, 50vw" : "(max-width: 767px) 50vw, 25vw"} />
              {hidden > 0 && i === shown.length - 1 && (
                <span className={styles.more} aria-hidden="true">
                  +{hidden}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </Lightbox>
  );
}
