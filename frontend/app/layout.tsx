import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import { SearchBox } from "@/components/SearchBox";
import { t } from "@/lib/i18n/ru";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin", "cyrillic"] });

export const metadata: Metadata = {
  title: { default: `${t.siteName} — ${t.home.heroTitle}`, template: `%s — ${t.siteName}` },
  description: t.tagline,
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru" className={`${inter.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col font-sans">
        <header className="sticky top-0 z-20 border-b border-border bg-surface/95 backdrop-blur">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
            <Link href="/" className="text-lg font-extrabold tracking-tight">
              {t.siteName}
            </Link>
            <nav className="order-3 flex gap-4 text-sm text-muted sm:order-2">
              <Link href="/catalog" className="hover:text-foreground">{t.nav.catalog}</Link>
              <Link href="/catalog?gender=men" className="hover:text-foreground">{t.nav.men}</Link>
              <Link href="/catalog?gender=women" className="hover:text-foreground">{t.nav.women}</Link>
              <Link href="/catalog?on_sale=true&sort=discount" className="text-sale hover:opacity-80">{t.nav.sale}</Link>
            </nav>
            <div className="order-2 ml-auto w-full sm:order-3 sm:w-80">
              <SearchBox compact />
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>

        <footer className="border-t border-border bg-surface">
          <div className="mx-auto max-w-6xl space-y-2 px-4 py-6 text-xs leading-relaxed text-muted">
            <p>{t.footer.disclaimer}</p>
            <p>{t.footer.about}</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
