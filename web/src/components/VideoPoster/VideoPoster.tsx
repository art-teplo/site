"use client";

import { useState, type CSSProperties, type ReactNode } from "react";
import { Frame } from "@/components/Frame/Frame";
import { VideoPlayer } from "@/components/VideoPlayer/VideoPlayer";
import { firstFrame, useVideoShape } from "@/lib/use-video-shape";
import styles from "./VideoPoster.module.css";

type Props = {
  src?: string; // нет — постер с подписью «скоро», без кнопки
  label: string; // подпись под кнопкой или «скоро»
  children: ReactNode; // постер — <Picture>, отрисованный на сервере
};

// Постер 16:9, нажимается целиком; по нажатию на его месте играет видео со звуком и обычными кнопками.
// Файл грузится только после нажатия — главная не тянет мегабайты зря (до этого — только заголовок, ради пропорций).
// Вертикальный ролик (снят под Telegram) — рамка его формы высотой в экран, постер — первый кадр; секция видит это
// по data-shape="tall". Появится озвучка — добавить <track> с субтитрами.
export function VideoPoster({ src, label, children }: Props) {
  const [playing, setPlaying] = useState(false);
  const shape = useVideoShape(src);
  const tall = Boolean(src && shape?.tall);

  return (
    <div
      className={styles.root}
      data-shape={tall ? "tall" : undefined}
      style={tall ? ({ "--video-ratio": shape?.ratio } as CSSProperties) : undefined}
    >
      <Frame ratio={tall ? String(shape?.ratio) : "16 / 9"} parallax={!playing && !tall}>
        {playing && src ? (
          <VideoPlayer className={styles.video} src={src} label={label} />
        ) : tall && src ? (
          <video className={styles.video} src={firstFrame(src)} preload="metadata" muted playsInline aria-hidden="true" tabIndex={-1} />
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
