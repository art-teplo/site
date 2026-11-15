"use client";

import { useState, type CSSProperties } from "react";
import { Picture } from "@/components/Picture/Picture";
import { VideoPlayer } from "@/components/VideoPlayer/VideoPlayer";
import type { ImageAsset } from "@/data/types";
import { cx } from "@/lib/format";
import { firstFrame, useVideoShape } from "@/lib/use-video-shape";
import styles from "./SeriesVideo.module.css";

// Видеообзор: кадр серии с кнопкой; файл из админки (S3) грузится только после нажатия и играет на месте.
// Вертикальный ролик (снят под Telegram) — в рамке своей формы, высотой в экран, постер — его первый кадр.
export function SeriesVideo({ url, poster, title }: { url: string; poster: ImageAsset | null; title: string }) {
  const [playing, setPlaying] = useState(false);
  const shape = useVideoShape(url);
  const tall = shape?.tall ?? false;
  return (
    <div className={cx(styles.frame, tall && styles.tall)} style={tall ? ({ "--video-ratio": shape?.ratio } as CSSProperties) : undefined}>
      {playing ? (
        <VideoPlayer className={styles.player} src={url} label={`Видеообзор: ${title}`} />
      ) : (
        <>
          {tall ? (
            <video className={styles.player} src={firstFrame(url)} preload="metadata" muted playsInline aria-hidden="true" tabIndex={-1} />
          ) : (
            poster && <Picture image={poster} sizes="(max-width: 1023px) 100vw, 66vw" />
          )}
          <button type="button" className={styles.cover} onClick={() => setPlaying(true)} aria-label={`Смотреть видеообзор: ${title}`}>
            <span className={styles.chip}>
              <span className={styles.play} aria-hidden="true" />
              Смотреть видеообзор
            </span>
          </button>
        </>
      )}
    </div>
  );
}
