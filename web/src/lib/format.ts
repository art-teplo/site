const priceFormat = new Intl.NumberFormat("ru-BY", { maximumFractionDigits: 0 });

export const formatPrice = (byn: number) => `${priceFormat.format(byn)} BYN`;

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString("ru-BY", { day: "numeric", month: "long", year: "numeric" });

export const cx = (...parts: Array<string | false | null | undefined>) => parts.filter(Boolean).join(" ");

const pluralRules = new Intl.PluralRules("ru");
// «1 модель», «2 модели», «5 моделей»
export const plural = (n: number, one: string, few: string, many: string) =>
  `${n} ${{ one, few, many, other: few, zero: many, two: few }[pluralRules.select(n)]}`;
