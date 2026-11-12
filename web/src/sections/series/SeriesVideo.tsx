"use client";

import { useState } from "react";
import { Picture } from "@/components/Picture/Picture";
import type { ImageAsset } from "@/data/types";
import styles from "./SeriesVideo.module.css";

// ID ролика из ссылки YouTube; другой адрес — null (тогда просто ссылка)
function youtubeId(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname === "youtu.be") return u.pathname.slice(1) || null;
    if (u.hostname.endsWith("youtube.com")) {
      if (u.pathname === "/watch") return u.searchParams.get("v");
      const m = /^\/(?:embed|shorts|live)\/([\w-]+)/.exec(u.pathname);
      return m ? m[1] : null;
    }
  } catch {
    // не адрес — вернём null ниже
  }
  return null;
}

// Видеообзор: кадр серии с кнопкой; плеер YouTube подгружается только после нажатия (без cookie до него).
export function SeriesVideo({ url, poster, title }: { url: string; poster: ImageAsset | null; title: string }) {
  const [playing, setPlaying] = useState(false);
  const id = youtubeId(url);
  return (
    <div className={styles.frame}>
      {playing && id ? (
        <iframe
          className={styles.player}
          src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`}
          title={`Видеообзор: ${title}`}
          allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
          allowFullScreen
        />
      ) : (
        <>
          {poster && <Picture image={poster} sizes="(max-width: 1023px) 100vw, 66vw" />}
          {id ? (
            <button type="button" className={styles.cover} onClick={() => setPlaying(true)} aria-label={`Смотреть видеообзор: ${title}`}>
              <span className={styles.chip}>
                <span className={styles.play} aria-hidden="true" />
                Смотреть видеообзор
              </span>
            </button>
          ) : (
            <a className={styles.cover} href={url} target="_blank" rel="noopener noreferrer">
              <span className={styles.chip}>
                <span className={styles.play} aria-hidden="true" />
                Видео на YouTube
              </span>
            </a>
          )}
        </>
      )}
    </div>
  );
}
