const kzt = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const usd = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
const rate = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const formatKzt = (value: number) => `${kzt.format(value)} ₸`;
export const formatUsd = (value: number) => `$${usd.format(value)}`;
export const formatEur = (value: number) => `€${usd.format(value)}`;
export const formatRate = (value: number) => rate.format(value);

export function formatDate(iso: string, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "long" }) {
  return new Date(iso).toLocaleDateString("ru-RU", opts);
}

// Shopify CDN умеет отдавать уменьшенную картинку по параметру width.
export function imageUrl(src: string | null, width: number): string | null {
  if (!src) return null;
  try {
    const url = new URL(src);
    if (url.hostname === "cdn.shopify.com") url.searchParams.set("width", String(width));
    return url.toString();
  } catch {
    return src;
  }
}
