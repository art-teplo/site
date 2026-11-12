"use client";

import { useState } from "react";
import { Button } from "@/components/Button/Button";
import { ColorSwatches } from "@/components/ColorSwatches/ColorSwatches";
import { LeadForm } from "@/components/LeadForm/LeadForm";
import { Picture } from "@/components/Picture/Picture";
import { useSite } from "@/components/SiteProvider/SiteProvider";
import type { SeriesDetail, VariantRow } from "@/data/types";
import { CONNECTION_LABEL } from "@/lib/connections";
import { cx, formatPrice, plural } from "@/lib/format";
import { colorNote } from "@/lib/price";
import { pickColor } from "@/lib/series-color";
import { scrollToSection } from "./scroll";
import styles from "./SeriesHero.module.css";

type Props = {
  series: SeriesDetail;
  images: SeriesDetail["images"]; // фото изделия для галереи (интерьерные — в своём разделе)
  row: VariantRow | null; // выбранный вариант; null — не выбран
  color: string | undefined;
  stale: "pending" | "failed" | null; // строки загружены с другим цветом: цена из них неверна
  onColor: (code: string) => void;
};

// Размеры как на бирке: ширина × высота; у конвектора высоты нет — длина × ширина
const sizeOf = (row: VariantRow) => {
  const pair = row.heightMm == null && row.lengthMm != null ? [row.lengthMm, row.widthMm] : [row.widthMm, row.heightMm];
  const parts = pair.filter((n): n is number => n != null);
  return parts.length ? `${parts.join("×")} мм` : "";
};

// Верх страницы серии: галерея, название, цена и цвет; «Уточнить наличие» уносит выбранный вариант в заявку.
export function SeriesHero({ series, images: gallery, row, color, stale, onColor }: Props) {
  const site = useSite();
  const [active, setActive] = useState(0);
  const [asking, setAsking] = useState(false);
  const picked = pickColor(series.colorGroups, color);

  // Фото под цвет и положение: нет подходящих — общие, нет и их — все
  const images = (() => {
    const fit = (i: SeriesDetail["images"][number]) =>
      (!i.color || i.color === picked?.code) && (!i.orientation || !row?.orientation || i.orientation === row.orientation);
    const exact = picked ? gallery.filter((i) => i.color === picked.code && fit(i)) : [];
    const list = exact.length ? exact : gallery.filter(fit);
    return list.length ? list : gallery;
  })();
  const image = images[Math.min(active, images.length - 1)];

  // «От» считает бэк (и демо) по правилам цены: без цвета и по группе выбранного цвета
  const from = picked ? (picked.anyRal ? null : (series.priceFromByGroup[picked.group.id] ?? null)) : series.priceFrom;
  // пока грузятся строки с новым цветом, держим прежнюю цену — без промежуточного «уточняется»; не вышло — по запросу
  const price = row ? (picked?.anyRal || stale === "failed" ? null : row.price) : from;
  const priceText = price == null ? "Цена по запросу" : `${row ? "" : "от "}${formatPrice(price)}`;

  const colorPart = picked ? `цвет: ${picked.name}${picked.anyRal ? " (RAL на выбор — по запросу)" : ""}` : "цвет не выбран";
  const context = row
    ? [
        series.name,
        `арт. ${row.article}`,
        sizeOf(row),
        row.connection ? CONNECTION_LABEL[row.connection] : "",
        colorPart,
        price == null ? "цена по запросу" : formatPrice(price),
      ]
        .filter(Boolean)
        .join(", ")
    : `${series.name}, вариант не выбран`;

  // Характеристики: где у серии разброс — чип «от — до», он ведёт к таблице вариантов; выбран вариант — его значение
  const specs: { label: string; value: string; chip: boolean; to?: string }[] = (
    [
      ["Высота, мм", "height", row?.heightMm],
      ["Ширина, мм", "width", row?.widthMm],
      ["Длина, мм", "length", row?.lengthMm],
    ] as const
  ).flatMap(([label, key, own]) => {
    const [min, max] = series.ranges[key] ?? [null, null];
    if (own != null) return [{ label, value: String(own), chip: false }];
    if (min == null || max == null) return [];
    return [min === max ? { label, value: String(min), chip: false } : { label, value: `от ${min} — до ${max}`, chip: true }];
  });
  const connections = [...new Set(series.executions.map((e) => e.connection).filter((c): c is NonNullable<typeof c> => c != null))];
  if (row?.connection) specs.push({ label: "Подключение", value: CONNECTION_LABEL[row.connection], chip: false });
  else if (connections.length === 1) specs.push({ label: "Подключение", value: CONNECTION_LABEL[connections[0]], chip: false });
  else if (connections.length > 1) specs.push({ label: "Подключение", value: plural(connections.length, "вариант", "варианта", "вариантов"), chip: true, to: "series-pipes" });
  const note = row
    ? [sizeOf(row), row.powerW ? `${row.powerW} Вт` : "", row.connection ? CONNECTION_LABEL[row.connection] : "", `арт. ${row.article}`].filter(Boolean).join(" · ")
    : "Цена зависит от размера — выберите вариант в таблице ниже";

  return (
    <div className={styles.hero}>
      <div className={styles.gallery}>
        {images.length > 1 && (
          <ul className={styles.thumbs} aria-label="Фото серии">
            {images.map((im, i) => (
              <li key={`${im.src}-${i}`}>
                <button
                  type="button"
                  className={cx(styles.thumb, im === image && styles.thumbActive)}
                  aria-label={`Показать фото ${i + 1}: ${im.alt}`}
                  aria-pressed={im === image}
                  onClick={() => setActive(i)}
                >
                  <Picture image={im} sizes="72px" />
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className={cx(styles.main, images.length < 2 && styles.single)}>
          {image && <Picture key={image.src} image={image} sizes="(max-width: 1023px) 100vw, 50vw" eager />}
        </div>
      </div>

      <div className={styles.info}>
        <p className={styles.brand}>
          {series.brand.name}
          {series.brand.country ? ` · ${series.brand.country}` : ""}
        </p>
        <h1 id="series-title" className={styles.name}>
          {series.name}
        </h1>

        <div className={styles.price} aria-live="polite">
          <span className={styles.priceValue}>{priceText}</span>
          <span className={styles.priceNote}>{note}</span>
        </div>

        {specs.length > 0 && (
          <dl className={styles.specs}>
            {specs.map((sp) => (
              <div key={sp.label} className={styles.spec}>
                <dt>{sp.label}</dt>
                <dd>
                  {sp.chip ? (
                    <button type="button" className={styles.chip} onClick={() => scrollToSection(sp.to ?? "variants")}>
                      {sp.value}
                      <span aria-hidden="true">›</span>
                    </button>
                  ) : (
                    sp.value
                  )}
                </dd>
              </div>
            ))}
          </dl>
        )}

        {series.colorGroups.length > 0 && (
          <div className={styles.colors}>
            <p className={styles.legend}>
              Цвет{" "}
              <span>
                {picked ? picked.name : "не выбран"}
                {picked && <em>{colorNote(picked.group)}</em>}
              </span>
            </p>
            <ColorSwatches groups={series.colorGroups} selected={color} onSelect={onColor} compact limit={6} />
          </div>
        )}

        {!asking ? (
          <>
            <div className={styles.actions}>
              <Button onClick={() => setAsking(true)} arrow>
                Уточнить наличие
              </Button>
            </div>
            <p className={styles.call}>
              Или позвоните: <a href={site.phoneHref}>{site.phone}</a>
            </p>
          </>
        ) : (
          <div className={styles.ask}>
            <p className={styles.askContext}>{context}</p>
            <LeadForm source={`series/${series.slug}`} context={`Наличие и точная цена: ${context}`} withFile={false} compact submitLabel="Уточнить наличие" />
          </div>
        )}
      </div>
    </div>
  );
}
