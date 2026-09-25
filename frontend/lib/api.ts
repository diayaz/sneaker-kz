// Клиент бэкенда (FastAPI). Вызывается только из серверных компонентов.
import { notFound } from "next/navigation";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
// Данные обновляются раз в сутки — 5 минут кэша достаточно и разгружают API.
const REVALIDATE_SECONDS = 300;

export type Store = { code: string; name: string; country: string; website: string };
export type Size = { size: string; width: string; available: boolean };

export type Estimate = {
  price_usd: number;
  sales_tax_usd: number;
  shipping_usd: number;
  customs_value_eur: number;
  duty_eur: number;
  price_kzt: number;
  sales_tax_kzt: number;
  shipping_kzt: number;
  duty_kzt: number;
  total_kzt: number;
};

type ProductBase = {
  id: number;
  style_code: string;
  brand: string;
  name: string;
  color: string | null;
  gender: "men" | "women" | null;
  image_url: string | null;
};

export type ProductCard = ProductBase & {
  best_price: number;
  best_old_price: number | null;
  discount_pct: number | null;
  best_store: Store;
  total_kzt: number;
  offers_count: number;
};

export type Offer = {
  id: number;
  store: Store;
  price: number;
  old_price: number | null;
  discount_pct: number | null;
  currency: string;
  in_stock: boolean;
  url: string;
  sizes: Size[];
  updated_at: string;
  estimate: Estimate;
};

export type ProductDetail = ProductBase & { offers: Offer[] };
export type ProductList = { items: ProductCard[]; total: number; page: number; page_size: number };
export type PricePoint = { day: string; price: number; old_price: number | null; in_stock: boolean };
export type PriceHistory = { product_id: number; series: { store: Store; points: PricePoint[] }[] };
export type Filters = {
  brands: { name: string; count: number }[];
  sizes: string[];
  price_min: number | null;
  price_max: number | null;
};
export type EstimateInfo = {
  usd_kzt_rate: number;
  eur_kzt_rate: number;
  rates_date: string;
  shipping_usd_per_kg: number;
  shoe_weight_kg: number;
  duty_free_limit_eur: number;
  duty_rate_pct: number;
  disclaimer: string;
};

export type Query = Record<string, string | string[] | undefined>;

async function get<T>(path: string, query: Query = {}): Promise<T> {
  const url = new URL(`/api/v1${path}`, API_URL);
  for (const [key, value] of Object.entries(query)) {
    for (const v of Array.isArray(value) ? value : [value]) {
      if (v !== undefined && v !== "") url.searchParams.append(key, v);
    }
  }
  const res = await fetch(url, { next: { revalidate: REVALIDATE_SECONDS } });
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`API ${res.status}: ${url.pathname}`);
  return res.json() as Promise<T>;
}

export const api = {
  products: (query: Query) => get<ProductList>("/products", query),
  product: (id: string) => get<ProductDetail>(`/products/${encodeURIComponent(id)}`),
  history: (id: string, days = 180) => get<PriceHistory>(`/products/${encodeURIComponent(id)}/history`, { days: String(days) }),
  filters: () => get<Filters>("/filters"),
  estimateInfo: () => get<EstimateInfo>("/estimate-info"),
};
