// «Назад» и «Вперёд» браузера: страница, открытая из истории, возвращается туда, где её оставили, —
// на ту же прокрутку и с тем же числом карточек после «Показать ещё». Всё помним по адресу, пока открыта вкладка.

const positions = new Map<string, number>();
let popped: { url: string; y: number | undefined; at: number } | null = null;
const FRESH_MS = 5000; // после перехода по истории страница успевает загрузиться; дальше это уже не «возврат»
const PAGES_KEY = "catalog-pages:";

const here = () => window.location.pathname + window.location.search;

// Подписка на прокрутку и на переходы по истории; возвращает отписку
export function watchHistory(): () => void {
  const save = () => positions.set(here(), window.scrollY);
  // Позицию берём в момент перехода: потом новая, ещё короткая страница сдвинет прокрутку и перезапишет её
  const pop = () => {
    const url = here();
    popped = { url, y: positions.get(url), at: performance.now() };
  };
  window.addEventListener("scroll", save, { passive: true });
  window.addEventListener("popstate", pop);
  return () => {
    window.removeEventListener("scroll", save);
    window.removeEventListener("popstate", pop);
  };
}

// Эту страницу открыли кнопкой «Назад» / «Вперёд», а не ссылкой
export const cameBack = () => typeof window !== "undefined" && popped !== null && popped.url === here() && performance.now() - popped.at < FRESH_MS;

// Куда вернуть прокрутку; undefined — не возврат или позиции нет
export const backScroll = () => (cameBack() ? popped?.y : undefined);

// Сколько страниц каталога было открыто по этому адресу
export function savePages(url: string, pages: number) {
  try {
    sessionStorage.setItem(PAGES_KEY + url, String(pages));
  } catch {
    // нет хранилища — после «Назад» список начнётся с первой страницы
  }
}

export function savedPages(url: string): number {
  try {
    return Math.max(1, Number(sessionStorage.getItem(PAGES_KEY + url)) || 1);
  } catch {
    return 1;
  }
}
