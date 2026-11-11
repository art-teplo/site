import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Reveal } from "@/components/Reveal/Reveal";
import type { Brand, Product } from "@/data/types";
import { formatPrice } from "@/lib/format";
import { SizeDrawing } from "@/components/SizeDrawing/SizeDrawing";
import styles from "./ProductSpecs.module.css";

// Характеристики: чертёж габаритов + таблица на волосяных линиях (референс «675 Chair → Dimensions»).
export function ProductSpecs({ product, brand }: { product: Product; brand?: Brand }) {
  const base = product.variants[0];
  const rows: [string, string][] = [
    ["Бренд", brand ? `${brand.name}${brand.country ? `, ${brand.country}` : ""}` : "—"],
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
          <SizeDrawing row={{ heightMm: base.heightMm, widthMm: base.widthMm, depthMm: product.depthMm }} />
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
