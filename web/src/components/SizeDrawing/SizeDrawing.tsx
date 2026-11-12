"use client";

import { useEffect, useRef, useState } from "react";
import type { VariantRow } from "@/data/types";
import { pipePoints } from "@/lib/connections";
import styles from "./SizeDrawing.module.css";

export type DrawingRow = Pick<VariantRow, "heightMm" | "widthMm"> & Partial<VariantRow>;

type Pipe = { x: number; y: number; dx: number; dy: number; o: number }; // мм от левого верхнего угла; dx, dy — вылет патрубка; o — прозрачность
type Geo = { w: number; h: number; pipes: Pipe[] };

const DURATION = 480; // мс; при prefers-reduced-motion — 0

// Геометрия строки в мм: у конвектора (нет высоты, есть длина) — вид сверху, длина × ширина
function geoOf(row: DrawingRow): (Geo & { plan: boolean }) | null {
  const plan = row.heightMm == null && row.lengthMm != null;
  const w = plan ? row.lengthMm : row.widthMm;
  const h = plan ? row.widthMm : row.heightMm;
  if (!w || !h) return null;
  const points = !plan && row.connection ? pipePoints(row as VariantRow) : [];
  const pipes = points.map((p) => ({ x: p.x, y: p.y, dx: p.x <= 0 ? -1 : p.x >= w ? 1 : 0, dy: p.y >= h ? 1 : 0, o: 1 }));
  return { plan, w, h, pipes };
}

const mix = (a: number, b: number, t: number) => a + (b - a) * t;

// Промежуточный кадр: размеры и патрубки перетекают к новым значениям; лишние патрубки гаснут, новые проявляются
function lerp(a: Geo, b: Geo, t: number): Geo {
  const n = Math.max(a.pipes.length, b.pipes.length);
  const pipes = Array.from({ length: n }, (_, i) => {
    const from = a.pipes[i] ?? { ...b.pipes[i], o: 0 };
    const to = b.pipes[i] ?? { ...from, o: 0 };
    return { x: mix(from.x, to.x, t), y: mix(from.y, to.y, t), dx: mix(from.dx, to.dx, t), dy: mix(from.dy, to.dy, t), o: mix(from.o, to.o, t) };
  });
  return { w: mix(a.w, b.w, t), h: mix(a.h, b.h, t), pipes };
}

// Чертёж в масштабе с размерными линиями. Размер холста не меняется, поэтому страница не прыгает;
// при смене строки контур, размерные линии и патрубки плавно переезжают к новым значениям.
export function SizeDrawing({ row }: { row: DrawingRow | null }) {
  const target = row ? geoOf(row) : null;
  const key = target ? JSON.stringify([target.w, target.h, target.pipes]) : "";
  const [geo, setGeo] = useState<Geo | null>(target);
  const current = useRef<Geo | null>(target);
  const lastKey = useRef(key);
  const targetRef = useRef(target);

  useEffect(() => {
    targetRef.current = target;
  });

  // Только смена значений запускает перелёт: перерисовка с теми же размерами его не обрывает
  useEffect(() => {
    if (key === lastKey.current) return;
    lastKey.current = key;
    const target = targetRef.current;
    if (!target) return;
    const from = current.current ?? target;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const start = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const t = reduced ? 1 : Math.min(1, (now - start) / DURATION);
      const eased = 1 - (1 - t) ** 3;
      const next = t === 1 ? target : lerp(from, target, eased);
      current.current = next;
      setGeo(next);
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [key]);

  const shown = geo ?? target;
  if (!row || !target || !shown) return null;

  const box = 200;
  const scale = box / Math.max(shown.h, shown.w);
  const w = Math.max(shown.w * scale, 24);
  const h = Math.max(shown.h * scale, 24);
  const x = 40 + (box - w) / 2;
  const y = 20 + (box - h) / 2;
  const tubes = Math.max(3, Math.round(w / 9));
  const widthName = target.plan ? "длина" : "ширина";
  const heightName = target.plan ? "ширина" : "высота";
  const depth = row.depthMm ?? null;
  const axis = row.axisMm ?? null;
  const extra = [row.article ? `арт. ${row.article}` : null, depth ? `глубина ${depth} мм` : null, axis ? `межосевое ${axis} мм` : null].filter(Boolean);

  return (
    <figure className={styles.drawing}>
      <svg viewBox="0 0 280 260" role="img" aria-label={`Схема: ${heightName} ${target.h} мм, ${widthName} ${target.w} мм${depth ? `, глубина ${depth} мм` : ""}`}>
        <g stroke="currentColor" fill="none" strokeWidth="1">
          {Array.from({ length: tubes }, (_, i) => (
            <rect key={i} x={x + (i * w) / tubes + 1.5} y={y} width={w / tubes - 3} height={h} rx={2} />
          ))}
          <line x1={x} y1={y + h + 18} x2={x + w} y2={y + h + 18} />
          <line x1={x} y1={y + h + 12} x2={x} y2={y + h + 24} />
          <line x1={x + w} y1={y + h + 12} x2={x + w} y2={y + h + 24} />
          <line x1={x - 18} y1={y} x2={x - 18} y2={y + h} />
          <line x1={x - 24} y1={y} x2={x - 12} y2={y} />
          <line x1={x - 24} y1={y + h} x2={x - 12} y2={y + h} />
        </g>
        {shown.pipes.length > 0 && (
          <g stroke="var(--color-accent)" strokeWidth="4" strokeLinecap="round">
            {shown.pipes.map((p, i) => {
              const px = x + p.x * scale;
              const py = y + p.y * scale;
              return <line key={i} x1={px} y1={py} x2={px + p.dx * 10} y2={py + p.dy * 10} opacity={p.o} />;
            })}
          </g>
        )}
        <g fill="currentColor" fontSize="11" fontFamily="inherit">
          <text x={x + w / 2} y={y + h + 36} textAnchor="middle">
            {Math.round(shown.w)}
          </text>
          <text x={x - 26} y={y + h / 2} textAnchor="middle" transform={`rotate(-90 ${x - 26} ${y + h / 2})`}>
            {Math.round(shown.h)}
          </text>
        </g>
      </svg>
      <figcaption>{[...extra, "размеры в мм"].join(" · ")}</figcaption>
    </figure>
  );
}
