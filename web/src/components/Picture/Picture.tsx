import { getImageProps } from "next/image";
import type { ImageAsset } from "@/data/types";
import { versioned } from "@/lib/asset";
import { cx } from "@/lib/format";
import styles from "./Picture.module.css";

type Props = {
  image: ImageAsset;
  mobile?: ImageAsset; // другой кроп для узких экранов (art direction)
  sizes: string;
  eager?: boolean; // только для первого экрана
  className?: string;
  fit?: "cover" | "contain";
};

// <picture> с оптимизацией Next (AVIF/WebP, srcset), width/height и lazy loading по умолчанию.
export function Picture({ image, mobile, sizes, eager, className, fit = "cover" }: Props) {
  const common = { alt: image.alt, sizes, quality: 75 };
  const loading = eager ? { loading: "eager" as const, fetchPriority: "high" as const } : { loading: "lazy" as const };

  const { props } = getImageProps({ ...common, ...loading, src: versioned(image.src), width: image.width, height: image.height });
  const mobileSrcSet = mobile
    ? getImageProps({ ...common, src: versioned(mobile.src), width: mobile.width, height: mobile.height }).props.srcSet
    : undefined;

  // Фото заполняет рамку и обрезается — точка фокуса держит главное в кадре (у кропа для телефона — своя)
  const focus = fit === "cover" && !mobile && image.focus ? { objectPosition: `${image.focus.x}% ${image.focus.y}%` } : undefined;

  return (
    <picture className={cx(styles.picture, fit === "contain" && styles.bare, className)}>
      {mobileSrcSet && <source media="(max-width: 767px)" srcSet={mobileSrcSet} sizes={sizes} />}
      <img {...props} alt={image.alt} className={cx(styles.img, fit === "contain" && styles.contain)} style={focus ? { ...props.style, ...focus } : props.style} />
    </picture>
  );
}
