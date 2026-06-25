"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Banknote, Download, FileSpreadsheet, FileText,
  ShoppingBag, TrendingUp, Users,
} from "lucide-react";
import { toast } from "sonner";
import { reportsApi } from "@/lib/api";

type Period = "today" | "week" | "month" | "custom";

/* ── SVG Line chart (courbe revenus journaliers) ── */
function LineChart({ points, color = "#111111" }: { points: { x: number; y: number }[]; color?: string }) {
  if (points.length < 2) return null;
  const W = 300; const H = 80;
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs); const maxX = Math.max(...xs);
  const minY = Math.min(...ys); const maxY = Math.max(...ys);
  const px = (x: number) => maxX === minX ? W / 2 : ((x - minX) / (maxX - minX)) * W;
  const py = (y: number) => maxY === minY ? H / 2 : H - ((y - minY) / (maxY - minY)) * H;
  const d  = points.map((p, i) => `${i === 0 ? "M" : "L"}${px(p.x)},${py(p.y)}`).join(" ");
  const fill = points.map((p, i) => `${i === 0 ? "M" : "L"}${px(p.x)},${py(p.y)}`).join(" ")
    + ` L${px(xs[xs.length - 1])},${H} L${px(xs[0])},${H} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 80 }}>
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.15" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fill} fill="url(#lg)" />
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {points.map((p, i) => (
        <circle key={i} cx={px(p.x)} cy={py(p.y)} r="3" fill={color} />
      ))}
    </svg>
  );
}

/* ── SVG Bar chart (volume horaire) ── */
function BarChart({ bars, color = "#111111" }: { bars: { label: string; value: number }[]; color?: string }) {
  if (!bars.length) return null;
  const W = 300; const H = 60;
  const maxV = Math.max(...bars.map((b) => b.value), 1);
  const barW = W / bars.length;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 60 }}>
      {bars.map((b, i) => {
        const bh = (b.value / maxV) * (H - 4);
        return (
          <rect
            key={i}
            x={i * barW + barW * 0.15}
            y={H - bh}
            width={barW * 0.7}
            height={bh}
            rx="3"
            fill={color}
            opacity={b.value === maxV ? 1 : 0.4}
          />
        );
      })}
    </svg>
  );
}

/* ── Carte stat ── */
function StatCard({ label, value, icon, iconBg, sub }: {
  label: string; value: string; icon: React.ReactNode; iconBg: string; sub?: string;
}) {
  return (
    <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: iconBg }}>
        {icon}
      </div>
      <p className="text-2xl font-semibold" style={{ color: "var(--tx-head)" }}>{value}</p>
      <p className="mt-0.5 text-sm" style={{ color: "var(--tx-muted)" }}>{label}</p>
      {sub && <p className="mt-1 text-xs opacity-70" style={{ color: "var(--tx-muted)" }}>{sub}</p>}
    </div>
  );
}

export default function MerchantReportsPage() {
  const [period, setPeriod]         = useState<Period>("month");
  const [startDate, setStartDate]   = useState("");
  const [endDate, setEndDate]       = useState("");
  const [isExporting, setIsExporting] = useState(false);

  const PERIODS: { value: Period; label: string }[] = [
    { value: "today", label: "Aujourd'hui" },
    { value: "week",  label: "Cette semaine" },
    { value: "month", label: "Ce mois" },
    { value: "custom", label: "Personnalisé" },
  ];

  const { data, isLoading } = useQuery({
    queryKey: ["reports", period, startDate, endDate],
    queryFn: () =>
      reportsApi.getSummary({
        period,
        date_from: period === "custom" ? startDate : undefined,
        date_to:   period === "custom" ? endDate   : undefined,
      }).then((r) => r.data),
    enabled: period !== "custom" || (!!startDate && !!endDate),
  });

  const handleExport = async (format: "csv" | "excel" | "pdf") => {
    setIsExporting(true);
    try {
      const response = await reportsApi.export(format, {
        period,
        date_from: period === "custom" ? startDate : undefined,
        date_to:   period === "custom" ? endDate   : undefined,
      });
      const mimes: Record<string, string> = {
        pdf:   "application/pdf",
        excel: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        csv:   "text/csv",
      };
      const exts: Record<string, string> = { pdf: "pdf", excel: "xlsx", csv: "csv" };
      const blob = new Blob([response.data], { type: mimes[format] });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `rapport-fiissa-${period}.${exts[format]}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Export ${format.toUpperCase()} téléchargé`);
    } catch {
      toast.error("Erreur lors de l'export");
    } finally {
      setIsExporting(false);
    }
  };

  /* Données graphiques */
  const dailyPoints: { x: number; y: number }[] = (data?.daily_sales ?? []).map(
    (d: { date: string; revenue_xof: number }, i: number) => ({ x: i, y: d.revenue_xof ?? 0 })
  );
  const hourlyBars: { label: string; value: number }[] = (data?.hourly_breakdown ?? []).map(
    (h: { hour: number; count: number }) => ({ label: `${h.hour}h`, value: h.count ?? 0 })
  );

  const stats = [
    {
      label: "Commandes",
      value: data?.orders_count?.toLocaleString("fr-FR") ?? "-",
      icon: <ShoppingBag size={20} style={{ color: "var(--p-500)" }} />,
      iconBg: "rgba(34,87,255,0.08)",
      sub: data?.orders_delivered ? `${data.orders_delivered} livrées` : undefined,
    },
    {
      label: "Chiffre d'affaires",
      value: data?.revenue_xof ? `${data.revenue_xof.toLocaleString("fr-FR")} F` : "-",
      icon: <Banknote size={20} style={{ color: "var(--s-500)" }} />,
      iconBg: "rgba(0,214,143,0.10)",
      sub: data?.avg_order_xof ? `Panier : ${data.avg_order_xof.toLocaleString("fr-FR")} F` : undefined,
    },
    {
      label: "Clients uniques",
      value: data?.unique_customers?.toLocaleString("fr-FR") ?? "-",
      icon: <Users size={20} style={{ color: "#7C3AED" }} />,
      iconBg: "rgba(124,58,237,0.08)",
      sub: data?.new_customers ? `${data.new_customers} nouveaux` : undefined,
    },
    {
      label: "Panier moyen",
      value: data?.avg_order_xof ? `${data.avg_order_xof.toLocaleString("fr-FR")} F` : "-",
      icon: <TrendingUp size={20} style={{ color: "#F59E0B" }} />,
      iconBg: "rgba(245,158,11,0.08)",
    },
  ];

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>

      {/* ─── Header ─── */}
      <div style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }} className="px-5 pt-5 pb-4">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>Rapports</h1>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport("csv")}
              disabled={isExporting}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold"
              style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}
            >
              <Download size={13} />CSV
            </button>
            <button
              onClick={() => handleExport("pdf")}
              disabled={isExporting}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold"
              style={{ background: "rgba(220,38,38,0.08)", color: "#DC2626" }}
            >
              <FileText size={13} />PDF
            </button>
          </div>
        </div>

        {/* Excel export — prominent */}
        <button
          onClick={() => handleExport("excel")}
          disabled={isExporting}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl font-bold text-white transition-all active:scale-95 disabled:opacity-60 mb-4"
          style={{ background: "#1D6F42" }}
        >
          <FileSpreadsheet size={18} />
          {isExporting ? "Export en cours…" : "Exporter vers Excel"}
        </button>

        {/* Période */}
        <div className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1 scrollbar-hide">
          {PERIODS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setPeriod(value)}
              className="shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-colors"
              style={
                period === value
                  ? { background: "#111111", color: "#fff" }
                  : { background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }
              }
            >
              {label}
            </button>
          ))}
        </div>

        {period === "custom" && (
          <div className="mt-3 flex gap-2">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="flex-1 rounded-xl border px-3 py-2 text-sm"
              style={{ borderColor: "var(--bd)", color: "var(--tx-head)", background: "var(--bg-card)" }}
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="flex-1 rounded-xl border px-3 py-2 text-sm"
              style={{ borderColor: "var(--bd)", color: "var(--tx-head)", background: "var(--bg-card)" }}
            />
          </div>
        )}
      </div>

      <div className="px-4 py-4 space-y-4">

        {/* ─── KPIs ─── */}
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}>
                <div className="skeleton h-20 w-full" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {stats.map((s, i) => <StatCard key={i} {...s} />)}
          </div>
        )}

        {/* ─── Courbe revenus journaliers ─── */}
        {dailyPoints.length >= 2 && (
          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <div className="flex items-center justify-between mb-1">
              <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Revenus journaliers</h2>
              <span className="text-xs font-bold" style={{ color: "var(--tx-muted)" }}>
                {data?.daily_sales?.length ?? 0} jours
              </span>
            </div>
            <p className="text-xs mb-3" style={{ color: "var(--tx-muted)" }}>
              {data?.daily_sales?.[0]?.date} → {data?.daily_sales?.at(-1)?.date}
            </p>
            <LineChart points={dailyPoints} color="#111111" />
            <div className="flex justify-between mt-1">
              <span className="text-[10px]" style={{ color: "var(--tx-muted)" }}>
                Min : {Math.min(...dailyPoints.map((p) => p.y)).toLocaleString("fr-FR")} F
              </span>
              <span className="text-[10px] font-bold" style={{ color: "#111111" }}>
                Max : {Math.max(...dailyPoints.map((p) => p.y)).toLocaleString("fr-FR")} F
              </span>
            </div>
          </div>
        )}

        {/* ─── Volume horaire ─── */}
        {hourlyBars.length > 0 && (
          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-sm mb-1" style={{ color: "var(--tx-head)" }}>Volume par heure</h2>
            <p className="text-xs mb-3" style={{ color: "var(--tx-muted)" }}>Commandes par tranche horaire</p>
            <BarChart bars={hourlyBars} color="#111111" />
            <div className="flex justify-between mt-2">
              {[0, 6, 12, 18, 23].map((h) => (
                <span key={h} className="text-[10px]" style={{ color: "var(--tx-muted)" }}>{h}h</span>
              ))}
            </div>
          </div>
        )}

        {/* ─── Répartition par opérateur ─── */}
        {data?.payment_by_operator?.length > 0 && (
          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-sm mb-3" style={{ color: "var(--tx-head)" }}>Paiements par opérateur</h2>
            <div className="space-y-3">
              {data.payment_by_operator.map((info: any) => {
                const OP_LABELS: Record<string, string> = {
                  tmoney: "T-Money", flooz: "Flooz", wave: "Wave",
                  orange_money: "Orange Money", mtn_momo: "MTN MoMo", free_money: "Free Money",
                };
                const OP_COLORS: Record<string, string> = {
                  tmoney: "#E11D48", flooz: "#F97316", wave: "#1D4ED8",
                  orange_money: "#EA580C", mtn_momo: "#CA8A04",
                };
                const op  = info.operator || "other";
                const pct = data.revenue_xof ? Math.round((info.total_xof / data.revenue_xof) * 100) : 0;
                const col = OP_COLORS[op] || "var(--n-400)";
                return (
                  <div key={op}>
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs font-bold" style={{ color: "#111111" }}>{OP_LABELS[op] || op}</p>
                      <p className="text-xs font-bold" style={{ color: "#111111" }}>
                        {info.total_xof?.toLocaleString("fr-FR")} F · {pct}%
                      </p>
                    </div>
                    <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--n-100)" }}>
                      <div className="h-2 rounded-full transition-all" style={{ background: col, width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ─── Top produits ─── */}
        {data?.top_products?.length > 0 && (
          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-sm mb-3" style={{ color: "var(--tx-head)" }}>Top produits</h2>
            <div className="space-y-3">
              {data.top_products.map((product: any, i: number) => (
                <div key={product.product_id || i} className="flex items-center gap-3">
                  <div
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
                    style={{ background: i === 0 ? "#111111" : "var(--n-300)" }}
                  >
                    {i + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
                      {product.product_name || product.name}
                    </p>
                    <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                      {product.quantity_sold} vendus
                    </p>
                  </div>
                  <p className="shrink-0 text-sm font-bold" style={{ color: "#111111" }}>
                    {product.revenue_xof?.toLocaleString("fr-FR")} F
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ─── Top clients ─── */}
        {data?.top_customers?.length > 0 && (
          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-sm mb-3" style={{ color: "var(--tx-head)" }}>Top clients</h2>
            <div className="space-y-3">
              {data.top_customers.map((customer: any, i: number) => (
                <div key={customer.customer_id} className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
                      {i + 1}. {customer.customer_name}
                    </p>
                    <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                      {customer.orders_count} achats · {customer.segment}
                    </p>
                  </div>
                  <p className="shrink-0 text-sm font-bold" style={{ color: "#111111" }}>
                    {customer.total_spent_xof?.toLocaleString("fr-FR")} F
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ─── Qualité de service ─── */}
        {data && (
          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-sm mb-3" style={{ color: "var(--tx-head)" }}>Qualité de service</h2>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-xl font-semibold" style={{ color: "var(--s-500)" }}>
                  {data.orders_count > 0 ? Math.round(((data.orders_delivered || 0) / data.orders_count) * 100) : 0}%
                </p>
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>Taux de livraison</p>
              </div>
              <div>
                <p className="text-xl font-semibold" style={{ color: "#EF4444" }}>
                  {data.orders_cancelled || 0}
                </p>
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>Annulées</p>
              </div>
              <div>
                <p className="text-xl font-semibold" style={{ color: "var(--p-500)" }}>
                  {data.orders_delivered || 0}
                </p>
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>Livrées</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
