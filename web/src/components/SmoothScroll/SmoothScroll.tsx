"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import Lenis from "lenis";
import { backScroll, watchHistory } from "@/lib/back-navigation";

// Один экземпляр Lenis на приложение — меню останавливает его, когда открыто.
let lenis: Lenis | null = null;
export const getLenis = () => lenis;

const RESTORE_MS = 3000;

const headerOffset = () => -(document.querySelector("header")?.getBoundingClientRect().height ?? 0);

// Плавный скролл на всю страницу. Не включается при prefers-reduced-motion.
export function SmoothScroll() {
  const pathname = usePathname();

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    // allowNestedScroll: блоки со своей прокруткой (фильтры каталога, меню) листаются колесом сами,
    // а дойдя до края, отдают прокрутку странице
    lenis = new Lenis({ lerp: 0.1, anchors: { offset: headerOffset() }, allowNestedScroll: true });
    let frame = requestAnimationFrame(function raf(time) {
      lenis?.raf(time);
      frame = requestAnimationFrame(raf);
    });

    return () => {
      cancelAnimationFrame(frame);
      lenis?.destroy();
      lenis = null;
    };
  }, []);

  useEffect(() => watchHistory(), []);

  // Переход между страницами: Lenis помнит старую позицию и «доезжает» до неё на новой странице.
  // Сбрасываем мгновенно — наверх или к якорю из адреса. «Назад» — туда, где страницу оставили:
  // ждём, пока она дорастёт до нужной высоты (список догружается), но не дольше RESTORE_MS
  useEffect(() => {
    const instance = lenis;
    const hash = window.location.hash;
    const back = backScroll();
    const jump = (y: number | HTMLElement) => {
      if (instance) {
        instance.resize();
        instance.scrollTo(y, { offset: typeof y === "number" ? 0 : headerOffset(), immediate: true, force: true });
      } else if (typeof y === "number") window.scrollTo(0, y);
      else y.scrollIntoView();
    };
    let frame = 0;
    let stopped = false;
    const stop = () => {
      stopped = true;
    };
    // Человек сам крутит страницу — больше не вмешиваемся
    const events = ["wheel", "touchstart", "keydown", "pointerdown"] as const;
    if (back !== undefined) events.forEach((e) => window.addEventListener(e, stop, { passive: true, once: true }));
    const started = performance.now();
    const step = () => {
      if (stopped) return;
      if (back === undefined) {
        const target = hash ? document.querySelector<HTMLElement>(decodeURIComponent(hash)) : null;
        jump(target ?? 0);
        return;
      }
      const max = document.documentElement.scrollHeight - window.innerHeight;
      if (max >= back || performance.now() - started > RESTORE_MS) {
        jump(Math.min(back, Math.max(0, max)));
        return;
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frame);
      events.forEach((e) => window.removeEventListener(e, stop));
    };
  }, [pathname]);

  return null;
}
