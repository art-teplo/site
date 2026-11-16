import type { IconName } from "@/components/Icon/Icon";

// Вид документа серии по названию: подпись и иконка для вкладки «Файлы»
const KINDS: { test: RegExp; label: string; icon: IconName }[] = [
  { test: /паспорт/i, label: "Паспорт", icon: "project" },
  { test: /каталог/i, label: "Каталог", icon: "spec" },
  { test: /монтаж|схем/i, label: "Монтажная схема", icon: "scheme" },
  { test: /сертификат|декларац/i, label: "Сертификат", icon: "seal" },
  { test: /рекомендац|руководств|инструкц/i, label: "Рекомендации", icon: "spec" },
];

export function documentKind(title: string): { label: string; icon: IconName } {
  return KINDS.find((k) => k.test.test(title)) ?? { label: "Документ", icon: "project" };
}

// Расширение файла для подписи: «PDF»
export const fileType = (url: string) => (url.split("?")[0].split(".").pop() ?? "").toUpperCase() || "Файл";
