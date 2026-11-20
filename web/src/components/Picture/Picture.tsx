import type { CSSProperties, ReactEventHandler } from "react";
import { getImageProps } from "next/image";
import type { ImageAsset } from "@/data/types";
import { versioned } from "@/lib/asset";
import { cx } from "@/lib/format";
import styles from "./Picture.module.css";

// Сколько кадра можно срезать, чтобы фото заполнило рамку (по центру — радиатор остаётся в кадре).
// Больше — фото целиком на размытом фоне: заказчица предпочитает чуть приближенное фото размытым полям
export const MAX_CROP = 0.3;
const AMBIENT_WIDTH = 64; // размытой подложке хватает крошечной копии

type Props = {
  image: ImageAsset;
  mobile?: ImageAsset; // другой кроп для узких экранов (art direction)
  sizes: string;
  eager?: boolean; // только для первого экрана
  className?: string;
  onLoad?: ReactEventHandler<HTMLImageElement>;
  // cover — заполняет рамку с обрезкой (оформление сайта, кадр известен заранее);
  // contain — товар без фона (PNG), без подложки;
  // smart — фото из админки: обрезка не больше MAX_CROP, иначе целиком, а поля — то же фото, размытое
  fit?: "cover" | "contain" | "smart";
  frame?: number; // для smart: пропорция рамки, ширина / высота
};

// Доля кадра, которая срежется при заполнении рамки
export const cropShare = (image: { width: number; height: number }, frame: number) => {
  const ratio = image.width / image.height;
  return 1 - Math.min(ratio / frame, frame / ratio);
};

// <picture> с оптимизацией Next (AVIF/WebP, srcset), width/height и lazy loading по умолчанию.
export function Picture({ image, mobile, sizes, eager, className, fit = "cover", frame, onLoad }: Props) {
  const common = { alt: image.alt, sizes, quality: 75 };
  const loading = eager ? { loading: "eager" as const, fetchPriority: "high" as const } : { loading: "lazy" as const };

  const { props } = getImageProps({ ...common, ...loading, src: versioned(image.src), width: image.width, height: image.height });
  const mobileSrcSet = mobile
    ? getImageProps({ ...common, src: versioned(mobile.src), width: mobile.width, height: mobile.height }).props.srcSet
    : undefined;

  // smart: срезать немного — заполняем рамку, как cover; много или форма рамки не известна — целиком на размытом фоне
  const whole = fit === "smart" && (frame == null || cropShare(image, frame) > MAX_CROP);
  const cover = fit === "cover" || (fit === "smart" && !whole);

  // Фото заполняет рамку и обрезается — точка фокуса держит главное в кадре (у кропа для телефона — своя)
  const focus = cover && !mobile && image.focus ? { objectPosition: `${image.focus.x}% ${image.focus.y}%` } : undefined;

  let pictureStyle: CSSProperties | undefined;
  if (whole) {
    const ambient = getImageProps({ alt: "", src: versioned(image.src), width: AMBIENT_WIDTH, height: Math.round((AMBIENT_WIDTH * image.height) / image.width), quality: 40 }).props.src;
    pictureStyle = { "--ambient": `url("${ambient}")` } as CSSProperties;
  }

  return (
    <picture
      className={cx(
        styles.picture,
        fit === "contain" && styles.bare,
        whole && styles.ambient,
        className,
      )}
      style={pictureStyle}
    >
      {mobileSrcSet && <source media="(max-width: 767px)" srcSet={mobileSrcSet} sizes={sizes} />}
      <img
        {...props}
        alt={image.alt}
        onLoad={onLoad}
        className={cx(styles.img, !cover && styles.contain)}
        style={focus ? { ...props.style, ...focus } : props.style}
      />
    </picture>
  );
}
