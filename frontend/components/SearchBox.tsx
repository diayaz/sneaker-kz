"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { t } from "@/lib/i18n/ru";

function SearchForm({ compact }: { compact?: boolean }) {
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        const query = q.trim();
        router.push(query ? `/catalog?q=${encodeURIComponent(query)}` : "/catalog");
      }}
      className="flex w-full gap-2"
    >
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t.search.placeholder}
        aria-label={t.search.placeholder}
        className={`min-w-0 flex-1 rounded-lg border border-border bg-background px-3 outline-none focus:border-accent ${
          compact ? "py-1.5 text-sm" : "py-3 text-base"
        }`}
      />
      {!compact && (
        <button type="submit" className="rounded-lg bg-accent px-5 font-semibold text-on-accent hover:opacity-90">
          {t.search.button}
        </button>
      )}
    </form>
  );
}

// useSearchParams требует Suspense-границы, иначе страница целиком уходит в клиентский рендер.
export function SearchBox(props: { compact?: boolean }) {
  return (
    <Suspense fallback={<div className={props.compact ? "h-8" : "h-12"} />}>
      <SearchForm {...props} />
    </Suspense>
  );
}
