"use client";

import { t } from "@/lib/i18n/ru";

// retry() заново запрашивает данные — нужно, если API был временно недоступен.
export default function Error({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <div className="py-16 text-center">
      <h1 className="text-xl font-bold">{t.error.title}</h1>
      <p className="mt-2 text-muted">{t.error.text}</p>
      <button type="button" onClick={() => retry()} className="mt-6 rounded-lg bg-accent px-5 py-2 font-semibold text-on-accent hover:opacity-90">
        {t.error.retry}
      </button>
    </div>
  );
}
