import { imageUrl } from "@/lib/format";

// Обычный <img>, а не next/image: картинки идут с CDN разных магазинов,
// и Shopify сам отдаёт уменьшенную версию по параметру width.
export function ProductImage({ src, alt, width, className = "" }: { src: string | null; alt: string; width: number; className?: string }) {
  const url = imageUrl(src, width);
  if (!url) return <div className={`bg-border/40 ${className}`} aria-hidden />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={alt} loading="lazy" className={`bg-white object-contain ${className}`} />;
}
