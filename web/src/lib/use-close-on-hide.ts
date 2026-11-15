"use client";

import { useLayoutEffect, type RefObject } from "react";
import { getLenis } from "@/components/SmoothScroll/SmoothScroll";

// Окно (<dialog>) на странице, которую спрятали: Next (Cache Components) при переходе, в том числе кнопкой «Назад»,
// не убирает прошлую страницу, а скрывает её через <Activity>. Открытое модальное окно там оставило бы запрет прокрутки
// и сделало бы новую страницу некликабельной. Cleanup эффекта React вызывает и при скрытии, и при размонтировании:
// закрываем окно и возвращаем прокрутку (onClose окна сбросит его состояние).
export function useCloseOnHide(ref: RefObject<HTMLDialogElement | null>) {
  useLayoutEffect(() => {
    const dialog = ref.current;
    return () => {
      if (!dialog?.open) return;
      dialog.close();
      getLenis()?.start();
      document.documentElement.style.overflow = "";
    };
  }, [ref]);
}
