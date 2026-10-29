"use client";

import { useState } from "react";
import { Picture } from "@/components/Picture/Picture";
import { Button } from "@/components/Button/Button";
import { ChoiceGroup } from "@/components/Field/Field";
import { LeadForm } from "@/components/LeadForm/LeadForm";
import type { Brand, Product } from "@/data/types";
import { site } from "@/data/site";
import { cx, formatPrice } from "@/lib/format";
import styles from "./ProductHero.module.css";

const variantLabel = (v: Product["variants"][number]) =>
  v.sections ? `${v.sections} секц. · ${v.heightMm}×${v.widthMm}` : `${v.heightMm}×${v.widthMm} мм`;

// Верх карточки: галерея слева, выбор варианта и цена справа (референс «675 Chair»).
export function ProductHero({ product, brand }: { product: Product; brand?: Brand }) {
  const [active, setActive] = useState(0);
  const [variantId, setVariantId] = useState(product.variants[0].id);
  const [colorId, setColorId] = useState(product.colors[0].id);
  const [connection, setConnection] = useState(product.connections[0]);
  const [asking, setAsking] = useState(false);

  const variant = product.variants.find((v) => v.id === variantId) ?? product.variants[0];
  const color = product.colors.find((c) => c.id === colorId) ?? product.colors[0];
  const context = `${product.name}; ${variantLabel(variant)}; ${color.name}; подключение: ${connection}`;

  return (
    <div className={styles.hero}>
      <div className={styles.gallery}>
        <ul className={styles.thumbs} aria-label="Фото товара">
          {product.images.map((image, i) => (
            <li key={image.src}>
              <button
                type="button"
                className={cx(styles.thumb, i === active && styles.thumbActive)}
                aria-label={`Показать фото ${i + 1}: ${image.alt}`}
                aria-pressed={i === active}
                onClick={() => setActive(i)}
              >
                <Picture image={image} sizes="72px" />
              </button>
            </li>
          ))}
        </ul>
        <div className={styles.main}>
          {product.images.map((image, i) => (
            <div key={image.src} className={cx(styles.slide, i === active && styles.slideActive)} aria-hidden={i !== active}>
              <Picture image={image} sizes="(max-width: 1023px) 100vw, 50vw" eager={i === 0} />
            </div>
          ))}
          {product.videoUrl && (
            <a href={product.videoUrl} target="_blank" rel="noopener noreferrer" className={styles.video}>
              <span className={styles.play} aria-hidden="true" />
              Видео на YouTube
            </a>
          )}
        </div>
      </div>

      <div className={styles.info}>
        <p className={styles.brand}>
          {brand?.name}
          {brand?.country && brand.country !== "—" ? ` · ${brand.country}` : ""}
        </p>
        <h1 className={styles.name}>{product.name}</h1>
        <p className={styles.summary}>{product.summary}</p>

        <div className={styles.price} aria-live="polite">
          <span className={styles.priceValue}>{formatPrice(variant.priceByn)}</span>
          <span className={styles.priceNote}>за {variantLabel(variant)} · {variant.powerW} Вт</span>
        </div>

        <div className={styles.options}>
          <ChoiceGroup
            legend={product.variants.some((v) => v.sections) ? "Размер и секции" : "Размер"}
            name="variant"
            options={product.variants.map(variantLabel)}
            value={variantLabel(variant)}
            onChange={(label) => setVariantId(product.variants.find((v) => variantLabel(v) === label)?.id ?? variantId)}
          />

          <fieldset className={styles.colors}>
            <legend className={styles.legend}>
              Цвет <span>{color.name}</span>
            </legend>
            <div className={styles.swatches}>
              {product.colors.map((c) => (
                <label key={c.id} className={styles.swatch} title={c.name}>
                  <input
                    type="radio"
                    name="color"
                    value={c.id}
                    checked={c.id === colorId}
                    onChange={() => setColorId(c.id)}
                    className={styles.swatchInput}
                    aria-label={c.name}
                  />
                  <span className={styles.swatchDot} style={{ background: c.hex }} />
                </label>
              ))}
            </div>
            <p className={styles.ral}>Любой другой цвет — по палитре RAL</p>
          </fieldset>

          {product.connections.length > 1 && (
            <ChoiceGroup legend="Подключение" name="connection" options={product.connections} value={connection} onChange={setConnection} />
          )}
        </div>

        {!asking ? (
          <>
            {/* Одна кнопка: цена уже на экране, а наличие и точную цену менеджер называет в одном звонке */}
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
            <LeadForm
              source={`product/${product.slug}`}
              context={`Наличие и точная цена: ${context}`}
              withFile={false}
              compact
              submitLabel="Уточнить наличие"
            />
          </div>
        )}
      </div>
    </div>
  );
}
