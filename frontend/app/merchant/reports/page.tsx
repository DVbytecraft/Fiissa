"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Banknote, Download, FileText, ShoppingBag, TrendingUp, Users } from "lucide-react";
import { toast } from "sonner";

import { reportsApi } from "@/lib/api";

type Period = "today" | "week" | "month" | "custom";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  iconBg: string;
  sub?: string;
}

function StatCard({ label, value, icon, iconBg, sub }: StatCardProps) {
  return (
    <div
      style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
      className="rounded-2xl p-4"
    >
      <div
        style={{ background: iconBg }}
        className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
      >
        {icon}
      </div>
      <p style={{ color: "var(--tx-head)" }} className="text-2xl font-black">
        {value}
      </p>
      <p style={{ color: "var(--tx-muted)" }} className="mt-0.5 text-sm">
        {label}
      </p>
      {sub && (
        <p style={{ color: "var(--tx-muted)" }} className="mt-1 text-xs opacity-75">
          {sub}
        </p>
      )}
    </div>
  );
}

export default function MerchantReportsPage() {
  const [period, setPeriod] = useState<Period>("month");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isExporting, setIsExporting] = useState(false);

  const periodOptions: { value: Period; label: string }[] = [
    { value: "today", label: "Aujourd'hui" },
    { value: "week", label: "Cette semaine" },
    { value: "month", label: "Ce mois" },
    { value: "custom", label: "Personnalise" },
  ];

  const { data, isLoading } = useQuery({
    queryKey: ["reports", period, startDate, endDate],
    queryFn: () =>
      reportsApi
        .getSummary({
          period,
          date_from: period === "custom" ? startDate : undefined,
          date_to: period === "custom" ? endDate : undefined,
        })
        .then((response) => response.data),
    enabled: period !== "custom" || (!!startDate && !!endDate),
  });

  const handleExport = async (format: "csv" | "excel" | "pdf") => {
    setIsExporting(true);
    try {
      const response = await reportsApi.export(format, {
        period,
        date_from: period === "custom" ? startDate : undefined,
        date_to: period === "custom" ? endDate : undefined,
      });
      const blob = new Blob([response.data], {
        type:
          format === "pdf"
            ? "application/pdf"
            : format === "excel"
              ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              : "text/csv",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `rapport-${period}.${format === "excel" ? "xlsx" : format}`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success("Export telecharge");
    } catch {
      toast.error("Erreur lors de l'export");
    } finally {
      setIsExporting(false);
    }
  };

  const stats: StatCardProps[] = [
    {
      label: "Commandes",
      value: data?.orders_count?.toLocaleString("fr-FR") || "-",
      icon: <ShoppingBag size={20} style={{ color: "var(--p-500)" }} />,
      iconBg: "rgba(34,87,255,0.08)",
      sub: data?.orders_delivered ? `${data.orders_delivered} livrees` : undefined,
    },
    {
      label: "Chiffre d'affaires",
      value: data?.revenue_xof ? `${data.revenue_xof.toLocaleString("fr-FR")} F` : "-",
      icon: <Banknote size={20} style={{ color: "var(--s-500)" }} />,
      iconBg: "rgba(0,214,143,0.1)",
      sub: data?.avg_order_xof ? `Panier moyen : ${data.avg_order_xof.toLocaleString("fr-FR")} F` : undefined,
    },
    {
      label: "Clients uniques",
      value: data?.unique_customers?.toLocaleString("fr-FR") || "-",
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
      <div
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
        className="px-6 pb-4 pt-12"
      >
        <div className="mb-4 flex items-center justify-between">
          <h1 style={{ color: "var(--tx-head)" }} className="text-xl font-bold">
            Rapports
          </h1>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport("csv")}
              disabled={isExporting}
              style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}
              className="flex items-center gap-1 rounded-xl px-3 py-2 text-sm font-medium"
            >
              <Download size={14} />
              CSV
            </button>
            <button
              onClick={() => handleExport("pdf")}
              disabled={isExporting}
              className="flex items-center gap-1 rounded-xl px-3 py-2 text-sm font-medium"
              style={{ background: "rgba(220,38,38,0.08)", color: "#DC2626" }}
            >
              <FileText size={14} />
              PDF
            </button>
          </div>
        </div>

        <div className="-mx-6 flex gap-2 overflow-x-auto px-6 pb-1 scrollbar-hide">
          {periodOptions.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setPeriod(value)}
              style={
                period === value
                  ? { background: "var(--p-500)", color: "#fff" }
                  : { background: "var(--bg-app)", color: "var(--tx-muted)" }
              }
              className="shrink-0 rounded-full px-4 py-2 text-sm font-medium transition-colors"
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
              style={{ borderColor: "var(--bd)", color: "var(--tx-head)", background: "var(--bg-card)" }}
              className="flex-1 rounded-xl border px-3 py-2 text-sm"
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={{ borderColor: "var(--bd)", color: "var(--tx-head)", background: "var(--bg-card)" }}
              className="flex-1 rounded-xl border px-3 py-2 text-sm"
            />
          </div>
        )}
      </div>

      <div className="space-y-4 px-4 py-4">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
                <div className="skeleton h-20 w-full" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {stats.map((stat, i) => (
              <StatCard key={i} {...stat} />
            ))}
          </div>
        )}

        {data?.top_products && data.top_products.length > 0 && (
          <div
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
            className="rounded-2xl p-4"
          >
            <h2 style={{ color: "var(--tx-head)" }} className="mb-3 font-bold">
              Top produits
            </h2>
            <div className="space-y-3">
              {data.top_products.map((product: any, i: number) => (
                <div
                  key={product.product_id || `${product.product_name || product.name}-${i}`}
                  className="flex items-center gap-3"
                >
                  <div
                    style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  >
                    {i + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p style={{ color: "var(--tx-head)" }} className="truncate text-sm font-semibold">
                      {product.product_name || product.name}
                    </p>
                    <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                      {product.quantity_sold} vendus
                    </p>
                  </div>
                  <p style={{ color: "var(--tx-head)" }} className="shrink-0 text-sm font-bold">
                    {product.revenue_xof?.toLocaleString("fr-FR")} F
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {data?.payment_by_operator && data.payment_by_operator.length > 0 && (
          <div
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
            className="rounded-2xl p-4"
          >
            <h2 style={{ color: "var(--tx-head)" }} className="mb-3 font-bold">
              Paiements par operateur
            </h2>
            <div className="space-y-2">
              {data.payment_by_operator.map((info: any) => {
                const op = info.operator || "other";
                const labels: Record<string, string> = {
                  wave: "Wave",
                  orange_money: "Orange Money",
                  mtn_momo: "MTN MoMo",
                  moov_money: "Moov Money",
                  free_money: "Free Money",
                };
                const pct = data.revenue_xof ? Math.round((info.total_xof / data.revenue_xof) * 100) : 0;

                return (
                  <div key={op} className="flex items-center gap-2">
                    <p style={{ color: "var(--tx-muted)" }} className="w-32 shrink-0 text-sm">
                      {labels[op] || op}
                    </p>
                    <div
                      style={{ background: "var(--bg-app)" }}
                      className="h-2 flex-1 overflow-hidden rounded-full"
                    >
                      <div
                        style={{ background: "var(--p-500)", width: `${pct}%` }}
                        className="h-2 rounded-full"
                      />
                    </div>
                    <p style={{ color: "var(--tx-head)" }} className="w-24 shrink-0 text-right text-xs font-semibold">
                      {info.total_xof?.toLocaleString("fr-FR")} F
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {data?.top_customers && data.top_customers.length > 0 && (
          <div
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
            className="rounded-2xl p-4"
          >
            <h2 style={{ color: "var(--tx-head)" }} className="mb-3 font-bold">
              Top clients
            </h2>
            <div className="space-y-3">
              {data.top_customers.map((customer: any, i: number) => (
                <div key={customer.customer_id} className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p style={{ color: "var(--tx-head)" }} className="truncate text-sm font-semibold">
                      {i + 1}. {customer.customer_name}
                    </p>
                    <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                      {customer.orders_count} achats · segment {customer.segment}
                    </p>
                  </div>
                  <p style={{ color: "var(--tx-head)" }} className="shrink-0 text-sm font-bold">
                    {customer.total_spent_xof?.toLocaleString("fr-FR")} F
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {data && (
          <div
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
            className="rounded-2xl p-4"
          >
            <h2 style={{ color: "var(--tx-head)" }} className="mb-3 font-bold">
              Qualite de service
            </h2>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p style={{ color: "var(--s-500)" }} className="text-xl font-black">
                  {data.orders_count > 0 ? Math.round(((data.orders_delivered || 0) / data.orders_count) * 100) : 0}%
                </p>
                <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                  Taux de livraison
                </p>
              </div>
              <div>
                <p className="text-xl font-black" style={{ color: "#EF4444" }}>{data.orders_cancelled || 0}</p>
                <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                  Annulees
                </p>
              </div>
              <div>
                <p style={{ color: "var(--p-500)" }} className="text-xl font-black">
                  {data.orders_delivered || 0}
                </p>
                <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                  Livrees
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
