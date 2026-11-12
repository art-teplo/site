import Link from "next/link";
import { Arrow } from "@/components/Button/Button";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import type { ShowcaseCard as Card } from "@/data/types";
import { cx, formatPrice } from "@/lib/format";
import styles from "./ShowcaseCard.module.css";

const MAX_DOTS = 5;

// Карточка формфактора серии: фото, «Гармония А40 · 1800 мм, вертикальный», бренд, «от N BYN», цвета.
// Вся карточка — одна ссылка на серию с выбранной высотой.
type Props = { card: Card; category: string; brand?: string; sizes?: string; priority?: boolean };

export function ShowcaseCard({ card, category, brand, sizes = "(max-width: 767px) 50vw, (max-width: 1023px) 33vw, 25vw", priority }: Props) {
  const href = `/catalog/${category}/${card.series}${card.heightMm ? `?h=${card.heightMm}` : ""}`;
  const extra = card.colors.length - MAX_DOTS;
  return (
    <article className={styles.card}>
      <div className={cx(styles.media, card.image && card.hoverImage && styles.swap)}>
        {card.image ? (
          <>
            <Picture image={card.image} sizes={sizes} eager={priority} />
            {/* второе фото проявляется поверх первого при наведении */}
            {card.hoverImage && <Picture image={card.hoverImage} sizes={sizes} className={styles.hoverImage} />}
          </>
        ) : (
          <Frame ratio="4 / 5" rounded={false}>
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
            {card.colors.slice(0, MAX_DOTS).map((c) => (
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
