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
} as const;

export type IconName = keyof typeof paths;

export function Icon({ name, ...props }: { name: IconName } & SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d={paths[name]} />
    </svg>
  );
}
