"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/Button/Button";
import { ColorSwatches } from "@/components/ColorSwatches/ColorSwatches";
import { ShowcaseCard } from "@/components/ShowcaseCard/ShowcaseCard";
import { mapShowcase, type ApiShowcase, type Showcase } from "@/data/catalog-map";
import type { Brand, CatalogField, Category, ColorGroup, Facet } from "@/data/types";
import { csv, parseCatalogQuery, serializeCatalogQuery, type CatalogQuery, PAGE_SIZE_CARDS } from "@/lib/catalog-query";
import { cx, plural } from "@/lib/format";
import { ModelRange } from "./ModelRange";
import styles from "./CatalogBrowser.module.css";

type Loaded = Showcase & { key: string; page: number };

const fieldsOf = (facets: Facet[]): CatalogField[] =>
  facets.map((f) => ({ key: f.key, label: f.label, kind: f.kind, unit: f.kind === "range" ? f.unit : (f.unit ?? ""), column: false, filter: true }));

// Запрос витрины: на бэк по /api/series/ (nginx / rewrites), в демо — те же данные из src/data (грузим только там)
async function fetchShowcase(category: string, query: CatalogQuery, signal: AbortSignal): Promise<Showcase> {
  if (process.env.NEXT_PUBLIC_DEMO === "1") {
    const { demoShowcases } = await import("@/data/catalog-demo");
    return demoShowcases(category, query);
  }
  const q = `category=${encodeURIComponent(category)}&${serializeCatalogQuery(query)}`;
  const response = await fetch(`/api/series/?${q}`, { signal });
  if (!response.ok) throw new Error(String(response.status));
  return mapShowcase((await response.json()) as ApiShowcase);
}

const sizes = "(max-width: 767px) 50vw, (max-width: 1023px) 33vw, 25vw";

// Список с фильтрами. Состояние — в адресе: ссылку с фильтрами можно отправить менеджеру.
export function CatalogBrowser({ category, initial, brands }: { category: Category; initial: Showcase; brands: Brand[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState<Loaded>({ ...initial, key: "", page: 1 });
  const [busy, setBusy] = useState(false);
  const [moreFailed, setMoreFailed] = useState(false);
  const moreController = useRef<AbortController | null>(null);

  // «Показать ещё» живёт в состоянии, в адрес page не попадает
  const key = useMemo(() => {
    const p = new URLSearchParams(params.toString());
    p.delete("page");
    return p.toString();
  }, [params]);
  const query = useMemo(() => parseCatalogQuery(new URLSearchParams(key), fieldsOf(loaded.facets)), [key, loaded.facets]);
  const brandNames = useMemo(() => Object.fromEntries(brands.map((b) => [b.slug, b.name])), [brands]);

  // Страница меняется только вместе с адресом: старый список остаётся, пока не пришёл новый
  useEffect(() => {
    if (key === loaded.key) return;
    moreController.current?.abort(); // «Показать ещё» от прежнего запроса не должен дописаться к новому списку
    const controller = new AbortController();
    fetchShowcase(category.slug, { ...query, page: 1 }, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setFailed(false);
        setMoreFailed(false);
        setLoaded({ ...data, key, page: 1 });
      })
      .catch((e) => !controller.signal.aborted && (console.error(e), setFailed(true)));
    return () => controller.abort();
  }, [key, loaded.key, category.slug, query]);

  const replace = (next: CatalogQuery) => {
    const q = serializeCatalogQuery({ ...next, page: undefined });
    router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
  };
  const toggleIn = (list: string[], value: string) => (list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  const toggleBrand = (slug: string) => {
    const next = toggleIn(csv(query.brand ?? ""), slug);
    replace({ ...query, brand: next.length ? next.join(",") : undefined });
  };
  const toggleColor = (code: string) => {
    replace({ ...query, color: query.color === code ? undefined : code });
  };
  const toggleList = (facetKey: string, value: string) => {
    replace({ ...query, lists: { ...query.lists, [facetKey]: toggleIn(query.lists[facetKey] ?? [], value) } });
  };
  const setRange = (facetKey: string, bound: 0 | 1, raw: string, limit: number | null) => {
    const n = raw.trim() === "" ? undefined : Number(raw);
    const [min, max] = query.ranges[facetKey] ?? [];
    const pair: [number?, number?] = bound === 0 ? [n, max] : [min, n];
    const ranges = { ...query.ranges };
    if (n === undefined || !Number.isFinite(n) || n === limit) pair[bound] = undefined;
    if (pair[0] === undefined && pair[1] === undefined) delete ranges[facetKey];
    else ranges[facetKey] = pair;
    replace({ ...query, ranges });
  };

  const more = async () => {
    moreController.current?.abort();
    const controller = new AbortController();
    moreController.current = controller;
    setBusy(true);
    setMoreFailed(false);
    try {
      const data = await fetchShowcase(category.slug, { ...query, page: loaded.page + 1 }, controller.signal);
      if (controller.signal.aborted) return;
      setLoaded((prev) => (prev.key === key ? { ...prev, results: [...prev.results, ...data.results], count: data.count, page: prev.page + 1 } : prev));
    } catch (e) {
      if (controller.signal.aborted) return;
      console.error(e);
      setMoreFailed(true);
    } finally {
      if (moreController.current === controller) setBusy(false);
    }
  };

  const selectedBrands = csv(query.brand ?? "");
  const selectedColors = csv(query.color ?? "");
  const active =
    selectedBrands.length + selectedColors.length + Object.keys(query.ranges).length + Object.values(query.lists).reduce((n, v) => n + v.length, 0);
  const brandLabel = (slug: string) => brandNames[slug] ?? slug;
  // Бренды с сериями в этой категории — по фасету brand первого экрана; нет фасета — все
  const brandFacet = initial.facets.find((f) => f.key === "brand");
  const brandsOfCategory = brandFacet && brandFacet.kind !== "range" ? brands.filter((b) => brandFacet.values.some((v) => v.value === b.slug)) : brands;
  const facets = loaded.facets.filter((f) => f.key !== "brand");
  const pending = key !== loaded.key;

  return (
    <div className={styles.layout}>
      <div className={styles.brands} role="group" aria-label="Бренды">
        {brandsOfCategory.map((b) => (
          <label key={b.slug} className={styles.option}>
            <input type="checkbox" checked={selectedBrands.includes(b.slug)} onChange={() => toggleBrand(b.slug)} className={styles.optionInput} />
            <span className={cx(styles.optionLabel, styles.brandChip)}>
              {/* eslint-disable-next-line @next/next/no-img-element -- логотипы брендов: обычный img по README */}
              {b.logo ? <img src={b.logo} alt="" className={styles.logo} /> : null}
              {brandLabel(b.slug)}
            </span>
          </label>
        ))}
      </div>

      {selectedBrands.length > 0 && loaded.modelRange.length > 0 && (
        <div className={styles.modelRange}>
          <ModelRange tiles={loaded.modelRange} category={category.slug} />
        </div>
      )}

      <div className={styles.toolbar}>
        <p className={styles.found} aria-live="polite">
          {plural(loaded.count, "вариант", "варианта", "вариантов")}
        </p>
        <Button variant="secondary" className={styles.filterToggle} aria-expanded={open} aria-controls="filters" onClick={() => setOpen((v) => !v)}>
          Фильтры{active ? ` · ${active}` : ""}
        </Button>
      </div>

      <aside id="filters" className={cx(styles.filters, open && styles.filtersOpen)} aria-label="Фильтры">
        {facets.map((f) => {
          if (f.kind === "range") {
            if (f.min == null || f.max == null) return null;
            const [min, max] = query.ranges[f.key] ?? [];
            return (
              <fieldset key={f.key} className={styles.group}>
                <legend className={styles.legend}>
                  {f.unit ? `${f.label}, ${f.unit}` : f.label}
                </legend>
                <div className={styles.rangeFields}>
                  <input
                    key={`${f.key}-min-${min ?? ""}`}
                    type="number"
                    inputMode="numeric"
                    className={styles.numberInput}
                    aria-label={`${f.label}: от`}
                    placeholder={String(f.min)}
                    min={f.min}
                    max={f.max}
                    defaultValue={min ?? ""}
                    onBlur={(e) => setRange(f.key, 0, e.target.value, f.min)}
                    onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                  />
                  <span aria-hidden="true">–</span>
                  <input
                    key={`${f.key}-max-${max ?? ""}`}
                    type="number"
                    inputMode="numeric"
                    className={styles.numberInput}
                    aria-label={`${f.label}: до`}
                    placeholder={String(f.max)}
                    min={f.min}
                    max={f.max}
                    defaultValue={max ?? ""}
                    onBlur={(e) => setRange(f.key, 1, e.target.value, f.max)}
                    onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                  />
                </div>
              </fieldset>
            );
          }
          if (f.kind === "colors") {
            const group: ColorGroup = {
              id: 0,
              name: f.label,
              percent: 0,
              isBase: true,
              anyRal: false,
              colors: f.values.map((v) => ({ code: v.value, name: v.label, hex: v.hex ?? "" })),
            };
            return (
              <fieldset key={f.key} className={styles.group}>
                <legend className={styles.legend}>{f.label}</legend>
                <ColorSwatches groups={[group]} selected={selectedColors[0]} onSelect={toggleColor} size="s" />
              </fieldset>
            );
          }
          return (
            <fieldset key={f.key} className={styles.group}>
              <legend className={styles.legend}>{f.label}</legend>
              <div className={styles.options}>
                {f.values.map(({ value, label, count }) => (
                  <label key={value} className={styles.option}>
                    <input
                      type="checkbox"
                      checked={query.lists[f.key]?.includes(value) ?? false}
                      onChange={() => toggleList(f.key, value)}
                      className={styles.optionInput}
                    />
                    <span className={styles.optionLabel}>
                      {label}
                      <span className={styles.optionCount}>{count}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          );
        })}
        {active > 0 && (
          <Button variant="ghost" onClick={() => router.replace(pathname, { scroll: false })}>
            Сбросить фильтры
          </Button>
        )}
      </aside>

      <div className={cx(styles.results, pending && styles.pending)} aria-busy={pending}>
        {failed && <p className={styles.error}>Не удалось обновить список. Попробуйте ещё раз или откройте страницу заново.</p>}
        {loaded.results.length ? (
          <>
            <ul className={styles.grid}>
              {loaded.results.map((card, i) => (
                <li key={`${card.series}-${card.heightMm}-${i}`}>
                  <ShowcaseCard card={card} category={category.slug} brand={brandNames[card.brand]} sizes={sizes} priority={i < 2} />
                </li>
              ))}
            </ul>
            {moreFailed && <p className={styles.error}>Не удалось загрузить остальные.</p>}
            {loaded.results.length < loaded.count && (
              <div className={styles.more}>
                <Button variant="secondary" onClick={more} disabled={busy}>
                  {busy ? "Загружаем…" : moreFailed ? "Повторить" : `Показать ещё (${Math.min(PAGE_SIZE_CARDS, loaded.count - loaded.results.length)})`}
                </Button>
              </div>
            )}
          </>
        ) : (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>По этим фильтрам ничего нет</p>
            <p>Ослабьте условия или опишите задачу менеджеру — подберём под размеры вручную.</p>
            <Button variant="secondary" onClick={() => router.replace(pathname, { scroll: false })}>
              Сбросить фильтры
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

// Без JS и во время гидрации — тот же первый экран без фильтров (его видят поисковики).
export function CatalogFallback({ category, initial, brands }: { category: Category; initial: Showcase; brands: Brand[] }) {
  const names = Object.fromEntries(brands.map((b) => [b.slug, b.name]));
  return (
    <div className={styles.layout}>
      <div className={styles.toolbar}>
        <p className={styles.found}>{plural(initial.count, "вариант", "варианта", "вариантов")}</p>
      </div>
      <div className={styles.filters} aria-hidden="true" />
      <div className={styles.results}>
        <ul className={styles.grid}>
          {initial.results.map((card, i) => (
            <li key={`${card.series}-${card.heightMm}-${i}`}>
              <ShowcaseCard card={card} category={category.slug} brand={names[card.brand]} sizes={sizes} priority={i < 2} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
