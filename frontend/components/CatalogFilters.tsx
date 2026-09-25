"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";
import type { Filters } from "@/lib/api";
import { t } from "@/lib/i18n/ru";

const BRANDS_COLLAPSED = 10;
const isShoeSize = (s: string) => /^\d{1,2}(\.5)?$/.test(s) && Number(s) >= 3 && Number(s) <= 16;

export function CatalogFilters({ filters }: { filters: Filters }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [showAllBrands, setShowAllBrands] = useState(false);

  const selectedBrands = params.getAll("brand");
  const selectedSizes = params.getAll("size");

  function update(mutate: (p: URLSearchParams) => void) {
    const next = new URLSearchParams(params.toString());
    mutate(next);
    next.delete("page"); // при смене фильтров — на первую страницу
    startTransition(() => router.push(`${pathname}?${next.toString()}`, { scroll: false }));
  }

  function toggle(key: string, value: string) {
    update((p) => {
      const values = p.getAll(key);
      p.delete(key);
      for (const v of values.includes(value) ? values.filter((x) => x !== value) : [...values, value]) p.append(key, v);
    });
  }

  function setValue(key: string, value: string | null) {
    update((p) => (value ? p.set(key, value) : p.delete(key)));
  }

  const brands = showAllBrands ? filters.brands : filters.brands.slice(0, BRANDS_COLLAPSED);
  // Выбранные бренды всегда видны, даже если свёрнуты.
  const hiddenSelected = filters.brands.filter((b) => selectedBrands.includes(b.name) && !brands.includes(b));

  return (
    <div className={`space-y-6 text-sm transition-opacity ${pending ? "opacity-60" : ""}`}>
      <Group title={t.catalog.gender}>
        <div className="flex flex-wrap gap-2">
          {[
            [null, t.catalog.genderAll],
            ["men", t.gender.men],
            ["women", t.gender.women],
          ].map(([value, label]) => (
            <Chip key={label} active={params.get("gender") === value} onClick={() => setValue("gender", value)}>
              {label}
            </Chip>
          ))}
        </div>
      </Group>

      <Group title={t.catalog.size}>
        <div className="grid grid-cols-5 gap-1.5">
          {filters.sizes.filter(isShoeSize).map((s) => (
            <Chip key={s} active={selectedSizes.includes(s)} onClick={() => toggle("size", s)} center>
              {s}
            </Chip>
          ))}
        </div>
      </Group>

      <Group title={t.catalog.price}>
        <PriceRange
          key={`${params.get("min_price")}-${params.get("max_price")}`}
          min={params.get("min_price") ?? ""}
          max={params.get("max_price") ?? ""}
          onApply={(min, max) =>
            update((p) => {
              if (min) p.set("min_price", min);
              else p.delete("min_price");
              if (max) p.set("max_price", max);
              else p.delete("max_price");
            })
          }
        />
      </Group>

      <label className="flex cursor-pointer items-center gap-2">
        <input
          type="checkbox"
          checked={params.get("on_sale") === "true"}
          onChange={(e) => setValue("on_sale", e.target.checked ? "true" : null)}
          className="size-4 accent-[var(--accent)]"
        />
        {t.catalog.onSale}
      </label>

      <Group title={t.catalog.brand}>
        <ul className="space-y-1.5">
          {[...hiddenSelected, ...brands].map((b) => (
            <li key={b.name}>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedBrands.includes(b.name)}
                  onChange={() => toggle("brand", b.name)}
                  className="size-4 accent-[var(--accent)]"
                />
                <span className="flex-1">{b.name}</span>
                <span className="tabular text-xs text-muted">{b.count}</span>
              </label>
            </li>
          ))}
        </ul>
        {filters.brands.length > BRANDS_COLLAPSED && (
          <button type="button" onClick={() => setShowAllBrands(!showAllBrands)} className="mt-2 text-accent hover:underline">
            {showAllBrands ? t.catalog.showLess : t.catalog.showMore(filters.brands.length - BRANDS_COLLAPSED)}
          </button>
        )}
      </Group>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset>
      <legend className="mb-2 font-semibold">{title}</legend>
      {children}
    </fieldset>
  );
}

function Chip({ active, onClick, center, children }: { active: boolean; onClick: () => void; center?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`rounded-md border px-2.5 py-1 ${center ? "text-center" : ""} ${
        active ? "border-accent bg-accent-soft font-semibold text-accent" : "border-border hover:border-foreground/40"
      }`}
    >
      {children}
    </button>
  );
}

function PriceRange({ min, max, onApply }: { min: string; max: string; onApply: (min: string, max: string) => void }) {
  const [lo, setLo] = useState(min);
  const [hi, setHi] = useState(max);
  const apply = () => (lo !== min || hi !== max) && onApply(lo, hi);
  const input = "w-full rounded-md border border-border bg-background px-2 py-1.5 outline-none focus:border-accent";
  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        apply();
      }}
    >
      <input className={input} inputMode="numeric" placeholder={t.catalog.priceFrom} value={lo} onChange={(e) => setLo(e.target.value.replace(/\D/g, ""))} onBlur={apply} />
      <span className="text-muted">—</span>
      <input className={input} inputMode="numeric" placeholder={t.catalog.priceTo} value={hi} onChange={(e) => setHi(e.target.value.replace(/\D/g, ""))} onBlur={apply} />
    </form>
  );
}
