import Link from "next/link";
import type { ProductCard as Product } from "@/lib/api";
import { formatKzt, formatUsd } from "@/lib/format";
import { t } from "@/lib/i18n/ru";
import { ProductImage } from "./ProductImage";

export function ProductCard({ product: p }: { product: Product }) {
  return (
    <Link
      href={`/product/${p.id}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-border bg-surface transition hover:border-accent hover:shadow-sm"
    >
      <div className="relative">
        <ProductImage src={p.image_url} alt={p.name} width={400} className="aspect-square w-full p-2" />
        {p.discount_pct ? (
          <span className="absolute top-2 left-2 rounded-md bg-sale px-1.5 py-0.5 text-xs font-bold text-on-accent">
            −{p.discount_pct}%
          </span>
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <p className="text-xs font-medium tracking-wide text-muted uppercase">{p.brand}</p>
        <h3 className="line-clamp-2 text-sm leading-snug font-medium group-hover:text-accent">{p.name}</h3>
        {p.color && <p className="line-clamp-1 text-xs text-muted">{p.color}</p>}
        <div className="mt-auto pt-2">
          <p className="tabular text-sm">
            <span className="font-semibold">{formatUsd(p.best_price)}</span>
            {p.best_old_price && <span className="ml-1.5 text-xs text-muted line-through">{formatUsd(p.best_old_price)}</span>}
          </p>
          <p className="tabular text-base font-bold text-accent">
            {p.offers_count > 1 && <span className="mr-1 text-xs font-normal text-muted">{t.card.from}</span>}
            {formatKzt(p.total_kzt)}
            <span className="ml-1 text-xs font-normal text-muted">{t.card.toDoor}</span>
          </p>
          <p className="mt-0.5 text-xs text-muted">
            {p.offers_count > 1 ? t.card.inStores(p.offers_count) : p.best_store.name}
          </p>
        </div>
      </div>
    </Link>
  );
}

export function ProductGrid({ products }: { products: Product[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {products.map((p) => (
        <ProductCard key={p.id} product={p} />
      ))}
    </div>
  );
}
