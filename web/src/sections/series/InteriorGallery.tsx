"use client";

import { Lightbox } from "@/components/Lightbox/Lightbox";
import { Picture, cropShare } from "@/components/Picture/Picture";
import type { SeriesImage } from "@/data/types";
import { cx } from "@/lib/format";
import styles from "./InteriorGallery.module.css";

const MAX_TILES = 5; // на раскладке «большое + сетка» видно не больше пяти плиток

// Форма плиток по раскладке (= aspect-ratio мозаики в CSS): у фото почти всегда 4:3…16:9 — рамка под них,
// чтобы фото заполняли плитку с небольшой обрезкой, а не лежали на размытом фоне
const TILE: Record<number, number> = { 1: 16 / 9, 2: 4 / 3, 3: 4 / 3, 4: 16 / 9, 5: 4 / 3 };

// Фото в интерьере на всю ширину: раскладка зависит от числа фото, «+N» — только на последней плитке и только если есть скрытые.
// В большую плитку — фото, которое ложится в её рамку лучше остальных.
export function InteriorGallery({ images, title }: { images: SeriesImage[]; title: string }) {
  const layout = Math.min(images.length, MAX_TILES);
  const frame = TILE[layout] ?? 4 / 3;
  const best = images.reduce((b, im, i) => (cropShare(im, frame) < cropShare(images[b], frame) ? i : b), 0);
  const ordered = best ? [images[best], ...images.filter((_, i) => i !== best)] : images;
  const shown = ordered.slice(0, MAX_TILES);
  const hidden = ordered.length - shown.length;

  return (
    <Lightbox images={ordered} title={title}>
      {(open) => (
        <div className={styles.mosaic} data-layout={layout}>
          {shown.map((im, i) => (
            <button
              key={im.src}
              type="button"
              className={cx(styles.tile, i === 0 && styles.main)}
              aria-haspopup="dialog"
              aria-label={`${title}: фото ${i + 1} из ${ordered.length}`}
              onClick={() => open(i)}
            >
              <Picture image={im} sizes={i === 0 ? "(max-width: 767px) 100vw, 50vw" : "(max-width: 767px) 50vw, 25vw"} fit="smart" frame={frame} />
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
