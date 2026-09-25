import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { CatalogFilters } from "@/components/CatalogFilters";
import { ProductGrid } from "@/components/ProductCard";
import { SortSelect } from "@/components/SortSelect";
import { api, type Query } from "@/lib/api";
import { t } from "@/lib/i18n/ru";

const PAGE_SIZE = 24;
const PASSTHROUGH = ["q", "brand", "size", "gender", "min_price", "max_price", "on_sale", "store", "sort", "page"];

export async function generateMetadata(props: PageProps<"/catalog">): Promise<Metadata> {
  const { q } = await props.searchParams;
  return { title: typeof q === "string" && q ? t.catalog.searchTitle(q) : t.catalog.title };
}

export default async function CatalogPage(props: PageProps<"/catalog">) {
  const searchParams = await props.searchParams;
  const query: Query = Object.fromEntries(PASSTHROUGH.map((k) => [k, searchParams[k]]));
  const [list, filters] = await Promise.all([api.products({ ...query, page_size: String(PAGE_SIZE) }), api.filters()]);

  const q = typeof searchParams.q === "string" ? searchParams.q : "";
  const pages = Math.max(1, Math.ceil(list.total / PAGE_SIZE));
  const hasFilters = PASSTHROUGH.some((k) => k !== "sort" && k !== "page" && searchParams[k]);

  return (
    <div className="grid gap-6 md:grid-cols-[220px_1fr]">
      <aside>
        {/* На телефоне фильтры свёрнуты, на десктопе — боковая колонка */}
        <details className="rounded-xl border border-border bg-surface p-4 md:hidden">
          <summary className="cursor-pointer font-semibold">{t.catalog.filters}</summary>
          <div className="mt-4">
            <Suspense>
              <CatalogFilters filters={filters} />
            </Suspense>
          </div>
        </details>
        <div className="hidden md:block">
          <Suspense>
            <CatalogFilters filters={filters} />
          </Suspense>
        </div>
      </aside>

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">{q ? t.catalog.searchTitle(q) : t.catalog.title}</h1>
            <p className="text-sm text-muted">
              {t.catalog.found(list.total)}
              {hasFilters && (
                <Link href="/catalog" className="ml-3 text-accent hover:underline">
                  {t.catalog.resetAll}
                </Link>
              )}
            </p>
          </div>
          <Suspense>
            <SortSelect />
          </Suspense>
        </div>

        {list.items.length ? (
          <ProductGrid products={list.items} />
        ) : (
          <p className="rounded-xl border border-border bg-surface p-8 text-center text-muted">{t.catalog.empty}</p>
        )}

        {pages > 1 && <Pagination page={list.page} pages={pages} searchParams={searchParams} />}
      </section>
    </div>
  );
}

function Pagination({ page, pages, searchParams }: { page: number; pages: number; searchParams: Query }) {
  const href = (p: number) => {
    const next = new URLSearchParams();
    for (const [k, v] of Object.entries(searchParams)) for (const x of [v].flat()) if (x) next.append(k, x);
    next.set("page", String(p));
    return `/catalog?${next.toString()}`;
  };
  const link = "rounded-md border border-border bg-surface px-3 py-1.5 hover:border-accent";
  return (
    <nav className="mt-8 flex items-center justify-center gap-3 text-sm" aria-label="pagination">
      {page > 1 && <Link href={href(page - 1)} className={link}>{t.catalog.prev}</Link>}
      <span className="text-muted">{t.catalog.page(page, pages)}</span>
      {page < pages && <Link href={href(page + 1)} className={link}>{t.catalog.next}</Link>}
    </nav>
  );
}
