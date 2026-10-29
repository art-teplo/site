"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import Lenis from "lenis";

// Один экземпляр Lenis на приложение — меню останавливает его, когда открыто.
let lenis: Lenis | null = null;
export const getLenis = () => lenis;

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

  // Переход между страницами: Lenis помнит старую позицию и «доезжает» до неё на новой странице.
  // Сбрасываем мгновенно — наверх или к якорю из адреса.
  useEffect(() => {
    const instance = lenis;
    const hash = window.location.hash;
    const frame = requestAnimationFrame(() => {
      const target = hash ? document.querySelector<HTMLElement>(decodeURIComponent(hash)) : null;
      if (instance) {
        instance.resize();
        if (target) instance.scrollTo(target, { offset: headerOffset(), immediate: true, force: true });
        else instance.scrollTo(0, { immediate: true, force: true });
      } else if (target) {
        target.scrollIntoView();
      } else {
        window.scrollTo(0, 0);
      }
    });
    return () => cancelAnimationFrame(frame);
  }, [pathname]);

  return null;
}
