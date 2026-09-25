import type { Metadata } from "next";
import Link from "next/link";
import { OfferCard } from "@/components/OfferCard";
import { PriceChart } from "@/components/PriceChart";
import { ProductImage } from "@/components/ProductImage";
import { api } from "@/lib/api";
import { formatKzt } from "@/lib/format";
import { t } from "@/lib/i18n/ru";

export async function generateMetadata(props: PageProps<"/product/[id]">): Promise<Metadata> {
  const { id } = await props.params;
  const p = await api.product(id);
  return { title: `${p.brand} ${p.name}${p.color ? ` ${p.color}` : ""} (${p.style_code})` };
}

export default async function ProductPage(props: PageProps<"/product/[id]">) {
  const { id } = await props.params;
  const [p, history, info] = await Promise.all([api.product(id), api.history(id), api.estimateInfo()]);

  // API отдаёт предложения: сначала в наличии, затем по итоговой цене.
  const inStock = p.offers.filter((o) => o.in_stock);
  const best = inStock[0];
  const savings = inStock.length > 1 ? inStock[inStock.length - 1].estimate.total_kzt - best.estimate.total_kzt : 0;
  const historyDays = new Set(history.series.flatMap((s) => s.points.map((pt) => pt.day))).size;

  return (
    <div className="space-y-8">
      <Link href="/catalog" className="text-sm text-muted hover:text-foreground">
        {t.product.back}
      </Link>

      <section className="grid gap-6 md:grid-cols-2">
        <ProductImage src={p.image_url} alt={p.name} width={900} className="aspect-square w-full rounded-2xl border border-border p-4" />
        <div>
          <p className="text-sm font-medium tracking-wide text-muted uppercase">{p.brand}</p>
          <h1 className="mt-1 text-2xl leading-tight font-bold sm:text-3xl">{p.name}</h1>
          <dl className="mt-3 space-y-1 text-sm">
            {p.color && <Row label={t.product.color} value={p.color} />}
            <Row label={t.product.styleCode} value={p.style_code} mono />
            {p.gender && <Row label="" value={t.gender[p.gender]} />}
          </dl>

          {best && (
            <div className="mt-6 rounded-xl bg-accent-soft p-4">
              <p className="text-sm text-muted">{t.product.bestTotal}</p>
              <p className="tabular text-3xl font-extrabold text-accent">{formatKzt(best.estimate.total_kzt)}</p>
              <p className="text-sm">{t.product.at(best.store.name)}</p>
              {savings > 0 && <p className="mt-2 text-sm font-medium">{t.product.savings(formatKzt(savings))}</p>}
            </div>
          )}
          <p className="mt-4 text-xs leading-relaxed text-muted">{info.disclaimer}</p>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-bold">{t.product.offersTitle}</h2>
        <div className="grid gap-3 lg:grid-cols-2">
          {p.offers.map((o) => (
            <OfferCard key={o.id} offer={o} best={o.id === best?.id} weightKg={info.shoe_weight_kg} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-bold">{t.product.historyTitle}</h2>
        <div className="rounded-xl border border-border bg-surface p-4">
          <PriceChart history={history} />
          {historyDays < 3 && <p className="mt-3 text-xs text-muted">{t.product.historyShort}</p>}
        </div>
      </section>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex gap-2">
      {label && <dt className="text-muted">{label}:</dt>}
      <dd className={mono ? "font-mono" : ""}>{value}</dd>
    </div>
  );
}
