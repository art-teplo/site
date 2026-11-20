"use client";

import { useState, type CSSProperties } from "react";
import { Button } from "@/components/Button/Button";
import { ColorSwatches } from "@/components/ColorSwatches/ColorSwatches";
import { LeadForm } from "@/components/LeadForm/LeadForm";
import { Lightbox } from "@/components/Lightbox/Lightbox";
import { Picture } from "@/components/Picture/Picture";
import { VideoPlayer } from "@/components/VideoPlayer/VideoPlayer";
import { useSite } from "@/components/SiteProvider/SiteProvider";
import type { SeriesDetail, VariantRow } from "@/data/types";
import { CONNECTION_LABEL } from "@/lib/connections";
import { cx, formatPrice, plural } from "@/lib/format";
import { colorNote } from "@/lib/price";
import { matchesGalleryColor, orderGalleryPhotos, pickColor } from "@/lib/series-color";
import { thumbnailWindow } from "@/lib/gallery-preview";
import { seriesPrice } from "@/lib/series-selection";
import { variantSize } from "@/lib/variant-size";
import { firstFrame, useVideoShape } from "@/lib/use-video-shape";
import { focusSeriesFilter, purchaseSectionId, scrollToSection } from "./scroll";
import styles from "./SeriesHero.module.css";

type Props = {
  configurationPriceFrom?: number | null;
  series: SeriesDetail;
  images: SeriesDetail["images"]; // фото изделия для галереи (интерьерные — в своём разделе)
  row: VariantRow | null; // выбранный вариант; null — не выбран
  color: string | undefined;
  stale: "pending" | "failed" | null; // строки загружены с другим цветом: цена из них неверна
  onColor: (code: string | undefined) => void;
};

// Рамка главного фото — по форме кадра, как у акций, но не уже 4:5 и не шире 16:9: дальше — фото целиком на размытом фоне
const FRAME_MIN = 4 / 5;
const FRAME_MAX = 16 / 9;
const THUMB_LIMIT = 6;
const frameRatio = (im: { width: number; height: number }) => Math.min(FRAME_MAX, Math.max(FRAME_MIN, im.width / im.height));

// Видеообзор в галерее — вторым после главного фото; выбран — играет на месте фото
const VIDEO = "video" as const;

// Верх страницы серии: галерея, название, цена и цвет; «Уточнить наличие» уносит выбранный вариант в заявку.
export function SeriesHero({ series, images: gallery, row, color, stale, configurationPriceFrom, onColor }: Props) {
  const site = useSite();
  // Выбранное фото помним по адресу файла: при смене цвета его номер в списке может измениться.
  const [pick, setPick] = useState<{ src: string; lead: string } | null>(null);
  const [asking, setAsking] = useState(false);
  const picked = pickColor(series.colorGroups, color);

  const images = orderGalleryPhotos(gallery, picked?.code);
  const lead = images[0]?.src ?? "";
  // Если первое фото сменилось, показываем его. Иначе сохраняем выбранный кадр или видео.
  const current = pick && pick.lead === lead ? Math.max(0, images.findIndex((im) => im.src === pick.src)) : 0;
  const setActive = (i: number) => setPick({ src: images[i].src, lead });
  const selectColor = (code?: string) => {
    if (!code || images.some((image) => matchesGalleryColor(image, code))) setPick(null);
    onColor(code);
  };
  const image = images[current];
  const video = series.videoUrl || "";
  const videoShape = useVideoShape(video || undefined);
  const playing = Boolean(video) && pick?.src === VIDEO && pick.lead === lead;
  // Рамка видео — его форма в тех же пределах, что у фото; вертикальное — 4:5 с полями по бокам
  const videoRatio = Math.min(FRAME_MAX, Math.max(FRAME_MIN, videoShape?.ratio ?? 16 / 9));
  // Лента превью: индексы фото, видео — вторым (или единственным, если фото нет)
  const thumbs: (number | typeof VIDEO)[] = images.map((_, i) => i);
  if (video) thumbs.splice(Math.min(1, thumbs.length), 0, VIDEO);
  const { visible: visibleThumbs, hidden: hiddenThumbs } = thumbnailWindow(thumbs, THUMB_LIMIT);
  const firstHidden = hiddenThumbs.find((t): t is number => t !== VIDEO);

  // «От» считает бэк (и демо) по правилам цены: без цвета и по группе выбранного цвета
  const from = configurationPriceFrom !== undefined ? configurationPriceFrom : picked ? (picked.anyRal ? null : (series.priceFromByGroup[picked.group.id] ?? null)) : series.priceFrom;
  // пока грузятся строки с новым цветом, держим прежнюю цену — без промежуточного «уточняется»; не вышло — по запросу
  const price = seriesPrice({ anyRal: Boolean(picked?.anyRal), stale, selectedPrice: row?.price, priceFrom: from });
  const priceText = stale === "pending" && !picked?.anyRal ? "Обновляем цену…" : price == null ? "Цена по запросу" : `${row ? "" : "от "}${formatPrice(price)}`;

  const colorPart = picked ? `цвет: ${picked.name}${picked.anyRal ? " (RAL на выбор — по запросу)" : ""}` : "цвет не выбран";
  const context = stale !== null ? `${series.name}, параметры выбранного варианта уточняются` : row
    ? [
        series.name,
        `арт. ${row.article}`,
        variantSize(row),
        row.configurationLabel ?? (row.connection ? CONNECTION_LABEL[row.connection] : ""),
        row.mount ? `монтаж: ${row.mount === "floor" ? "напольный" : "настенный"}` : "",
        colorPart,
        price == null ? "цена по запросу" : formatPrice(price),
      ]
        .filter(Boolean)
        .join(", ")
    : `${series.name}, вариант не выбран`;

  // Характеристики: где у серии разброс — чип «от — до», он ведёт к фильтру этого размера в таблице вариантов;
  // выбран вариант — его значение
  const specs: { label: string; value: string; chip: boolean; to?: string; filter?: string }[] = (
    [
      ["Высота, мм", "height", row?.heightMm],
      ["Ширина, мм", "width", row?.widthMm],
      ["Длина, мм", "length", row?.lengthMm],
      ["Глубина, мм", "depth", row?.depthMm],
      ["Межосевое, мм", "axis", row?.axisMm],
      ["Мощность, Вт", "power", row?.powerW],
      ["Площадь обогрева, м²", "area", row?.areaM2],
    ] as const
  ).flatMap(([label, key, own]) => {
    const [min, max] = series.ranges[key] ?? [null, null];
    if (own != null) return [{ label, value: String(own), chip: false }];
    if (min == null || max == null) return [];
    return [min === max ? { label, value: String(min), chip: false } : { label, value: `от ${min} — до ${max}`, chip: true, filter: key }];
  });
  const connections = [...new Set(series.executions.map((e) => e.connection).filter((c): c is NonNullable<typeof c> => c != null))];
  if (row?.connection) specs.push({ label: "Подключение", value: row.configurationLabel ?? CONNECTION_LABEL[row.connection], chip: false });
  else if (connections.length === 1) specs.push({ label: "Подключение", value: CONNECTION_LABEL[connections[0]], chip: false });
  else if (connections.length > 1) specs.push({ label: "Подключение", value: plural(connections.length, "вариант", "варианта", "вариантов"), chip: true, to: "series-pipes" });
  // Общее для всей серии — без чипа
  if (series.material) specs.push({ label: "Материал", value: series.material, chip: false });
  if (series.pressureBar) specs.push({ label: "Рабочее давление", value: `${series.pressureBar} бар`, chip: false });
  if (series.warrantyYears) specs.push({ label: "Гарантия", value: `до ${plural(series.warrantyYears, "года", "лет", "лет")}`, chip: false });
  const note = row
    ? [variantSize(row), row.powerW ? `${row.powerW} Вт` : "", row.configurationLabel ?? (row.connection ? CONNECTION_LABEL[row.connection] : ""), `арт. ${row.article}`].filter(Boolean).join(" · ")
    : "Цена зависит от размера — выберите вариант в таблице ниже";

  return (
    <div className={styles.hero}>
      <div className={styles.gallery}>
        {images.length + (video ? 1 : 0) > 1 && (
          <ul className={styles.thumbs} aria-label="Фото и видео серии">
            {visibleThumbs.map((t) =>
              t === VIDEO ? (
                <li key={VIDEO}>
                  <button
                    type="button"
                    className={cx(styles.thumb, styles.thumbVideo, playing && styles.thumbActive)}
                    aria-label={`Смотреть видеообзор: ${series.name}`}
                    aria-pressed={playing}
                    onClick={() => setPick({ src: VIDEO, lead })}
                  >
                    <video src={firstFrame(video)} preload="metadata" muted playsInline aria-hidden="true" tabIndex={-1} />
                  </button>
                </li>
              ) : (
                <li key={images[t].src}>
                  <button
                    type="button"
                    className={cx(styles.thumb, !playing && t === current && styles.thumbActive)}
                    aria-label={`Показать фото ${t + 1}: ${images[t].alt}`}
                    aria-pressed={!playing && t === current}
                    onClick={() => setActive(t)}
                  >
                    <Picture image={images[t]} sizes="72px" fit="smart" frame={4 / 3} />
                  </button>
                </li>
              ),
            )}
            {firstHidden !== undefined && (
              <li>
                <Lightbox images={images} title={series.name}>
                  {(open) => (
                    <button
                      type="button"
                      className={cx(styles.thumb, styles.thumbMore)}
                      aria-haspopup="dialog"
                      aria-label={`Посмотреть ещё ${hiddenThumbs.length} фото: ${series.name}`}
                      onClick={() => open(firstHidden)}
                    >
                      <Picture image={images[firstHidden]} sizes="72px" fit="smart" frame={4 / 3} />
                      <span className={styles.thumbMoreCount}>+{hiddenThumbs.length}</span>
                    </button>
                  )}
                </Lightbox>
              </li>
            )}
          </ul>
        )}
        {playing ? (
          // Файл грузится только сейчас — по нажатию на превью; звук и кнопки обычные
          <div className={cx(styles.main, styles.videoMain)} style={{ aspectRatio: videoRatio, "--video-ratio": videoRatio } as CSSProperties}>
            <VideoPlayer className={styles.videoPlayer} src={video} label={`Видеообзор: ${series.name}`} />
          </div>
        ) : image ? (
          // Клик по фото — галерея на весь экран с того же кадра: стрелки, свайп, ← →, Esc
          <Lightbox images={images} title={series.name}>
            {(open) => (
              <button
                type="button"
                className={cx(styles.main, styles.zoomable, images.length < 2 && styles.single)}
                style={{ aspectRatio: frameRatio(image) }}
                aria-haspopup="dialog"
                aria-label={`${series.name}: открыть фото ${current + 1} из ${images.length} на весь экран`}
                onClick={() => open(current)}
              >
                {/* Текущий и соседние кадры: остальные полноразмерные фото не конкурируют за загрузку первого экрана. */}
                {images.map((im, i) => ({ im, i })).filter(({ i }) => Math.abs(i - current) <= 1).map(({ im, i }) => (
                  <Picture
                    key={im.src}
                    image={im}
                    sizes="(max-width: 1023px) 100vw, 60vw"
                    eager={i === current}
                    fit="smart"
                    frame={frameRatio(im)}
                    className={cx(styles.layer, i === current && styles.layerShown)}
                  />
                ))}
              </button>
            )}
          </Lightbox>
        ) : (
          <div className={cx(styles.main, images.length < 2 && styles.single)} />
        )}
      </div>

      <div className={styles.info}>
        <p className={styles.brand}>
          {series.brand.name}
          {series.brand.country ? ` · ${series.brand.country}` : ""}
        </p>
        <h1 id="series-title" className={styles.name}>
          {series.name}
        </h1>

        <div id={purchaseSectionId(series.slug)} className={styles.price} aria-live="polite">
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
                    <button type="button" className={styles.chip} onClick={() => (sp.filter ? focusSeriesFilter(sp.filter) : scrollToSection(sp.to ?? "variants"))}>
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
            <ColorSwatches groups={series.colorGroups} selected={color} onSelect={selectColor} compact limit={6} />
            {picked && (
              <button type="button" className={styles.resetColor} onClick={() => selectColor()}>
                Сбросить цвет
              </button>
            )}
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

