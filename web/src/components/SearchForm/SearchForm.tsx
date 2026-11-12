"use client";

import { useRouter } from "next/navigation";
import { useId, type FormEvent } from "react";
import { Icon } from "@/components/Icon/Icon";
import { cx } from "@/lib/format";
import styles from "./SearchForm.module.css";

type Props = {
  defaultValue?: string;
  onSubmitted?: () => void; // шапка закрывает поле после перехода
  className?: string;
};

// Строка поиска по сайту: Enter или лупа ведут на /poisk?q=…
export function SearchForm({ defaultValue = "", onSubmitted, className }: Props) {
  const router = useRouter();
  const id = useId();

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const q = String(new FormData(e.currentTarget).get("q") ?? "").trim();
    if (!q) return;
    router.push(`/poisk?q=${encodeURIComponent(q)}`);
    onSubmitted?.();
  };

  return (
    <form role="search" className={cx(styles.form, className)} onSubmit={onSubmit}>
      <label htmlFor={id} className="visually-hidden">
        Поиск по каталогу
      </label>
      <input
        id={id}
        type="search"
        name="q"
        className={styles.input}
        defaultValue={defaultValue}
        placeholder="Название, бренд или артикул"
        autoComplete="off"
        enterKeyHint="search"
      />
      <button type="submit" className={styles.submit} aria-label="Найти">
        <Icon name="search" className={styles.icon} />
      </button>
    </form>
  );
}
