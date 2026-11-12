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
