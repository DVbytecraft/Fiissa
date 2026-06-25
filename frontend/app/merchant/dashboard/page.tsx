"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { reportsApi, ordersApi, paymentsApi, notificationsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import {
  ShoppingBag, CreditCard, Package, TrendingUp,
  ChevronRight, AlertCircle, Bell, ArrowUpRight,
  Sparkles, Clock,
} from "lucide-react";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bonjour";
  if (h < 18) return "Bon après-midi";
  return "Bonsoir";
}

function todayLabel() {
  return new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
}

function KpiCard({
  label, value, icon: Icon, iconBg, href, urgent = false, sub,
}: {
  label: string; value: React.ReactNode; icon: any; iconBg: string;
  href?: string; urgent?: boolean; sub?: string;
}) {
  const inner = (
    <div
      className={`rounded-2xl p-4 h-full flex flex-col justify-between ${href ? "active:scale-95 transition-transform" : ""}`}
      style={{
        background: "var(--bg-card)",
        border: `1px solid ${urgent ? "rgba(220,38,38,0.3)" : "var(--bd)"}`,
        boxShadow: urgent ? "0 0 0 3px rgba(220,38,38,0.06)" : "var(--sh-sm)",
      }}
    >
      <div className="flex items-start justify-between">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: iconBg }}>
          <Icon size={20} className="text-white" />
        </div>
        {href && <ChevronRight size={16} style={{ color: "var(--bd)" }} />}
      </div>
      <div className="mt-3">
        <p className="text-2xl font-semibold" style={{ color: urgent ? "#DC2626" : "var(--tx-head)" }}>
          {value}
        </p>
        <p className="text-sm mt-0.5 font-medium" style={{ color: "var(--tx-muted)" }}>{label}</p>
        {sub && <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>{sub}</p>}
      </div>
    </div>
  );
  return href ? <Link href={href} className="block">{inner}</Link> : inner;
}

export default function MerchantDashboard() {
  const { user } = useAuthStore();

  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => reportsApi.getDashboard().then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: pendingPayments } = useQuery({
    queryKey: ["pending-payments"],
    queryFn: () => paymentsApi.getPending().then((r) => r.data),
    refetchInterval: 15_000,
  });

  const { data: pendingOrders } = useQuery({
    queryKey: ["merchant-orders-confirmed"],
    queryFn: () => ordersApi.getMerchantOrders("confirmed").then((r) => r.data),
    refetchInterval: 15_000,
  });

  const { data: notifSummary } = useQuery({
    queryKey: ["merchant-notification-summary"],
    queryFn: () => notificationsApi.getSummary().then((r) => r.data),
    refetchInterval: 30_000,
  });

  const firstName = user?.firstName || "Marchand";
  const hasPendingPayments = (pendingPayments?.length ?? 0) > 0;
  const hasUnread = (notifSummary?.unread_count ?? 0) > 0;

  const kpis = useMemo(() => [
    {
      label: "Commandes",
      value: isLoading ? "—" : (stats?.orders_today ?? 0),
      icon: ShoppingBag,
      iconBg: "var(--p-500)",
      href: "/merchant/orders",
      sub: "Aujourd'hui",
    },
    {
      label: "Revenus",
      value: isLoading ? "—" : `${(stats?.revenue_today_xof || 0).toLocaleString("fr-FR")} F`,
      icon: TrendingUp,
      iconBg: "var(--s-600)",
      href: "/merchant/reports",
      sub: "Aujourd'hui",
    },
    {
      label: "À préparer",
      value: isLoading ? "—" : (stats?.pending_orders ?? 0),
      icon: Package,
      iconBg: "#F59E0B",
      href: "/merchant/orders?status=confirmed",
      urgent: (stats?.pending_orders ?? 0) > 5,
      sub: "En attente",
    },
    {
      label: "Paiements",
      value: isLoading ? "—" : (stats?.pending_payments ?? 0),
      icon: CreditCard,
      iconBg: hasPendingPayments ? "#DC2626" : "var(--n-400)",
      href: "/merchant/payments",
      urgent: hasPendingPayments,
      sub: "À vérifier",
    },
  ], [stats, isLoading, hasPendingPayments]);

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <div
        className="px-5 pt-6 pb-5"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
              {todayLabel()}
            </p>
            <h1 className="mt-1 text-2xl font-semibold leading-tight" style={{ color: "var(--tx-head)" }}>
              {greeting()}, {firstName} 👋
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--tx-muted)" }}>
              Voici l'activité de votre commerce.
            </p>
          </div>
          <Link
            href="/merchant/notifications"
            className="relative w-10 h-10 flex items-center justify-center rounded-2xl transition-colors"
            style={{ background: hasUnread ? "var(--warning-bg)" : "var(--bg-app)", border: "1px solid var(--bd)" }}
          >
            <Bell size={18} style={{ color: hasUnread ? "#D97706" : "var(--tx-muted)" }} />
            {hasUnread && (
              <span
                className="absolute -top-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-semibold text-white"
                style={{ background: "#D97706" }}
              >
                {notifSummary.unread_count > 9 ? "9+" : notifSummary.unread_count}
              </span>
            )}
          </Link>
        </div>
      </div>

      <div className="px-4 py-5 space-y-5">

        {/* ── Alerte paiements urgents ───────────────────────────────── */}
        {hasPendingPayments && (
          <div
            className="rounded-2xl p-4"
            style={{ background: "#FEF2F2", border: "1px solid #FCA5A5" }}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertCircle size={18} style={{ color: "#DC2626" }} />
                <div>
                  <p className="font-bold text-sm" style={{ color: "#B91C1C" }}>
                    {pendingPayments.length} paiement{pendingPayments.length > 1 ? "s" : ""} en attente
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "#DC2626" }}>
                    Des clients attendent votre validation.
                  </p>
                </div>
              </div>
              <Link href="/merchant/payments">
                <button
                  className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-bold text-white active:scale-95 transition-transform"
                  style={{ background: "#DC2626" }}
                >
                  Vérifier <ArrowUpRight size={14} />
                </button>
              </Link>
            </div>
          </div>
        )}

        {/* ── KPIs 2×2 ──────────────────────────────────────────────── */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={14} style={{ color: "var(--p-500)" }} />
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
              Aujourd'hui
            </h2>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {kpis.map((kpi) => (
              <KpiCard key={kpi.label} {...kpi} />
            ))}
          </div>
        </section>

        {/* ── Commandes confirmées à traiter ────────────────────────── */}
        {(pendingOrders?.items?.length ?? 0) > 0 && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Clock size={14} style={{ color: "#F59E0B" }} />
                <h2 className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
                  À préparer
                </h2>
              </div>
              <Link
                href="/merchant/orders?status=confirmed"
                className="flex items-center gap-1 text-xs font-bold"
                style={{ color: "var(--p-500)" }}
              >
                Voir tout <ChevronRight size={12} />
              </Link>
            </div>
            <div className="space-y-2">
              {pendingOrders.items.slice(0, 3).map((order: any) => (
                <Link key={order.id} href={`/merchant/orders/${order.id}`}>
                  <div
                    className="rounded-2xl p-4 flex items-center gap-3 active:scale-[0.99] transition-transform"
                    style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
                  >
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                      style={{ background: "rgba(245,158,11,0.1)" }}
                    >
                      <Package size={18} style={{ color: "#F59E0B" }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{order.order_number}</p>
                      <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                        {order.items_count} article{order.items_count > 1 ? "s" : ""} · {order.customer_name}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="font-bold text-sm" style={{ color: "var(--p-500)" }}>
                        {order.total_xof?.toLocaleString("fr-FR")} F
                      </p>
                      <ChevronRight size={14} className="ml-auto mt-0.5" style={{ color: "var(--bd)" }} />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* ── Liens rapides ─────────────────────────────────────────── */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-[0.16em] mb-3" style={{ color: "var(--tx-muted)" }}>
            Accès rapide
          </h2>
          <div className="grid grid-cols-3 gap-2">
            {[
              { href: "/merchant/products",  icon: Package,    label: "Produits",  color: "var(--p-500)" },
              { href: "/merchant/reports",   icon: TrendingUp, label: "Rapports",  color: "var(--s-600)" },
              { href: "/merchant/customers", icon: ShoppingBag, label: "Clients",  color: "#7C3AED" },
            ].map(({ href, icon: Icon, label, color }) => (
              <Link key={href} href={href}>
                <div
                  className="rounded-2xl p-4 text-center active:scale-95 transition-transform"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2"
                    style={{ background: `${color}14` }}
                  >
                    <Icon size={20} style={{ color }} />
                  </div>
                  <p className="text-xs font-semibold" style={{ color: "var(--tx-muted)" }}>{label}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
