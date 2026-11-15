"use client";

import { useLayoutEffect, useRef } from "react";

type Props = { src: string; label: string; className?: string };

// Плеер ролика (видеообзор, шоурум, проект): стартует сам, звук и кнопки — обычные.
// Ушли со страницы — пауза: Next (Cache Components) не убирает прошлую страницу, а прячет её через <Activity>
// с display: none, и <video> продолжал бы играть невидимым. Cleanup эффекта React вызывает и при скрытии, и при размонтировании.
// Включили этот ролик — остальные на странице на паузе: два звука сразу не нужны.
export function VideoPlayer({ src, label, className }: Props) {
  const ref = useRef<HTMLVideoElement>(null);
  useLayoutEffect(() => {
    const video = ref.current;
    // Ещё не играл — запускаем: в dev StrictMode монтирует дважды, и пауза из cleanup отменяла бы autoPlay.
    // Вернулись на страницу с начатым роликом — не трогаем: он ждёт на паузе, где остановили
    if (video && video.paused && video.currentTime === 0) video.play().catch(() => {});
    return () => video?.pause();
  }, []);
  const pauseOthers = () => {
    document.querySelectorAll("video").forEach((v) => {
      if (v !== ref.current && !v.paused) v.pause();
    });
  };
  return <video ref={ref} className={className} src={src} controls autoPlay playsInline preload="auto" aria-label={label} onPlay={pauseOthers} />;
}
