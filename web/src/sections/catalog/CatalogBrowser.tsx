"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/Button/Button";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import { ShowcaseCard } from "@/components/ShowcaseCard/ShowcaseCard";
import { SortMenu } from "@/components/SortMenu/SortMenu";
import { mapShowcase, type ApiShowcase, type Showcase } from "@/data/catalog-map";
import type { Brand, CatalogField, Category, Facet } from "@/data/types";
import { catalogKey, csv, parseCatalogQuery, serializeCatalogQuery, type CatalogQuery, type Sort, PAGE_SIZE_CARDS, SORT_LABEL } from "@/lib/catalog-query";
import { facetValueLabel } from "@/lib/facet-labels";
import { cx, plural } from "@/lib/format";
import { colorLabel } from "@/lib/series-color";
import { FilterGroup } from "./FilterGroup";
import { RangeFilter } from "./RangeFilter";
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

// Сколько групп фильтров видно сразу; остальные — под «Ещё фильтры»
const VISIBLE_GROUPS = 5;

const sizes = "(max-width: 767px) 50vw, (max-width: 1023px) 33vw, 25vw";

// Список с фильтрами. Состояние — в адресе: ссылку с фильтрами можно отправить менеджеру.
export function CatalogBrowser({ category, initial, brands }: { category: Category; initial: Showcase; brands: Brand[] }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const [open, setOpen] = useState(false);
  const [allFilters, setAllFilters] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState<Loaded>({ ...initial, key: "", page: 1 });
  const [busy, setBusy] = useState(false);
  const [moreFailed, setMoreFailed] = useState(false);
  const moreController = useRef<AbortController | null>(null);

  // «Показать ещё» живёт в состоянии, в адрес page не попадает
  const key = useMemo(() => catalogKey(params), [params]);
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

  // Адрес меняем в истории без перехода: useSearchParams его подхватывает, сервер страницу не пересобирает
  // (список браузер грузит сам)
  const go = (url: string) => window.history.replaceState(null, "", url);
  const replace = (next: CatalogQuery) => {
    const q = serializeCatalogQuery({ ...next, page: undefined });
    go(q ? `${pathname}?${q}` : pathname);
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
  const setRange = (facetKey: string, pair: [number?, number?]) => {
    const ranges = { ...query.ranges };
    if (pair[0] === undefined && pair[1] === undefined) delete ranges[facetKey];
    else ranges[facetKey] = pair;
    replace({ ...query, ranges });
  };
  const setSort = (value: string) => replace({ ...query, sort: value === "price" || value === "-price" ? (value as Sort) : undefined });
  // Сброс фильтров порядок не трогает
  const reset = () => replace({ ranges: {}, lists: {}, sort: query.sort });
  const setType = (slug: string | undefined) => replace({ ...query, type: slug });

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
    selectedBrands.length + selectedColors.length + Object.keys(query.ranges).length + (query.type ? 1 : 0) + Object.values(query.lists).reduce((n, v) => n + v.length, 0);
  const brandLabel = (slug: string) => brandNames[slug] ?? slug;
  // Бренды с сериями в этой категории — по фасету brand первого экрана; нет фасета — все
  const brandFacet = initial.facets.find((f) => f.key === "brand");
  const brandsOfCategory = brandFacet && brandFacet.kind !== "range" ? brands.filter((b) => brandFacet.values.some((v) => v.value === b.slug)) : brands;
  const types = category.types ?? [];
  // Без значений и с min == max выбирать нечего; тип и бренд — отдельными блоками над списком
  const facets = loaded.facets.filter((f) => {
    if (f.key === "brand" || f.key === "type") return false;
    if (f.kind === "range") return f.min != null && f.max != null && f.min !== f.max;
    return f.values.length > 0;
  });
  const pending = key !== loaded.key;
  // Открыли ссылку с фильтрами: на руках ещё первый экран без них — его не показываем, ждём свой список
  const awaiting = pending && loaded.key === "" && !failed;
  const singleBrand = selectedBrands.length === 1 ? brands.find((b) => b.slug === selectedBrands[0]) : undefined;
  // Группы фильтров: первые VISIBLE_GROUPS видны, остальные под кнопкой; группа с выбранным значением видна всегда
  const selectedIn = (f: Facet): number => {
    if (f.kind === "range") return query.ranges[f.key] ? 1 : 0;
    if (f.kind === "colors") return selectedColors.length;
    return query.lists[f.key]?.length ?? 0;
  };
  const shown = facets.filter((f, i) => allFilters || i < VISIBLE_GROUPS || selectedIn(f) > 0);
  const hiddenCount = facets.length - shown.length;

  return (
    <div className={styles.layout}>
      {types.length > 0 && (
        <nav className={styles.types} aria-label="Тип">
          {[{ slug: "", name: `Все ${category.name.toLowerCase()}`, image: category.image, seriesCount: category.seriesCount }, ...types].map((t) => {
            const on = (query.type ?? "") === t.slug;
            const all = t.slug === "";
            return (
              <button key={t.slug} type="button" className={cx(styles.typeTile, on && styles.typeTileOn)} aria-pressed={on} onClick={() => setType(t.slug || undefined)}>
                <span className={cx(styles.typeMedia, all && styles.typeMediaAll)}>
                  {t.image && <Picture image={t.image} fit={all ? "contain" : "cover"} sizes="160px" className={styles.typeImg} />}
                </span>
                <span className={styles.typeName}>{t.name}</span>
                <span className={styles.typeCount}>{t.seriesCount > 0 ? plural(t.seriesCount, "модель", "модели", "моделей") : "скоро"}</span>
              </button>
            );
          })}
        </nav>
      )}

      {brandsOfCategory.length > 0 && (
        <div className={styles.brands} role="group" aria-label="Бренды">
          {brandsOfCategory.map((b) => (
            <label key={b.slug} className={styles.option}>
              <input type="checkbox" checked={selectedBrands.includes(b.slug)} onChange={() => toggleBrand(b.slug)} className={styles.optionInput} />
              <span className={styles.brandCard}>
                {b.logo ? (
                  // eslint-disable-next-line @next/next/no-img-element -- логотипы брендов: обычный img по README
                  <img src={b.logo} alt={brandLabel(b.slug)} className={styles.logo} />
                ) : (
                  <span className={styles.brandName}>{brandLabel(b.slug)}</span>
                )}
              </span>
            </label>
          ))}
        </div>
      )}

      {singleBrand && (
        <div className={styles.brandBar}>
          <p className={styles.brandBarFacts}>
            {[
              singleBrand.name,
              singleBrand.country,
              singleBrand.warrantyYears ? `гарантия до ${plural(singleBrand.warrantyYears, "год", "года", "лет")}` : "",
            ]
              .filter(Boolean)
              .map((fact) => (
                <span key={fact}>{fact}</span>
              ))}
          </p>
        </div>
      )}

      <div className={styles.toolbar}>
        <p className={styles.found} aria-live="polite">
          {awaiting ? "Подбираем…" : plural(loaded.count, "вариант", "варианта", "вариантов")}
        </p>
        <SortMenu
          label="Сортировка"
          className={styles.sortMenu}
          value={query.sort ?? ""}
          options={(Object.keys(SORT_LABEL) as ("" | Sort)[]).map((v) => ({ value: v, label: SORT_LABEL[v] }))}
          onChange={setSort}
        />
        <Button variant="secondary" className={styles.filterToggle} aria-expanded={open} aria-controls="filters" onClick={() => setOpen((v) => !v)}>
          Фильтры{active ? ` · ${active}` : ""}
        </Button>
      </div>

      <aside id="filters" className={cx(styles.filters, open && styles.filtersOpen)} aria-label="Фильтры">
        {shown.map((f) => {
          if (f.kind === "range") {
            const [min, max] = query.ranges[f.key] ?? [];
            return (
              <FilterGroup key={f.key} title={f.unit ? `${f.label}, ${f.unit}` : f.label} defaultOpen selected={min !== undefined || max !== undefined ? 1 : 0}>
                <RangeFilter label={f.label} unit={f.unit} min={f.min as number} max={f.max as number} value={[min, max]} onApply={(pair) => setRange(f.key, pair)} />
              </FilterGroup>
            );
          }
          if (f.kind === "colors") {
            return (
              <FilterGroup key={f.key} title={f.label} defaultOpen={false} selected={selectedColors.length}>
                <div className={styles.swatches}>
                  {f.values.map((v) => (
                    <button
                      key={v.value}
                      type="button"
                      className={styles.swatch}
                      style={{ background: v.hex }}
                      title={colorLabel(v.label, v.value)}
                      aria-label={colorLabel(v.label, v.value)}
                      aria-pressed={selectedColors.includes(v.value)}
                      onClick={() => toggleColor(v.value)}
                    />
                  ))}
                </div>
              </FilterGroup>
            );
          }
          return (
            <FilterGroup key={f.key} title={f.label} defaultOpen={false} selected={query.lists[f.key]?.length ?? 0}>
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
                      {facetValueLabel(label, value)}
                      <span className={styles.optionCount}>{count}</span>
                    </span>
                  </label>
                ))}
              </div>
            </FilterGroup>
          );
        })}
        {(hiddenCount > 0 || allFilters) && facets.length > VISIBLE_GROUPS && (
          <Button variant="ghost" aria-expanded={allFilters} onClick={() => setAllFilters((v) => !v)}>
            {allFilters ? "Свернуть" : `Ещё фильтры (${hiddenCount})`}
          </Button>
        )}
        {active > 0 && (
          <Button variant="ghost" onClick={reset}>
            Сбросить фильтры
          </Button>
        )}
      </aside>

      <div className={cx(styles.results, pending && styles.pending, awaiting && styles.awaiting)} aria-busy={pending}>
        {pending && <div className={styles.progress} role="progressbar" aria-label="Загружаем список"><span className={styles.progressBar} /></div>}
        {failed && <p className={styles.error}>Не удалось обновить список. Попробуйте ещё раз или откройте страницу заново.</p>}
        {awaiting ? null : loaded.results.length ? (
          <>
            {/* key по запросу: новый список монтируется заново и появляется с анимацией блоков */}
            <ul key={loaded.key} className={styles.grid}>
              {loaded.results.map((card, i) => (
                <Reveal as="li" key={`${card.series}-${card.heightMm}-${i}`} index={i % 3}>
                  <ShowcaseCard card={card} category={category.slug} brand={brandNames[card.brand]} sizes={sizes} priority={i < 2} />
                </Reveal>
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
            <Button variant="secondary" onClick={reset}>
              Сбросить фильтры
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

// Без JS и во время гидрации — тот же первый экран без фильтров (его видят поисковики).
// Ссылку с фильтрами этот экран не знает: скрипт в <head> (CATALOG_QUERY_SCRIPT) ставит <html data-catalog-query>,
// и CSS вместо чужого списка показывает полосу загрузки
export function CatalogFallback({ category, initial, brands }: { category: Category; initial: Showcase; brands: Brand[] }) {
  const names = Object.fromEntries(brands.map((b) => [b.slug, b.name]));
  return (
    <div className={cx(styles.layout, styles.fallback)}>
      <div className={styles.toolbar}>
        <p className={styles.found}>{plural(initial.count, "вариант", "варианта", "вариантов")}</p>
      </div>
      <div className={styles.filters} aria-hidden="true" />
      <div className={styles.results}>
        <div className={cx(styles.progress, styles.fallbackProgress)} aria-hidden="true">
          <span className={styles.progressBar} />
        </div>
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
