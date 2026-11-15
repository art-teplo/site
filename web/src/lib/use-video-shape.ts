"use client";

import { useEffect, useState } from "react";

// Пропорции видео: браузер читает только заголовок файла (preload="metadata", несколько КБ), сам ролик не грузится.
// null — ещё не известно или файла нет; tall — вертикальное (ролики под Telegram), ratio — ширина / высота.
export type VideoShape = { tall: boolean; ratio: number } | null;

export function useVideoShape(src: string | undefined): VideoShape {
  const [shape, setShape] = useState<VideoShape>(null);
  useEffect(() => {
    if (!src) return;
    const probe = document.createElement("video");
    probe.preload = "metadata";
    probe.muted = true;
    const read = () => {
      if (probe.videoWidth && probe.videoHeight) {
        setShape({ tall: probe.videoHeight > probe.videoWidth, ratio: probe.videoWidth / probe.videoHeight });
      }
    };
    probe.addEventListener("loadedmetadata", read);
    probe.src = src;
    return () => {
      probe.removeEventListener("loadedmetadata", read);
      probe.removeAttribute("src");
      probe.load(); // обрывает загрузку, если ушли со страницы раньше
    };
  }, [src]);
  return shape;
}

// Первый кадр как постер вертикального видео: фото товара в узкой рамке не смотрится, а при нажатии кадр не прыгает
export const firstFrame = (src: string) => `${src}#t=0.1`;
