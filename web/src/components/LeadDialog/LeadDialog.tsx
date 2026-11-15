"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { LeadForm } from "@/components/LeadForm/LeadForm";
import { getLenis } from "@/components/SmoothScroll/SmoothScroll";
import { useCloseOnHide } from "@/lib/use-close-on-hide";
import styles from "./LeadDialog.module.css";

type Props = {
  title: string;
  text: string;
  source: string; // откуда заявка — видно менеджеру
  context?: string; // что выбрал человек
  withFile?: boolean;
  className?: string; // стиль кнопки-триггера
  children: ReactNode; // содержимое кнопки
};

// Кнопка, которая открывает форму заявки поверх страницы (нативный <dialog>: Esc, фокус внутри окна).
// Не уводит человека вниз страницы, как ссылка на #lead.
export function LeadDialog({ title, text, source, context, withFile = true, className, children }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [open, setOpen] = useState(false);
  const titleId = useId();
  useCloseOnHide(ref);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open === dialog.open) return; // первый рендер и повторные вызовы — ничего не трогаем
    // Пока окно открыто, страница под ним не прокручивается
    if (open) {
      dialog.showModal();
      getLenis()?.stop();
      document.documentElement.style.overflow = "hidden";
    } else {
      dialog.close();
      getLenis()?.start();
      document.documentElement.style.overflow = "";
    }
  }, [open]);

  return (
    <>
      <button type="button" className={className} aria-haspopup="dialog" onClick={() => setOpen(true)}>
        {children}
      </button>
      {/* data-lenis-prevent: длинная форма на телефоне прокручивается внутри окна */}
      <dialog
        ref={ref}
        className={styles.dialog}
        aria-labelledby={titleId}
        onClose={() => {
          // Esc закрывает окно сам — возвращаем прокрутку странице
          getLenis()?.start();
          document.documentElement.style.overflow = "";
          setOpen(false);
        }}
        onClick={(e) => e.target === e.currentTarget && setOpen(false)}
        data-lenis-prevent
      >
        <div className={styles.panel} data-tone="white">
          <button type="button" className={styles.close} aria-label="Закрыть" onClick={() => setOpen(false)} />
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          <p className={styles.text}>{text}</p>
          {/* Форма монтируется заново при каждом открытии — после отправки окно снова пустое */}
          {open && <LeadForm source={source} context={context} withFile={withFile} />}
        </div>
      </dialog>
    </>
  );
}
