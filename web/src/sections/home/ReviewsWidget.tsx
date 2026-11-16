"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/Button/Button";
import styles from "./Reviews.module.css";

type Props = { orgId: number; reviewsUrl: string };

// Виджет живёт на yandex.ru. Если у посетителя Яндекс не открывается (VPN, сеть, страна),
// в iframe вылезла бы ошибка браузера, а снаружи её не поймать — onload срабатывает и на ней.
// Поэтому сначала пробный запрос к тому же адресу: no-cors-ответ непрозрачный, но сетевая
// ошибка видна как reject. Ответил — ставим iframe, нет — спокойная заглушка со ссылкой (решение 178).
// Проверка стартует, когда до блока почти докрутили: как loading="lazy" у iframe раньше (решение 16)
const PROBE_TIMEOUT_MS = 8000;

export function ReviewsWidget({ orgId, reviewsUrl }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"idle" | "ok" | "failed">("idle");
  const src = `https://yandex.ru/maps-reviews-widget/${orgId}?comments`;

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let unmounted = false;

    // Не ответил за PROBE_TIMEOUT_MS — тоже заглушка: abort уводит запрос в catch
    const probe = () => {
      timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
      fetch(src, { mode: "no-cors", signal: controller.signal, credentials: "omit" })
        .then(() => !unmounted && setState("ok"))
        .catch(() => !unmounted && setState("failed"))
        .finally(() => clearTimeout(timer));
    };

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          observer.disconnect();
          probe();
        }
      },
      { rootMargin: "600px 0px" },
    );
    observer.observe(node);

    return () => {
      unmounted = true;
      observer.disconnect();
      clearTimeout(timer);
      controller.abort();
    };
  }, [src]);

  return (
    <div ref={ref} className={styles.widgetInner}>
      {state === "ok" && <iframe className={styles.frame} src={src} title="Отзывы о шоуруме на Яндекс.Картах" />}
      {state === "failed" && (
        <div className={styles.fallback} role="status">
          <p className={styles.fallbackTitle}>Отзывы с Яндекс.Карт сейчас не загрузились</p>
          <p className={styles.fallbackText}>
            Возможно, Яндекс недоступен в вашей сети. Отзывы можно прочитать прямо на Яндекс.Картах.
          </p>
          <Button href={reviewsUrl} target="_blank" rel="noopener noreferrer" variant="secondary" arrow>
            Открыть отзывы
          </Button>
        </div>
      )}
    </div>
  );
}
