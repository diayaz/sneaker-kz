import type { PriceHistory } from "@/lib/api";
import { formatDate, formatUsd } from "@/lib/format";

const COLORS = ["#0f766e", "#c2410c", "#4f46e5", "#b45309", "#be185d", "#0369a1"];
const W = 640;
const H = 220;
const PAD = { top: 12, right: 12, bottom: 28, left: 52 };

// Линейный график цен по магазинам. Серверный SVG: без JS, подсказки — через <title>.
export function PriceChart({ history }: { history: PriceHistory }) {
  const series = history.series.filter((s) => s.points.length);
  const days = [...new Set(series.flatMap((s) => s.points.map((p) => p.day)))].sort();
  const prices = series.flatMap((s) => s.points.map((p) => p.price));
  if (!days.length) return null;

  const lo = Math.min(...prices);
  const hi = Math.max(...prices);
  const span = hi - lo || hi * 0.1 || 1;
  const yMin = Math.max(0, lo - span * 0.15);
  const yMax = hi + span * 0.15;

  const t0 = Date.parse(days[0]);
  const t1 = Date.parse(days[days.length - 1]);
  const x = (day: string) =>
    t1 === t0 ? (PAD.left + W - PAD.right) / 2 : PAD.left + ((Date.parse(day) - t0) / (t1 - t0)) * (W - PAD.left - PAD.right);
  const y = (price: number) => PAD.top + (1 - (price - yMin) / (yMax - yMin)) * (H - PAD.top - PAD.bottom);
  const ticks = [yMin, (yMin + yMax) / 2, yMax];

  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="График цен">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} stroke="var(--border)" />
            <text x={PAD.left - 6} y={y(v) + 4} textAnchor="end" fontSize="11" fill="var(--muted)">
              {formatUsd(Math.round(v))}
            </text>
          </g>
        ))}
        {[days[0], days[days.length - 1]].filter((d, i, a) => a.indexOf(d) === i).map((d) => (
          <text key={d} x={x(d)} y={H - 8} textAnchor={days.length === 1 ? "middle" : d === days[0] ? "start" : "end"} fontSize="11" fill="var(--muted)">
            {formatDate(d, { day: "numeric", month: "short" })}
          </text>
        ))}
        {series.map((s, i) => {
          const color = COLORS[i % COLORS.length];
          // Ступенчатая линия: цена держится до следующего замера.
          const path = s.points
            .map((p, j) => (j === 0 ? `M${x(p.day)},${y(p.price)}` : `H${x(p.day)}V${y(p.price)}`))
            .join("");
          return (
            <g key={s.store.code}>
              <path d={path} fill="none" stroke={color} strokeWidth="2" />
              {s.points.map((p) => (
                <circle key={p.day} cx={x(p.day)} cy={y(p.price)} r="3.5" fill={color}>
                  <title>{`${s.store.name}, ${formatDate(p.day)}: ${formatUsd(p.price)}`}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {series.map((s, i) => (
          <span key={s.store.code} className="flex items-center gap-1.5">
            <span className="inline-block size-2.5 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
            {s.store.name}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
