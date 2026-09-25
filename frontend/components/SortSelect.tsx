"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { t } from "@/lib/i18n/ru";

export function SortSelect() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted">{t.catalog.sort}:</span>
      <select
        value={params.get("sort") ?? "popular"}
        onChange={(e) => {
          const next = new URLSearchParams(params.toString());
          next.set("sort", e.target.value);
          next.delete("page");
          router.push(`${pathname}?${next.toString()}`, { scroll: false });
        }}
        className="rounded-md border border-border bg-surface px-2 py-1.5"
      >
        {Object.entries(t.catalog.sorts).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}
