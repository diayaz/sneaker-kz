import type { Offer } from "@/lib/api";
import { formatDate, formatKzt, formatUsd } from "@/lib/format";
import { t } from "@/lib/i18n/ru";

export function OfferCard({ offer: o, best, weightKg }: { offer: Offer; best: boolean; weightKg: number }) {
  const e = o.estimate;
  const available = o.sizes.filter((s) => s.available);

  return (
    <article className={`rounded-xl border bg-surface p-4 ${best ? "border-accent ring-1 ring-accent" : "border-border"} ${o.in_stock ? "" : "opacity-60"}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{o.store.name}</h3>
          <p className={`text-xs ${o.in_stock ? "text-accent" : "text-muted"}`}>{o.in_stock ? t.product.inStock : t.product.outOfStock}</p>
        </div>
        <div className="text-right">
          <p className="tabular text-sm">
            {o.old_price && <span className="mr-1.5 text-xs text-muted line-through">{formatUsd(o.old_price)}</span>}
            <span className="font-semibold">{formatUsd(o.price)}</span>
            {o.discount_pct ? <span className="ml-1.5 text-xs font-bold text-sale">−{o.discount_pct}%</span> : null}
          </p>
          <p className="tabular text-xl font-bold">{formatKzt(e.total_kzt)}</p>
          <p className="text-xs text-muted">{t.card.toDoor}</p>
        </div>
      </div>

      {o.in_stock && (
        <div className="mt-3">
          <p className="mb-1.5 text-xs text-muted">{t.product.sizesInStock}</p>
          {available.length ? (
            <ul className="flex flex-wrap gap-1.5">
              {available.map((s) => (
                <li key={`${s.size}-${s.width}`} className="tabular rounded-md border border-border px-2 py-0.5 text-xs">
                  {s.size}
                  {s.width && <span className="text-muted"> {s.width}</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted">{t.product.noSizes}</p>
          )}
        </div>
      )}

      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-accent">{t.product.breakdown}</summary>
        <dl className="tabular mt-2 space-y-1">
          <Line label={t.product.lines.price} usd={e.price_usd} kzt={e.price_kzt} />
          {e.sales_tax_usd > 0 && <Line label={t.product.lines.tax} usd={e.sales_tax_usd} kzt={e.sales_tax_kzt} />}
          <Line label={t.product.lines.shipping(String(weightKg).replace(".", ","))} usd={e.shipping_usd} kzt={e.shipping_kzt} />
          {e.duty_eur > 0 ? (
            <Line label={t.product.lines.duty} eur={e.duty_eur} kzt={e.duty_kzt} />
          ) : (
            <Line label={t.product.lines.dutyNone} kzt={0} />
          )}
          <div className="flex justify-between border-t border-border pt-1 font-semibold">
            <dt>{t.product.lines.total}</dt>
            <dd>{formatKzt(e.total_kzt)}</dd>
          </div>
        </dl>
      </details>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted">{t.product.updated(formatDate(o.updated_at, { day: "numeric", month: "long" }))}</p>
        <a
          href={o.url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className={`rounded-lg px-4 py-2 text-sm font-semibold ${best ? "bg-accent text-on-accent hover:opacity-90" : "border border-border hover:border-accent"}`}
        >
          {t.product.goToStore} ↗
        </a>
      </div>
    </article>
  );
}

function Line({ label, usd, eur, kzt }: { label: string; usd?: number; eur?: number; kzt: number }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted">{label}</dt>
      <dd>
        {usd !== undefined && <span className="mr-2 text-xs text-muted">{formatUsd(usd)}</span>}
        {eur !== undefined && <span className="mr-2 text-xs text-muted">€{eur.toLocaleString("ru-RU")}</span>}
        {formatKzt(kzt)}
      </dd>
    </div>
  );
}
