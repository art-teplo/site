import type { SVGProps } from "react";

// Линейные иконки сайта: сетка 24, линия 1.5, скруглённые концы — один рисунок на все блоки.
const paths = {
  // Нет проекта — план комнаты
  plan: "M3.5 3.5h17v17h-17z M3.5 12.5h6 M13 3.5v5.5 M13 12.5v8 M9.5 12.5v3",
  // Есть проект — лист чертежа
  project: "M6 2.5h8.5l4.5 4.5v14.5H6z M14.5 2.5V7H19 M9 12h7 M9 15.5h7 M9 19h4",
  // Есть спецификация — список позиций
  spec: "M10 6.5h10 M10 12h10 M10 17.5h10 M4 6.5l1.2 1.2L7.5 5.4 M4 12l1.2 1.2 2.3-2.3 M4 17.5l1.2 1.2 2.3-2.3",
  // Поиск — лупа
  search: "M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15z M16 16l4.5 4.5",
  // Закрыть — крест
  close: "M6 6l12 12 M18 6L6 18",
  // История поиска — часы
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 7.5V12l3 2",
  // Монтажная схема — радиатор с размерной линией и трубами подвода
  scheme: "M5 5.5h14v9H5z M8 5.5v9 M11 5.5v9 M13 5.5v9 M16 5.5v9 M5 18.5h14 M5 17v3 M19 17v3 M3 9h2 M3 11h2",
  // Сертификат — лист с печатью
  seal: "M5 2.5h11l3 3v9 M5 2.5v19h7 M8.5 7.5h7 M8.5 11h5 M17.5 21.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z M15.8 21l-.8 2.5 2.5-1 2.5 1-.8-2.5",
  // Скачать — стрелка в лоток
  download: "M12 3.5v11 M7.5 10l4.5 4.5 4.5-4.5 M4.5 16.5v3.5h15v-3.5",
  arrowUp: "M12 20V4 M5.5 10.5L12 4l6.5 6.5",
  chevronUp: "M6 15l6-6 6 6",
  chevronDown: "M6 9l6 6 6-6",
} as const;

export type IconName = keyof typeof paths;

export function Icon({ name, ...props }: { name: IconName } & SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d={paths[name]} />
    </svg>
  );
}
