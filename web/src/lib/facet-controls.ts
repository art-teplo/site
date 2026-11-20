import type { Facet } from '@/data/types';
import type { CatalogQuery } from './catalog-query';

export const toggleFacetValue = (selected: string[], value: string): string[] =>
  selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value];

// Константа подтверждается всей серией/категорией, а выбранное значение всегда можно снять.
export function splitFacetControls(facets: Facet[], query: Pick<CatalogQuery, 'lists' | 'ranges' | 'color'>): { controls: Facet[]; constants: Facet[] } {
  const controls: Facet[] = [];
  const constants: Facet[] = [];
  for (const facet of facets) {
    if (facet.kind === 'range') {
      const active = query.ranges[facet.key]?.some((value) => value !== undefined);
      if (!active && facet.total_values === 1 && !facet.has_unknown && facet.min != null && facet.min === facet.max) constants.push(facet);
      else if (active || (facet.min != null && facet.max != null)) controls.push(facet);
      continue;
    }
    const selected = facet.kind === 'colors' ? (query.color ?? '').split(',').filter(Boolean) : query.lists[facet.key] ?? [];
    const missing = selected.filter((value) => !facet.values.some((item) => item.value === value));
    const withSelected = missing.length ? { ...facet, values: [...facet.values, ...missing.map((value) => ({ value, label: value, count: 0 }))] } : facet;
    if (facet.kind === 'list' && facet.total_values === 1 && !facet.has_unknown && facet.values.length === 1 && !selected.length) constants.push(facet);
    else if (withSelected.values.length) controls.push(withSelected);
  }
  return { controls, constants };
}
