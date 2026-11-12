"use client";

import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import { Arrow } from "@/components/Button/Button";
import { Picture } from "@/components/Picture/Picture";
import { getLenis } from "@/components/SmoothScroll/SmoothScroll";
import type { ImageAsset } from "@/data/types";
import { cx } from "@/lib/format";
import styles from "./Lightbox.module.css";

const SWIPE = 48; // px: короче — это был тап, а не свайп

type Props = {
  images: ImageAsset[];
  title: string; // подпись окна: чьи это фото
  // превью, по которому открывается галерея; функция — свои кнопки-превью, каждая открывает окно на своём фото (без бейджа)
  children: ReactNode | ((open: (index: number) => void) => ReactNode);
  className?: string;
};

// Фото на весь экран поверх страницы: стрелки, свайп, клавиши ← →, Esc закрывает (нативный <dialog>).
export function Lightbox({ images, title, children, className }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const startX = useRef<number | null>(null);
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const image = images[index];
  const many = images.length > 1;

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog || open === dialog.open) return;
    // Пока окно открыто, страница под ним не прокручивается
    if (open) {
      dialog.showModal();
      getLenis()?.stop();
      document.documentElement.style.overflow = "hidden";
    } else {
      dialog.close();
    }
  }, [open]);

  const go = (step: number) => setIndex((i) => (i + step + images.length) % images.length);

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "ArrowLeft") go(-1);
    if (e.key === "ArrowRight") go(1);
  };

  const onPointerDown = (e: PointerEvent) => {
    startX.current = e.clientX;
  };
  const onPointerUp = (e: PointerEvent) => {
    if (startX.current === null) return;
    const dx = e.clientX - startX.current;
    startX.current = null;
    if (Math.abs(dx) > SWIPE) go(dx < 0 ? 1 : -1);
  };

  const openAt = (i: number) => {
    setIndex(i);
    setOpen(true);
  };

  return (
    <>
      {typeof children === "function" ? (
        children(openAt)
      ) : (
        <button
          type="button"
          className={cx(styles.trigger, className)}
          aria-haspopup="dialog"
          aria-label={`${title}: смотреть фото (${images.length})`}
          onClick={() => openAt(0)}
        >
          {children}
          {many && (
            <span className={styles.badge} aria-hidden="true">
              {images.length} фото
            </span>
          )}
        </button>
      )}
      <dialog
        ref={ref}
        className={styles.dialog}
        data-tone="dark"
        aria-label={title}
        onClose={() => {
          // Esc закрывает окно сам — возвращаем прокрутку странице
          getLenis()?.start();
          document.documentElement.style.overflow = "";
          setOpen(false);
        }}
        onKeyDown={onKeyDown}
        data-lenis-prevent
      >
        <header className={styles.bar}>
          <p className={styles.title}>{title}</p>
          {many && (
            <p className={styles.counter} aria-live="polite">
              {index + 1} / {images.length}
            </p>
          )}
          <button type="button" className={styles.close} aria-label="Закрыть" onClick={() => setOpen(false)} />
        </header>

        <figure className={styles.stage} onPointerDown={onPointerDown} onPointerUp={onPointerUp}>
          {open && image && (
            <Picture key={image.src} image={image} sizes="100vw" fit="contain" className={styles.picture} eager />
          )}
          {image && <figcaption className={styles.caption}>{image.alt}</figcaption>}
        </figure>

        {many && (
          <>
            <button type="button" className={cx(styles.nav, styles.prev)} aria-label="Предыдущее фото" onClick={() => go(-1)}>
              <Arrow />
            </button>
            <button type="button" className={cx(styles.nav, styles.next)} aria-label="Следующее фото" onClick={() => go(1)}>
              <Arrow />
            </button>
          </>
        )}
      </dialog>
    </>
  );
}
