"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { ProductCard } from "@/components/ProductCard/ProductCard";
import { RangeSlider } from "@/components/RangeSlider/RangeSlider";
import { Button } from "@/components/Button/Button";
import { brands } from "@/data/catalog";
import type { Product } from "@/data/types";
import { activeCount, applyFilters, buildFacets, buildRanges, parseFilters, type FacetKey, type RangeKey } from "@/lib/catalog-filter";
import { cx, plural } from "@/lib/format";
import styles from "./CatalogBrowser.module.css";

const brandName = (slug: string) => brands.find((b) => b.slug === slug)?.name ?? slug;

// Список с фильтрами. Состояние — в URL: ссылку с фильтрами можно отправить менеджеру.
export function CatalogBrowser({ products }: { products: Product[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [open, setOpen] = useState(false);

  const facets = useMemo(() => buildFacets(products), [products]);
  const ranges = useMemo(() => buildRanges(products), [products]);
  const state = useMemo(() => parseFilters(new URLSearchParams(params.toString())), [params]);
  const result = useMemo(() => applyFilters(products, state), [products, state]);
  const count = activeCount(state);

  const update = (mutate: (p: URLSearchParams) => void) => {
    const next = new URLSearchParams(params.toString());
    mutate(next);
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  const toggle = (key: FacetKey, value: string) =>
    update((p) => {
      const current = p.getAll(key);
      p.delete(key);
      const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
      next.forEach((v) => p.append(key, v));
    });

  const setRange = (key: RangeKey, [min, max]: [number, number], bounds: [number, number]) =>
    update((p) => {
      p.delete(`${key}_min`);
      p.delete(`${key}_max`);
      if (min > bounds[0]) p.set(`${key}_min`, String(min));
      if (max < bounds[1]) p.set(`${key}_max`, String(max));
    });

  return (
    <div className={styles.layout}>
      <div className={styles.toolbar}>
        <p className={styles.found} aria-live="polite">
          {result.length} из {products.length}
        </p>
        <Button variant="secondary" className={styles.filterToggle} aria-expanded={open} aria-controls="filters" onClick={() => setOpen((v) => !v)}>
          Фильтры{count ? ` · ${count}` : ""}
        </Button>
        <label className={styles.sort}>
          <span className="visually-hidden">Сортировка</span>
          <select
            value={state.sort}
            onChange={(e) => update((p) => (e.target.value === "default" ? p.delete("sort") : p.set("sort", e.target.value)))}
          >
            <option value="default">Сначала популярные</option>
            <option value="price-asc">Сначала дешевле</option>
            <option value="price-desc">Сначала дороже</option>
          </select>
        </label>
      </div>

      <aside id="filters" className={cx(styles.filters, open && styles.filtersOpen)} aria-label="Фильтры">
        {ranges.map((r) => {
          const current = state.ranges[r.key];
          const value: [number, number] = [Math.max(current?.[0] ?? r.min, r.min), Math.min(current?.[1] ?? r.max, r.max)];
          return (
            <RangeSlider
              key={r.key}
              label={r.label}
              unit={r.unit}
              min={r.min}
              max={r.max}
              step={r.step}
              value={value}
              onCommit={(v) => setRange(r.key, v, [r.min, r.max])}
            />
          );
        })}

        {facets.map((f) => (
          <fieldset key={f.key} className={styles.group}>
            <legend className={styles.legend}>{f.label}</legend>
            <div className={styles.options}>
              {f.values.map(({ value, count: n }) => {
                const checked = state.facets[f.key]?.includes(value) ?? false;
                return (
                  <label key={value} className={styles.option}>
                    <input type="checkbox" checked={checked} onChange={() => toggle(f.key, value)} className={styles.optionInput} />
                    <span className={styles.optionLabel}>
                      {f.key === "brand" ? brandName(value) : value}
                      <span className={styles.optionCount}>{n}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        ))}

        {count > 0 && (
          <Button variant="ghost" onClick={() => update((p) => [...p.keys()].forEach((k) => k !== "sort" && p.delete(k)))}>
            Сбросить фильтры
          </Button>
        )}
      </aside>

      <div className={styles.results}>
        {result.length ? (
          <ul className={styles.grid}>
            {result.map((p, i) => (
              <li key={p.slug}>
                <ProductCard product={p} sizes="(max-width: 767px) 50vw, (max-width: 1023px) 33vw, 25vw" priority={i < 2} />
              </li>
            ))}
          </ul>
        ) : (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>Ничего не нашлось</p>
            <p>Ослабьте фильтры или опишите задачу менеджеру — подберём под размеры вручную.</p>
            <Button href="/#lead" arrow>
              Подобрать с менеджером
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

// Без JS и во время гидрации — тот же список без фильтров (его видят поисковики).
export function CatalogFallback({ products }: { products: Product[] }) {
  return (
    <div className={styles.layout}>
      <div className={styles.toolbar}>
        <p className={styles.found}>{plural(products.length, "модель", "модели", "моделей")}</p>
      </div>
      <div className={styles.filters} aria-hidden="true" />
      <div className={styles.results}>
        <ul className={styles.grid}>
          {products.map((p, i) => (
            <li key={p.slug}>
              <ProductCard product={p} sizes="(max-width: 767px) 50vw, (max-width: 1023px) 33vw, 25vw" priority={i < 2} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
