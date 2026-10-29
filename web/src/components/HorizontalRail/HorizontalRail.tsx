"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { cx } from "@/lib/format";
import styles from "./HorizontalRail.module.css";

type Props = { head: ReactNode; children: ReactNode; className?: string };

// Лента, которая едет вбок, пока страница прокручивается вниз (секция закреплена на экране).
// На узких экранах и при prefers-reduced-motion — обычная горизонтальная прокрутка пальцем.
export function HorizontalRail({ head, children, className }: Props) {
  const outerRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [distance, setDistance] = useState(0);
  const [pinned, setPinned] = useState(false);

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 1024px) and (prefers-reduced-motion: no-preference)");
    const outer = outerRef.current;
    const track = trackRef.current;
    if (!outer || !track) return;

    let frame = 0;
    const measure = () => {
      const active = desktop.matches;
      setPinned(active);
      setDistance(active ? Math.max(0, track.scrollWidth - track.clientWidth) : 0);
    };
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (!desktop.matches) {
          track.style.transform = "";
          return;
        }
        const max = outer.offsetHeight - window.innerHeight;
        const progress = max > 0 ? Math.min(1, Math.max(0, -outer.getBoundingClientRect().top / max)) : 0;
        const overflow = track.scrollWidth - track.clientWidth;
        track.style.transform = `translate3d(${-progress * overflow}px, 0, 0)`;
      });
    };

    measure();
    update();
    const ro = new ResizeObserver(() => {
      measure();
      update();
    });
    ro.observe(track);
    desktop.addEventListener("change", measure);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
      desktop.removeEventListener("change", measure);
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  return (
    <div
      ref={outerRef}
      className={cx(styles.outer, pinned && styles.pinned, className)}
      style={pinned ? { height: `calc(100svh + ${distance}px)` } : undefined}
    >
      <div className={styles.sticky}>
        {head}
        <div ref={trackRef} className={styles.track}>
          {children}
        </div>
      </div>
    </div>
  );
}
