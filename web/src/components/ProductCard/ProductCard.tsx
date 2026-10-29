import Link from "next/link";
import { Picture } from "@/components/Picture/Picture";
import { Arrow } from "@/components/Button/Button";
import { getBrand, priceFrom } from "@/data/catalog";
import type { Product } from "@/data/types";
import { formatPrice } from "@/lib/format";
import styles from "./ProductCard.module.css";

// Карточка товара в списке: фото 4:5, бренд, название, цена «от». Вся карточка — одна ссылка.
// Наличие и срок не показываем — их уточняет менеджер (правки заказчика).
export function ProductCard({ product, sizes = "(max-width: 767px) 50vw, 25vw", priority }: { product: Product; sizes?: string; priority?: boolean }) {
  const brand = getBrand(product.brand);
  return (
    <article className={styles.card}>
      <div className={styles.media}>
        <Picture image={product.images[0]} sizes={sizes} eager={priority} />
        <Picture image={product.images[1]} sizes={sizes} className={styles.hoverImage} />
      </div>
      <div className={styles.body}>
        <p className={styles.brand}>{brand?.name}</p>
        <h3 className={styles.name}>
          <Link href={`/catalog/${product.category}/${product.slug}`} className={styles.link}>
            {product.name}
          </Link>
        </h3>
        <p className={styles.meta}>
          {product.type}
          {product.position ? `, ${product.position}` : ""}
        </p>
        <p className={styles.price}>
          <span className={styles.from}>от</span> {formatPrice(priceFrom(product))}
          <Arrow className={styles.arrow} />
        </p>
      </div>
    </article>
  );
}
