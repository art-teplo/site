"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { SortMenu } from "@/components/SortMenu/SortMenu";
import { SORT_LABEL, type Sort } from "@/lib/catalog-query";

// Сортировка выдачи поиска — тот же список, что в каталоге; значение живёт в адресе (?sort=)
export function SearchSort({ value, className }: { value: "" | Sort; className?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const onChange = (next: "" | Sort) => {
    const query = new URLSearchParams(params);
    if (next) query.set("sort", next);
    else query.delete("sort");
    router.replace(`${pathname}?${query}`, { scroll: false });
  };

  return (
    <SortMenu
      label="Сортировка"
      className={className}
      value={value}
      options={(Object.keys(SORT_LABEL) as ("" | Sort)[]).map((v) => ({ value: v, label: SORT_LABEL[v] }))}
      onChange={onChange}
    />
  );
}
