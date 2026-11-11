import type { VariantRow } from "@/data/types";
import { pipePoints } from "@/lib/connections";
import styles from "./SizeDrawing.module.css";

export type DrawingRow = Pick<VariantRow, "heightMm" | "widthMm"> & Partial<VariantRow>;
type Range = [number | null, number | null];

const mid = (r?: Range) => (r && r[0] != null && r[1] != null ? Math.round((r[0] + r[1]) / 2) : null);

// Чертёж в масштабе с размерными линиями. Без варианта — контур по средним размерам серии, без патрубков.
export function SizeDrawing({ row, ranges }: { row: DrawingRow | null; ranges?: Record<string, Range> }) {
  const r = row ?? null;
  // Конвектор: нет высоты, но есть длина — рисуем вид сверху: длина × ширина
  const plan = r ? r.heightMm == null && r.lengthMm != null : false;
  const width = r ? (plan ? r.lengthMm : r.widthMm) : (mid(ranges?.width_mm) ?? mid(ranges?.length_mm));
  const height = r ? (plan ? r.widthMm : r.heightMm) : (mid(ranges?.height_mm) ?? mid(ranges?.width_mm));
  const depth = r?.depthMm ?? null;
  if (!width || !height) return null;

  const box = 200;
  const scale = box / Math.max(height, width);
  const w = Math.max(width * scale, 24);
  const h = Math.max(height * scale, 24);
  const x = 40 + (box - w) / 2;
  const y = 20 + (box - h) / 2;
  const tubes = Math.max(3, Math.round(w / 9));
  const pipes = r && "connection" in r && r.connection && !plan ? pipePoints(r as VariantRow) : [];
  const axis = r?.axisMm ?? null;
  const widthName = plan ? "длина" : "ширина";
  const heightName = plan ? "ширина" : "высота";

  return (
    <figure className={styles.drawing}>
      <svg
        viewBox="0 0 280 260"
        role="img"
        aria-label={`Схема: ${heightName} ${height} мм, ${widthName} ${width} мм${depth ? `, глубина ${depth} мм` : ""}${row ? "" : " (средние по серии)"}`}
      >
        <g stroke="currentColor" fill="none" strokeWidth="1" className={styles.lines}>
          {Array.from({ length: tubes }, (_, i) => {
            const tx = x + (i * w) / tubes + 1.5;
            return <rect key={i} x={tx} y={y} width={w / tubes - 3} height={h} rx={2} pathLength={1} />;
          })}
          <line x1={x} y1={y + h + 18} x2={x + w} y2={y + h + 18} pathLength={1} />
          <line x1={x} y1={y + h + 12} x2={x} y2={y + h + 24} pathLength={1} />
          <line x1={x + w} y1={y + h + 12} x2={x + w} y2={y + h + 24} pathLength={1} />
          <line x1={x - 18} y1={y} x2={x - 18} y2={y + h} pathLength={1} />
          <line x1={x - 24} y1={y} x2={x - 12} y2={y} pathLength={1} />
          <line x1={x - 24} y1={y + h} x2={x - 12} y2={y + h} pathLength={1} />
        </g>
        {pipes.length > 0 && (
          <g stroke="var(--color-accent)" strokeWidth="4" strokeLinecap="round">
            {pipes.map((p, i) => {
              const px = x + p.x * scale;
              const py = y + p.y * scale;
              const dx = p.x <= 0 ? -10 : p.x >= width ? 10 : 0;
              const dy = p.y >= height ? 10 : 0;
              return <line key={i} x1={px} y1={py} x2={px + dx} y2={py + dy} />;
            })}
          </g>
        )}
        <g fill="currentColor" fontSize="11" fontFamily="inherit" className={styles.labels}>
          <text x={x + w / 2} y={y + h + 36} textAnchor="middle">
            {width}
          </text>
          <text x={x - 26} y={y + h / 2} textAnchor="middle" transform={`rotate(-90 ${x - 26} ${y + h / 2})`}>
            {height}
          </text>
        </g>
      </svg>
      <figcaption>
        {[depth ? `Глубина ${depth} мм` : null, axis ? `межосевое ${axis} мм` : null, row ? null : "средние размеры серии"]
          .filter(Boolean)
          .join(" · ") || null}
        {depth || axis || !row ? " · " : ""}размеры в мм
      </figcaption>
    </figure>
  );
}
