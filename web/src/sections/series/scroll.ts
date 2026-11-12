import { getLenis } from "@/components/SmoothScroll/SmoothScroll";

// Полоса вкладок липнет под шапкой: подъезжаем так, чтобы заголовок раздела оказался под ней
const stickyOffset = () => {
  const header = document.querySelector("header")?.getBoundingClientRect().height ?? 0;
  const tabs = document.getElementById("series-tabs")?.getBoundingClientRect().height ?? 0;
  return header + tabs;
};

export function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  const top = el.getBoundingClientRect().top + window.scrollY - stickyOffset();
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const lenis = getLenis();
  if (lenis) lenis.scrollTo(top, { immediate: reduced });
  else window.scrollTo({ top, behavior: reduced ? "auto" : "smooth" });
}

export const OPEN_FILTERS_EVENT = "series:open-filters";
const FLASH_MS = 1600;

// Чип «от — до» в шапке серии: раскрыть фильтры таблицы (на телефоне они свёрнуты), подъехать к полю
// этого размера и коротко его подсветить. Поля нет (размер не фильтруется) — просто к таблице вариантов
export function focusSeriesFilter(key: string) {
  window.dispatchEvent(new Event(OPEN_FILTERS_EVENT));
  // два кадра: React успевает раскрыть блок фильтров, и у поля появляются размеры
  requestAnimationFrame(() =>
    requestAnimationFrame(() => {
      const field = document.getElementById(`series-filter-${key}`);
      if (!field || !field.getClientRects().length) return scrollToSection("variants");
      scrollToSection(field.id);
      field.removeAttribute("data-flash");
      void field.getBoundingClientRect(); // перезапуск анимации при повторном клике
      field.setAttribute("data-flash", "");
      window.setTimeout(() => field.removeAttribute("data-flash"), FLASH_MS);
    }),
  );
}
