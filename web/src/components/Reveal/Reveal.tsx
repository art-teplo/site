"use client";

import { useEffect, useRef, type CSSProperties, type ElementType, type ReactNode } from "react";
import { cx } from "@/lib/format";
import styles from "./Reveal.module.css";

// Один IntersectionObserver на всю страницу — дешевле, чем по наблюдателю на элемент.
let observer: IntersectionObserver | null = null;
const getObserver = () => {
  if (!observer) {
    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.setAttribute("data-visible", "");
            observer?.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
    );
  }
  return observer;
};

type Props = {
  children: ReactNode;
  as?: ElementType;
  index?: number; // позиция среди соседей — задаёт stagger
  className?: string;
  id?: string;
  // rise — fade + сдвиг блока; mask — блок не двигается, анимируются только SplitText внутри
  effect?: "rise" | "mask";
};

// Появление при прокрутке: fade + сдвиг (rise) или только запуск SplitText (mask). Без JS контент виден (см. html.js в base.css).
export function Reveal({ children, as: Tag = "div", index = 0, className, id, effect = "rise" }: Props) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const io = getObserver();
    io.observe(node);
    return () => io.unobserve(node);
  }, []);

  return (
    <Tag ref={ref} id={id} data-reveal="" className={cx(effect === "rise" && styles.reveal, className)} style={{ "--i": index } as CSSProperties}>
      {children}
    </Tag>
  );
}
