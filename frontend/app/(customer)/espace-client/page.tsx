"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Star, Receipt, TrendingUp, ChevronRight, Download,
  Store, Calendar, Package, ArrowLeft,
} from "lucide-react";
import { ordersApi, receiptsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";

const DAYS: Record<string, string> = {
  mon: "Lun", tue: "Mar", wed: "Mer", thu: "Jeu",
  fri: "Ven", sat: "Sam", sun: "Dim",
};

function formatXOF(amount: number) {
  return new Intl.NumberFormat("fr-FR").format(amount) + " XOF";
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
}

export default function EspaceClientPage() {
  const { user } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!user) router.push("/login");
  }, [user, router]);

  const { data: ordersData, isLoading: ordersLoading } = useQuery({
    queryKey: ["my-orders"],
    queryFn: () => ordersApi.getMyOrders(1),
    enabled: !!user,
  });

  const { data: receiptsData, isLoading: receiptsLoading } = useQuery({
    queryKey: ["my-receipts"],
    queryFn: () => receiptsApi.getMyReceipts(),
    enabled: !!user,
  });

  const orders: any[] = ordersData?.data?.items || ordersData?.data || [];
  const receipts: any[] = receiptsData?.data?.items || receiptsData?.data || [];

  // Calcul totaux
  const totalSpent = receipts.reduce((s: number, r: any) => s + (r.total_xof || 0), 0);
  const totalOrders = orders.length;

  // Regroupement par enseigne
  const byCompany: Record<string, { name: string; slug?: string; logoUrl?: string; spent: number; count: number }> = {};
  for (const r of receipts) {
    const cid = r.company_id || "unknown";
    if (!byCompany[cid]) {
      byCompany[cid] = {
        name: r.company_name || "Enseigne",
        slug: r.company_slug,
        logoUrl: r.company_logo_url,
        spent: 0,
        count: 0,
      };
    }
    byCompany[cid].spent += r.total_xof || 0;
    byCompany[cid].count += 1;
  }
  const companies = Object.entries(byCompany).sort((a, b) => b[1].spent - a[1].spent);

  if (!user) return null;

  return (
    <div className="flex flex-col min-h-screen" style={{ background: "var(--bg-app)" }}>
      {/* Header */}
      <div
        className="px-5 pt-12 pb-5"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <div className="flex items-center gap-3 mb-4">
          <button onClick={() => router.back()} style={{ color: "var(--tx-muted)" }}>
            <ArrowLeft size={22} />
          </button>
          <h1 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>
            Mon Espace
          </h1>
        </div>
        <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
          Bonjour <strong style={{ color: "var(--tx-head)" }}>{user.firstName}</strong> — voici votre tableau de bord.
        </p>
      </div>

      <div className="flex-1 px-5 py-6 space-y-6">

        {/* ── Stat cards ── */}
        <div className="grid grid-cols-2 gap-3">
          <div
            className="rounded-2xl p-4"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <TrendingUp size={20} style={{ color: "var(--p-500)" }} />
            <p className="mt-2 text-xl font-bold" style={{ color: "var(--tx-head)" }}>
              {receiptsLoading ? "—" : formatXOF(totalSpent)}
            </p>
            <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>Total dépensé</p>
          </div>
          <div
            className="rounded-2xl p-4"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <Package size={20} style={{ color: "var(--s-500)" }} />
            <p className="mt-2 text-xl font-bold" style={{ color: "var(--tx-head)" }}>
              {ordersLoading ? "—" : totalOrders}
            </p>
            <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>Commandes</p>
          </div>
        </div>

        {/* ── Mes enseignes ── */}
        {companies.length > 0 && (
          <section>
            <h2 className="text-sm font-bold uppercase tracking-[0.14em] mb-3" style={{ color: "var(--tx-muted)" }}>
              Mes enseignes
            </h2>
            <div className="space-y-2">
              {companies.map(([companyId, info]) => (
                <Link
                  key={companyId}
                  href={info.slug ? `/c/${info.slug}` : "#"}
                  className="flex items-center gap-4 rounded-2xl p-4"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 overflow-hidden"
                    style={{ background: "var(--bg-app)" }}
                  >
                    {info.logoUrl ? (
                      <img src={info.logoUrl} alt={info.name} className="w-full h-full object-cover" />
                    ) : (
                      <Store size={22} style={{ color: "var(--tx-muted)" }} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm truncate" style={{ color: "var(--tx-head)" }}>
                      {info.name}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                      {info.count} achat{info.count > 1 ? "s" : ""} · {formatXOF(info.spent)}
                    </p>
                  </div>
                  <ChevronRight size={18} style={{ color: "var(--tx-muted)" }} />
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* ── Mes reçus ── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-[0.14em]" style={{ color: "var(--tx-muted)" }}>
              Mes reçus
            </h2>
            <Link href="/receipts" className="text-xs font-semibold" style={{ color: "var(--p-500)" }}>
              Voir tout
            </Link>
          </div>

          {receiptsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-2xl h-16 animate-pulse" style={{ background: "var(--bg-card)" }} />
              ))}
            </div>
          ) : receipts.length === 0 ? (
            <div
              className="rounded-2xl p-8 flex flex-col items-center"
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
            >
              <Receipt size={36} style={{ color: "var(--tx-muted)", opacity: 0.4 }} />
              <p className="mt-3 text-sm" style={{ color: "var(--tx-muted)" }}>Aucun reçu pour l'instant</p>
            </div>
          ) : (
            <div className="space-y-2">
              {receipts.slice(0, 8).map((r: any) => (
                <div
                  key={r.id}
                  className="flex items-center gap-4 rounded-2xl p-4"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                    style={{ background: "rgba(34,87,255,0.07)" }}
                  >
                    <Receipt size={18} style={{ color: "var(--p-500)" }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate" style={{ color: "var(--tx-head)" }}>
                      {r.company_name || "Enseigne"} · #{r.receipt_number || r.order_number}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                      {r.created_at ? formatDate(r.created_at) : ""} · {formatXOF(r.total_xof || 0)}
                    </p>
                  </div>
                  <a
                    href={`/api/receipts/${r.id}/pdf`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-2 rounded-xl"
                    style={{ background: "var(--bg-app)" }}
                  >
                    <Download size={16} style={{ color: "var(--tx-muted)" }} />
                  </a>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Mes commandes récentes ── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-[0.14em]" style={{ color: "var(--tx-muted)" }}>
              Commandes récentes
            </h2>
            <Link href="/orders" className="text-xs font-semibold" style={{ color: "var(--p-500)" }}>
              Voir tout
            </Link>
          </div>
          {ordersLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="rounded-2xl h-16 animate-pulse" style={{ background: "var(--bg-card)" }} />
              ))}
            </div>
          ) : orders.length === 0 ? (
            <p className="text-sm text-center py-6" style={{ color: "var(--tx-muted)" }}>Aucune commande</p>
          ) : (
            <div className="space-y-2">
              {orders.slice(0, 5).map((o: any) => (
                <Link
                  key={o.id}
                  href={`/orders/${o.id}`}
                  className="flex items-center gap-4 rounded-2xl p-4"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                    style={{ background: "var(--bg-app)" }}
                  >
                    <Calendar size={18} style={{ color: "var(--tx-muted)" }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
                      Commande #{o.order_number}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                      {o.created_at ? formatDate(o.created_at) : ""} · {formatXOF(o.total_xof || 0)}
                    </p>
                  </div>
                  <span
                    className="text-[10px] font-semibold px-2 py-1 rounded-full"
                    style={{
                      background: o.status === "delivered" ? "rgba(0,200,100,0.1)" : "rgba(255,159,0,0.1)",
                      color: o.status === "delivered" ? "#00C864" : "#FF9F00",
                    }}
                  >
                    {o.status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>

      </div>
    </div>
  );
}
