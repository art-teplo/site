import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Reveal } from "@/components/Reveal/Reveal";
import type { Brand, Product } from "@/data/types";
import { formatPrice } from "@/lib/format";
import styles from "./ProductSpecs.module.css";

// Характеристики: чертёж габаритов + таблица на волосяных линиях (референс «675 Chair → Dimensions»).
export function ProductSpecs({ product, brand }: { product: Product; brand?: Brand }) {
  const base = product.variants[0];
  const rows: [string, string][] = [
    ["Бренд", brand ? `${brand.name}${brand.country !== "—" ? `, ${brand.country}` : ""}` : "—"],
    ["Тип", [product.type, product.position].filter(Boolean).join(", ")],
    ["Материал", product.material],
    ["Нагрев", product.heating],
    ["Подключение", product.connections.join(", ")],
    ["Глубина", `${product.depthMm} мм`],
    ...(product.axisMm ? ([["Межосевое расстояние", `${product.axisMm} мм`]] as [string, string][]) : []),
    ...(product.pressureBar ? ([["Рабочее давление", `${product.pressureBar} бар`]] as [string, string][]) : []),
    ["Гарантия", `${product.warrantyYears} лет`],
  ];

  return (
    <Section tone="white" labelledBy="specs-title">
      <Container className={styles.layout}>
        <Reveal className={styles.side}>
          <h2 id="specs-title" className={styles.title}>
            Размеры и данные
          </h2>
          <Drawing height={base.heightMm} width={base.widthMm} depth={product.depthMm} vertical={product.position === "вертикальный"} />
        </Reveal>

        <Reveal className={styles.main} index={1}>
          <table className={styles.table}>
            <caption className="visually-hidden">Характеристики {product.name}</caption>
            <tbody>
              {rows.map(([k, v]) => (
                <tr key={k}>
                  <th scope="row">{k}</th>
                  <td>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <table className={styles.table}>
            <caption className={styles.caption}>Варианты</caption>
            <thead>
              <tr>
                <th scope="col">Размер, мм</th>
                {product.variants.some((v) => v.sections) && <th scope="col">Секций</th>}
                <th scope="col">Мощность</th>
                <th scope="col">Цена от</th>
              </tr>
            </thead>
            <tbody>
              {product.variants.map((v) => (
                <tr key={v.id}>
                  <td>
                    {v.heightMm}×{v.widthMm}
                  </td>
                  {product.variants.some((x) => x.sections) && <td>{v.sections ?? "—"}</td>}
                  <td>{v.powerW ? `${v.powerW} Вт` : "—"}</td>
                  <td>{formatPrice(v.priceByn)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Reveal>
      </Container>
    </Section>
  );
}

// Схема фасада с размерными линиями; прорисовывается при прокрутке. Пропорции — от реальных размеров первого варианта.
function Drawing({ height, width, depth, vertical }: { height: number; width: number; depth: number; vertical: boolean }) {
  const box = 200;
  const scale = box / Math.max(height, width);
  const w = Math.max(width * scale, 24);
  const h = Math.max(height * scale, 24);
  const x = 40 + (box - w) / 2;
  const y = 20 + (box - h) / 2;
  const tubes = Math.max(3, Math.round((vertical ? w : w) / 9));

  return (
    <figure className={styles.drawing}>
      <svg viewBox="0 0 280 260" role="img" aria-label={`Схема: высота ${height} мм, ширина ${width} мм, глубина ${depth} мм`}>
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
        <g fill="currentColor" fontSize="11" fontFamily="inherit" className={styles.labels}>
          <text x={x + w / 2} y={y + h + 36} textAnchor="middle">
            {width}
          </text>
          <text x={x - 26} y={y + h / 2} textAnchor="middle" transform={`rotate(-90 ${x - 26} ${y + h / 2})`}>
            {height}
          </text>
        </g>
      </svg>
      <figcaption>Глубина {depth} мм · размеры в мм</figcaption>
    </figure>
  );
}
