import Link from "next/link";
import { ProductGrid } from "@/components/ProductCard";
import { SearchBox } from "@/components/SearchBox";
import { api } from "@/lib/api";
import { formatDate, formatRate } from "@/lib/format";
import { t } from "@/lib/i18n/ru";

// Рендер на запросе: данные берутся из API (с 5-минутным кэшем), сборка не зависит от запущенного бэкенда.
export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [popular, deals, filters, info] = await Promise.all([
    api.products({ sort: "popular", page_size: "8" }),
    api.products({ sort: "discount", on_sale: "true", page_size: "8" }),
    api.filters(),
    api.estimateInfo(),
  ]);

  return (
    <div className="space-y-12">
      <section className="rounded-2xl bg-surface px-5 py-8 sm:px-10 sm:py-12">
        <h1 className="max-w-2xl text-3xl leading-tight font-extrabold tracking-tight sm:text-4xl">{t.home.heroTitle}</h1>
        <p className="mt-3 max-w-2xl text-muted">{t.home.heroText}</p>
        <div className="mt-6 max-w-2xl">
          <SearchBox />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {filters.brands.slice(0, 8).map((b) => (
            <Link
              key={b.name}
              href={`/catalog?brand=${encodeURIComponent(b.name)}`}
              className="rounded-full border border-border px-3 py-1 text-sm hover:border-accent hover:text-accent"
            >
              {b.name}
            </Link>
          ))}
        </div>
        {info.rates_date && (
          <p className="mt-6 text-xs text-muted">
            {t.home.rates(
              formatDate(info.rates_date, { day: "numeric", month: "long" }),
              formatRate(info.usd_kzt_rate),
              formatRate(info.eur_kzt_rate),
            )}
          </p>
        )}
      </section>

      <Section title={t.home.popular} hint={t.home.popularHint} href="/catalog">
        <ProductGrid products={popular.items} />
      </Section>

      <Section title={t.home.deals} href="/catalog?on_sale=true&sort=discount">
        <ProductGrid products={deals.items} />
      </Section>

      <section>
        <h2 className="text-xl font-bold">{t.home.howTitle}</h2>
        <ol className="mt-4 grid gap-3 sm:grid-cols-3">
          {t.home.how.map(([title, text], i) => (
            <li key={title} className="rounded-xl border border-border bg-surface p-4">
              <p className="text-sm font-bold text-accent">{i + 1}</p>
              <p className="mt-1 font-semibold">{title}</p>
              <p className="mt-1 text-sm text-muted">{text}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function Section({ title, hint, href, children }: { title: string; hint?: string; href: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold">{title}</h2>
          {hint && <p className="text-sm text-muted">{hint}</p>}
        </div>
        <Link href={href} className="shrink-0 text-sm font-medium text-accent hover:underline">
          {t.home.allCatalog}
        </Link>
      </div>
      {children}
    </section>
  );
}
