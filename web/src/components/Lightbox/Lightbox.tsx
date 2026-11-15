"use client";

import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import { Arrow } from "@/components/Button/Button";
import { Picture } from "@/components/Picture/Picture";
import { VideoPlayer } from "@/components/VideoPlayer/VideoPlayer";
import { getLenis } from "@/components/SmoothScroll/SmoothScroll";
import type { ImageAsset } from "@/data/types";
import { cx } from "@/lib/format";
import { useCloseOnHide } from "@/lib/use-close-on-hide";
import styles from "./Lightbox.module.css";

const SWIPE = 48; // px: короче — это был тап, а не свайп

type Props = {
  images: ImageAsset[];
  title: string; // подпись окна: чьи это фото
  video?: string; // ролик — вторым кадром после первого фото; грузится, только когда до него долистали
  // превью, по которому открывается галерея; функция — свои кнопки-превью, каждая открывает окно на своём фото (без бейджа)
  children: ReactNode | ((open: (index: number) => void) => ReactNode);
  className?: string;
};

// Фото (и ролик) на весь экран поверх страницы: стрелки, свайп, клавиши ← →, Esc закрывает (нативный <dialog>).
export function Lightbox({ images, title, video, children, className }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const startX = useRef<number | null>(null);
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  useCloseOnHide(ref);
  // Кадры окна: фото по порядку, ролик — вторым (или единственным); videoAt = -1 — ролика нет
  const count = images.length + (video ? 1 : 0);
  const videoAt = video ? Math.min(1, images.length) : -1;
  const imageAt = (i: number) => (videoAt < 0 || i < videoAt ? images[i] : images[i - 1]);
  const onVideo = index === videoAt;
  const image = onVideo ? undefined : imageAt(index);
  const many = count > 1;
  const nearby = [...new Set([index, (index + 1) % count, (index - 1 + count) % count])].filter((i) => count && i !== videoAt);

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

  const go = (step: number) => setIndex((i) => (i + step + count) % count);

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "ArrowLeft") go(-1);
    if (e.key === "ArrowRight") go(1);
  };

  const onPointerDown = (e: PointerEvent) => {
    // По ролику тянут ползунок перемотки — это не свайп
    if (e.target instanceof HTMLVideoElement) return;
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
          aria-label={`${title}: смотреть фото (${images.length})${video ? " и видео" : ""}`}
          onClick={() => openAt(0)}
        >
          {children}
          {many && (
            <span className={styles.badge} aria-hidden="true">
              {images.length > 1 ? `${images.length} фото` : "фото"}
              {video && " · видео"}
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
              {index + 1} / {count}
            </p>
          )}
          <button type="button" className={styles.close} aria-label="Закрыть" onClick={() => setOpen(false)} />
        </header>

        <figure className={styles.stage} onPointerDown={onPointerDown} onPointerUp={onPointerUp}>
          {/* Соседние кадры грузятся заранее и лежат под текущим: листание без чёрного экрана; пока кадр не пришёл — индикатор под ним */}
          <div className={styles.frame}>
            {open &&
              nearby.map((i) => (
                <Picture
                  key={imageAt(i).src}
                  image={imageAt(i)}
                  sizes="100vw"
                  fit="contain"
                  className={cx(styles.picture, i === index && styles.shown)}
                  eager
                />
              ))}
            {open && onVideo && video && (
              <VideoPlayer className={cx(styles.picture, styles.shown, styles.video)} src={video} label={`Видео: ${title}`} />
            )}
          </div>
          <figcaption className={styles.caption}>{onVideo ? `Видео: ${title}` : image?.alt}</figcaption>
        </figure>

        {many && (
          <>
            <button type="button" className={cx(styles.nav, styles.prev)} aria-label="Предыдущий кадр" onClick={() => go(-1)}>
              <Arrow />
            </button>
            <button type="button" className={cx(styles.nav, styles.next)} aria-label="Следующий кадр" onClick={() => go(1)}>
              <Arrow />
            </button>
          </>
        )}
      </dialog>
    </>
  );
}
