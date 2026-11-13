"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Icon } from "@/components/Icon/Icon";
import { Picture } from "@/components/Picture/Picture";
import { mapCard, type ApiCard } from "@/data/catalog-map";
import type { ShowcaseCard } from "@/data/types";
import { cx, formatPrice } from "@/lib/format";
import styles from "./SearchForm.module.css";

type Props = {
  defaultValue?: string;
  onSubmitted?: () => void; // шапка закрывает поле после перехода
  className?: string;
};

const HISTORY_KEY = "search-history";
const HISTORY_MAX = 5;
const SUGGEST_MIN = 2;
const SUGGEST_LIMIT = 5;
const DEBOUNCE_MS = 300;
// «Часто ищут» — пока список руками; появится статистика запросов — брать оттуда
const POPULAR = ["Guardo Retta", "Nova Siluet", "трубчатые радиаторы", "полотенцесушители", "внутрипольные конвекторы"];
const DEMO = process.env.NEXT_PUBLIC_DEMO === "1"; // без бэка подсказок нет — только история и «Часто ищут»

// История — только в браузере посетителя: на сервер не уходит. Хранилище бывает недоступно (приватный режим)
const readHistory = (): string[] => {
  try {
    const raw = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]");
    return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === "string").slice(0, HISTORY_MAX) : [];
  } catch {
    return [];
  }
};
const writeHistory = (items: string[]) => {
  try {
    if (items.length) localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
    else localStorage.removeItem(HISTORY_KEY);
  } catch {
    /* без истории — не страшно */
  }
};

type Option = { kind: "query"; text: string } | { kind: "card"; card: ShowcaseCard } | { kind: "all"; text: string };

const cardHref = (card: ShowcaseCard) => `/catalog/${card.category}/${card.series}${card.heightMm ? `?h=${card.heightMm}` : ""}`;

// Строка поиска по сайту. Под полем — история и «Часто ищут», с двух букв — подходящие модели
// (GET /api/search/?limit=5 после паузы в наборе). Enter или лупа ведут на /poisk?q=…
export function SearchForm({ defaultValue = "", onSubmitted, className }: Props) {
  const router = useRouter();
  const id = useId();
  const listId = `${id}-list`;
  const root = useRef<HTMLFormElement>(null);
  const [value, setValue] = useState(defaultValue);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  // На сервере localStorage нет — readHistory вернёт []; разметка не расходится: панель закрыта до фокуса
  const [history, setHistory] = useState<string[]>(readHistory);
  const [found, setFound] = useState<ShowcaseCard[]>([]);
  const [loading, setLoading] = useState(false);

  const query = value.trim();
  const typing = query.length >= SUGGEST_MIN;

  // Подсказки: после паузы в наборе, прошлый запрос отменяется
  useEffect(() => {
    if (!typing || DEMO) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ q: query, limit: String(SUGGEST_LIMIT) });
        const response = await fetch(`/api/search/?${params}`, { signal: controller.signal });
        const data: ApiCard[] = response.ok ? await response.json() : [];
        setFound(data.map(mapCard).filter((c) => c.category));
      } catch {
        if (!controller.signal.aborted) setFound([]);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, typing]);

  // Клик мимо — закрыть
  useEffect(() => {
    if (!open) return;
    const close = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  // Пока идёт новый запрос, видны подсказки прошлого — без мигания пустым списком
  const cards = typing && !DEMO ? found : [];
  const options: Option[] = typing
    ? [...cards.map((card) => ({ kind: "card" as const, card })), { kind: "all", text: query }]
    : [
        ...history.map((text) => ({ kind: "query" as const, text })),
        ...POPULAR.filter((p) => !history.includes(p)).map((text) => ({ kind: "query" as const, text })),
      ];

  // Запрос — в историю (свежий первым, без повторов)
  const remember = (q: string) => {
    const next = [q, ...history.filter((h) => h.toLowerCase() !== q.toLowerCase())].slice(0, HISTORY_MAX);
    setHistory(next);
    writeHistory(next);
  };

  const navigate = (href: string) => {
    setOpen(false);
    setActive(-1);
    router.push(href);
    onSubmitted?.();
  };

  const go = (text: string) => {
    const q = text.trim();
    if (!q) return;
    remember(q);
    setValue(q);
    navigate(`/poisk?q=${encodeURIComponent(q)}`);
  };

  const choose = (option: Option) => {
    if (option.kind === "card") {
      remember(query); // в историю — то, что человек набирал, а ведём сразу в карточку
      navigate(cardHref(option.card));
      return;
    }
    go(option.text);
  };

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const option = open ? options[active] : undefined;
    if (option) choose(option);
    else go(value);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) setOpen(true);
      const step = e.key === "ArrowDown" ? 1 : -1;
      // Круг из n + 1 положений: −1 (ничего не выбрано, Enter ищет набранное) и n подсказок
      const n = options.length;
      setActive((i) => (n ? ((i + 1 + step + n + 1) % (n + 1)) - 1 : -1));
    } else if (e.key === "Escape" && open) {
      e.preventDefault();
      setOpen(false);
      setActive(-1);
    }
  };

  const clearHistory = () => {
    setHistory([]);
    writeHistory([]);
  };

  const historyCount = typing ? 0 : history.length;
  const shown = open && (options.length > 0 || (typing && loading));
  const optionId = (i: number) => `${id}-option-${i}`;

  return (
    <form ref={root} role="search" className={cx(styles.form, className)} onSubmit={onSubmit}>
      <label htmlFor={id} className="visually-hidden">
        Поиск по каталогу
      </label>
      <input
        id={id}
        type="search"
        name="q"
        className={styles.input}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder="Название, бренд или артикул"
        autoComplete="off"
        enterKeyHint="search"
        role="combobox"
        aria-expanded={shown}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={shown && active >= 0 ? optionId(active) : undefined}
      />
      <button type="submit" className={styles.submit} aria-label="Найти">
        <Icon name="search" className={styles.icon} />
      </button>

      {shown && (
        <div className={styles.panel}>
          {!typing && historyCount > 0 && (
            <div className={styles.groupHead}>
              <span>История</span>
              <button type="button" className={styles.clear} onClick={clearHistory}>
                Очистить
              </button>
            </div>
          )}
          <ul id={listId} role="listbox" aria-label="Подсказки" className={styles.list}>
            {options.map((option, i) => (
              <li
                key={option.kind === "card" ? `c-${option.card.series}-${option.card.heightMm}` : `${option.kind}-${option.text}`}
                id={optionId(i)}
                role="option"
                aria-selected={i === active}
                className={cx(styles.option, i === active && styles.optionActive, option.kind === "all" && styles.optionAll)}
                // pointerdown, а не click: поле не успевает потерять фокус и закрыть список
                onPointerDown={(e) => {
                  e.preventDefault();
                  choose(option);
                }}
                onPointerEnter={() => setActive(i)}
              >
                {!typing && i === historyCount && <span className={styles.groupLabel}>Часто ищут</span>}
                {option.kind === "card" ? (
                  <span className={styles.card}>
                    <span className={styles.thumb}>{option.card.image && <Picture image={option.card.image} sizes="56px" />}</span>
                    <span className={styles.cardText}>
                      <span className={styles.cardName}>{option.card.name}</span>
                      {option.card.label && <span className={styles.cardMeta}>{option.card.label}</span>}
                    </span>
                    <span className={styles.cardPrice}>{option.card.priceFrom != null ? `от ${formatPrice(option.card.priceFrom)}` : "по запросу"}</span>
                  </span>
                ) : option.kind === "all" ? (
                  <span>Все результаты по запросу «{option.text}»</span>
                ) : (
                  <span className={styles.query}>
                    <Icon name={i < historyCount ? "clock" : "search"} className={styles.queryIcon} />
                    {option.text}
                  </span>
                )}
              </li>
            ))}
          </ul>
          {typing && loading && cards.length === 0 && <p className={styles.loading}>Ищем…</p>}
        </div>
      )}
    </form>
  );
}
