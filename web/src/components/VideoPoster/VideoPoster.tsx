"use client";

import { useState, type ReactNode } from "react";
import { Frame } from "@/components/Frame/Frame";
import styles from "./VideoPoster.module.css";

type Props = {
  src?: string; // нет — постер с подписью «скоро», без кнопки
  label: string; // подпись под кнопкой или «скоро»
  children: ReactNode; // постер — <Picture>, отрисованный на сервере
};

// Постер 16:9, нажимается целиком; по нажатию на его месте играет видео со звуком и обычными кнопками.
// Файл грузится только после нажатия — главная не тянет мегабайты зря. Появится озвучка — добавить <track> с субтитрами.
export function VideoPoster({ src, label, children }: Props) {
  const [playing, setPlaying] = useState(false);

  return (
    <div className={styles.root}>
      <Frame ratio="16 / 9" parallax={!playing}>
        {playing ? (
          <video className={styles.video} src={src} controls autoPlay playsInline preload="auto" />
        ) : (
          children
        )}
      </Frame>
      {!playing &&
        (src ? (
          <button type="button" className={styles.cover} onClick={() => setPlaying(true)}>
            <span className={styles.icon} aria-hidden="true" />
            <span className={styles.label}>{label}</span>
          </button>
        ) : (
          <span className={styles.cover} aria-hidden="true">
            <span className={styles.label}>{label}</span>
          </span>
        ))}
    </div>
  );
}
