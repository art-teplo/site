"use client";

import { useState } from "react";
import { Button } from "@/components/Button/Button";
import { ColorSwatches } from "@/components/ColorSwatches/ColorSwatches";
import { LeadForm } from "@/components/LeadForm/LeadForm";
import { Picture } from "@/components/Picture/Picture";
import { useSite } from "@/components/SiteProvider/SiteProvider";
import type { SeriesDetail, VariantRow } from "@/data/types";
import { CONNECTION_LABEL } from "@/lib/connections";
import { cx, formatPrice } from "@/lib/format";
import { pickColor } from "@/lib/series-color";
import styles from "./SeriesHero.module.css";

type Props = {
  series: SeriesDetail;
  row: VariantRow | null; // выбранный вариант; null — не выбран
  color: string | undefined;
  stale: "pending" | "failed" | null; // строки загружены с другим цветом: цена из них неверна
  onColor: (code: string) => void;
};

const range = (pair: [number | null, number | null] | undefined) => {
  const [min, max] = pair ?? [null, null];
  return min == null || max == null ? null : min === max ? String(min) : `${min}–${max}`;
};

// Размеры как на бирке: ширина × высота; у конвектора высоты нет — длина × ширина
const sizeOf = (row: VariantRow) => {
  const pair = row.heightMm == null && row.lengthMm != null ? [row.lengthMm, row.widthMm] : [row.widthMm, row.heightMm];
  const parts = pair.filter((n): n is number => n != null);
  return parts.length ? `${parts.join("×")} мм` : "";
};

// Верх страницы серии: галерея, название, цена и цвет; «Уточнить наличие» уносит выбранный вариант в заявку.
export function SeriesHero({ series, row, color, stale, onColor }: Props) {
  const site = useSite();
  const [active, setActive] = useState(0);
  const [asking, setAsking] = useState(false);
  const picked = pickColor(series.colorGroups, color);

  // Фото под цвет и положение: нет подходящих — общие, нет и их — все
  const images = (() => {
    const fit = (i: SeriesDetail["images"][number]) =>
      (!i.color || i.color === picked?.code) && (!i.orientation || !row?.orientation || i.orientation === row.orientation);
    const exact = picked ? series.images.filter((i) => i.color === picked.code && fit(i)) : [];
    const list = exact.length ? exact : series.images.filter(fit);
    return list.length ? list : series.images;
  })();
  const image = images[Math.min(active, images.length - 1)];

  // «От» считает бэк (и демо) по правилам цены: без цвета и по группе выбранного цвета
  const from = picked ? (picked.anyRal ? null : (series.priceFromByGroup[picked.group.id] ?? null)) : series.priceFrom;
  const price = row ? (picked?.anyRal || stale ? null : row.price) : from;
  const priceText = price == null ? (stale === "pending" ? "Цена уточняется" : "Цена по запросу") : `${row ? "" : "от "}${formatPrice(price)}`;

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

  const dims = (
    [
      ["Высота", range(series.ranges.height)],
      ["Ширина", range(series.ranges.width)],
      ["Длина", range(series.ranges.length)],
    ] as const
  ).filter(([, v]) => v);
  const note = row
    ? [sizeOf(row), row.powerW ? `${row.powerW} Вт` : "", row.connection ? CONNECTION_LABEL[row.connection] : "", `арт. ${row.article}`].filter(Boolean).join(" · ")
    : dims.length
      ? `${dims.map(([label, v]) => `${label.toLowerCase()} ${v}`).join(", ")} мм. Выберите вариант в таблице ниже`
      : "Выберите вариант в таблице ниже";

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
          {series.videoUrl && (
            <a href={series.videoUrl} target="_blank" rel="noopener noreferrer" className={styles.video}>
              <span className={styles.play} aria-hidden="true" />
              Видео на YouTube
            </a>
          )}
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

        {series.colorGroups.length > 0 && (
          <div className={styles.colors}>
            <p className={styles.legend}>
              Цвет <span>{picked ? picked.name : "не выбран"}</span>
            </p>
            <ColorSwatches groups={series.colorGroups} selected={color} onSelect={onColor} />
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
