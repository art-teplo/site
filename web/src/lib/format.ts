const priceFormat = new Intl.NumberFormat("ru-BY", { maximumFractionDigits: 0 });

export const formatPrice = (byn: number) => `${priceFormat.format(byn)} BYN`;

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString("ru-BY", { day: "numeric", month: "long", year: "numeric" });

export const pad2 = (n: number) => String(n).padStart(2, "0");

export const cx = (...parts: Array<string | false | null | undefined>) => parts.filter(Boolean).join(" ");
