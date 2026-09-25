import Link from "next/link";
import { t } from "@/lib/i18n/ru";

export default function NotFound() {
  return (
    <div className="py-16 text-center">
      <p className="text-5xl font-extrabold text-muted">404</p>
      <p className="mt-4">{t.product.notFound}</p>
      <Link href="/catalog" className="mt-6 inline-block text-accent hover:underline">
        {t.product.back}
      </Link>
    </div>
  );
}
