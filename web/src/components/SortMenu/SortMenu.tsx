"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { cx } from "@/lib/format";
import styles from "./SortMenu.module.css";

type Option<T extends string> = { value: T; label: string };
type Props<T extends string> = {
  label: string; // для экранного диктора: «Сортировка»
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
  className?: string;
};

// Выпадающий список в стиле сайта вместо системного <select>: тот раскрывается белым окном браузера.
// Клавиатура как у listbox: стрелки, Home/End, Enter/пробел — выбрать, Esc — закрыть.
export function SortMenu<T extends string>({ label, value, options, onChange, className }: Props<T>) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const id = useId();
  const current = options.find((o) => o.value === value) ?? options[0];

  // Клик мимо — закрыть
  useEffect(() => {
    if (!open) return;
    const close = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  useEffect(() => {
    if (open) list.current?.focus();
  }, [open]);

  const show = () => {
    setActive(Math.max(0, options.indexOf(current)));
    setOpen(true);
  };
  const pick = (i: number) => {
    setOpen(false);
    button.current?.focus();
    if (options[i].value !== value) onChange(options[i].value);
  };
  const onListKey = (e: KeyboardEvent) => {
    const last = options.length - 1;
    const move: Record<string, number> = { ArrowDown: Math.min(last, active + 1), ArrowUp: Math.max(0, active - 1), Home: 0, End: last };
    if (e.key in move) {
      e.preventDefault();
      setActive(move[e.key]);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      pick(active);
    } else if (e.key === "Escape" || e.key === "Tab") {
      setOpen(false);
      if (e.key === "Escape") button.current?.focus();
    }
  };

  return (
    <div ref={root} className={cx(styles.root, className)}>
      <button
        ref={button}
        type="button"
        className={styles.trigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-label={`${label}: ${current.label}`}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            show();
          }
        }}
      >
        {current.label}
        <svg className={cx(styles.chevron, open && styles.chevronOpen)} viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="m5 8 5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <ul
          ref={list}
          id={`${id}-list`}
          role="listbox"
          tabIndex={-1}
          aria-label={label}
          aria-activedescendant={`${id}-${active}`}
          className={styles.list}
          onKeyDown={onListKey}
        >
          {options.map((o, i) => (
            <li
              key={o.value}
              id={`${id}-${i}`}
              role="option"
              aria-selected={o.value === value}
              className={cx(styles.option, i === active && styles.optionActive)}
              onPointerEnter={() => setActive(i)}
              onClick={() => pick(i)}
            >
              {o.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
