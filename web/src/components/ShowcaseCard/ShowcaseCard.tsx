"use client";

import { useState } from "react";
import { colorPreview } from "@/lib/color-preview";
import { showcaseQuery } from "@/lib/series-selection";
import Link from "next/link";
import { Arrow } from "@/components/Button/Button";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import type { ShowcaseCard as Card } from "@/data/types";
import { cx, formatPrice } from "@/lib/format";
import styles from "./ShowcaseCard.module.css";

const MAX_DOTS = 5;
const RATIO = "4 / 3"; // под форму фото: у большинства 4:3…16:9, обрезка небольшая

// Карточка формфактора серии: фото, «Гармония А40 · 1800 мм, вертикальный», бренд, «от N BYN», цвета.
// Вся карточка — одна ссылка на серию. Передаёт уже заданные фильтры каталога.
type Props = { card: Card; category: string; brand?: string; sizes?: string; priority?: boolean; query?: string; article?: string };

export function ShowcaseCard({ card, category, brand, sizes = "(max-width: 767px) 50vw, (max-width: 1023px) 33vw, 25vw", priority, query, article }: Props) {
  const params = showcaseQuery(query ?? "", article);
  const href = `/catalog/${category}/${card.series}${params.size ? `?${params}` : ""}`;
  const { visible: colors, extra } = colorPreview(card.colors, MAX_DOTS);
  const photo = { fit: "smart" as const, frame: 4 / 3 };
  const hoverImage = card.image ? card.hoverImage : null;
  const [requestedPhoto, setRequestedPhoto] = useState<string | null>(null);
  const [loadedPhoto, setLoadedPhoto] = useState<string | null>(null);
  return (
    <article className={styles.card} onPointerEnter={hoverImage ? (event) => {
      if (event.pointerType !== "touch" && window.matchMedia("(hover: hover)").matches) setRequestedPhoto(hoverImage.src);
    } : undefined}>
      <div className={cx(styles.media, hoverImage && styles.swap)}>
        {card.image ? (
          <>
            <Picture image={card.image} sizes={sizes} eager={priority} {...photo} />
            {hoverImage && requestedPhoto === hoverImage.src && (
              <Picture
                image={{ ...hoverImage, alt: "" }}
                sizes={sizes}
                {...photo}
                className={cx(styles.hoverImage, loadedPhoto === hoverImage.src && styles.hoverReady)}
                onLoad={() => setLoadedPhoto(hoverImage.src)}
              />
            )}
          </>
        ) : (
          <Frame ratio={RATIO} rounded={false}>
            <span className={styles.placeholder}>{card.name}</span>
          </Frame>
        )}
      </div>
      <div className={styles.body}>
        <p className={styles.brand}>{brand ?? card.brand}</p>
        <h3 className={styles.name}>
          <Link href={href} className={styles.link}>
            {card.name}
          </Link>
        </h3>
        {card.label && <p className={styles.meta}>{card.label}</p>}
        {card.colors.length > 0 && (
          <p className={styles.colors} aria-label={`Цветов: ${card.colors.length}`}>
            {colors.map((c) => (
              <span key={c.code} className={styles.dot} style={{ background: c.hex }} title={c.name} />
            ))}
            {extra > 0 && <span className={styles.more}>+{extra}</span>}
          </p>
        )}
        <p className={styles.price}>
          {card.priceFrom != null ? (
            <>
              <span className={styles.from}>от</span> {formatPrice(card.priceFrom)}
            </>
          ) : (
            <span className={styles.from}>Цена по запросу</span>
          )}
          <Arrow className={styles.arrow} />
        </p>
      </div>
    </article>
  );
}
