"use client";

import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Phone, Search, User, Package, Receipt,
  ChevronRight, Clock, CheckCircle, XCircle, AlertCircle,
  X,
} from "lucide-react";
import { ordersApi, receiptsApi } from "@/lib/api";

/* ── Badges statut ── */
const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  payment_submitted: { label: "Paiement soumis",  color: "var(--p-500)", bg: "rgba(34,87,255,0.08)", icon: <Clock size={11} /> },
  confirmed:         { label: "Confirmée",          color: "var(--p-500)", bg: "rgba(34,87,255,0.08)", icon: <CheckCircle size={11} /> },
  preparing:         { label: "En préparation",     color: "#F97316",      bg: "#FFF7ED",              icon: <Clock size={11} /> },
  ready:             { label: "Prête",              color: "var(--s-600)", bg: "rgba(0,214,143,0.08)", icon: <CheckCircle size={11} /> },
  delivered:         { label: "Livrée",             color: "var(--s-600)", bg: "rgba(0,214,143,0.08)", icon: <CheckCircle size={11} /> },
  cancelled:         { label: "Annulée",            color: "#DC2626",      bg: "rgba(220,38,38,0.08)", icon: <XCircle size={11} /> },
  refunded:          { label: "Remboursée",         color: "var(--tx-muted)", bg: "var(--n-100)",      icon: <AlertCircle size={11} /> },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: "var(--tx-muted)", bg: "var(--n-100)", icon: null };
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold"
      style={{ color: cfg.color, background: cfg.bg }}
    >
      {cfg.icon}{cfg.label}
    </span>
  );
}

/* ── Détail client (lecture seule) ── */
function CustomerDetail({ query }: { query: string }) {
  const { data: ordersData, isLoading: loadingOrders } = useQuery({
    queryKey: ["callcenter-orders", query],
    queryFn: () =>
      ordersApi.getMerchantOrders(undefined).then((r) => {
        const items: any[] = r.data?.items ?? r.data ?? [];
        const q = query.toLowerCase().replace(/\s+/g, "");
        return items.filter((o) => {
          const name  = (o.customer_name ?? "").toLowerCase().replace(/\s+/g, "");
          const phone = (o.customer_phone ?? "").replace(/\s+/g, "");
          return name.includes(q) || phone.includes(query.replace(/\s+/g, ""));
        });
      }),
    enabled: query.trim().length >= 3,
    staleTime: 30_000,
  });

  const { data: receiptsData, isLoading: loadingReceipts } = useQuery({
    queryKey: ["callcenter-receipts", query],
    queryFn: () =>
      receiptsApi.getMerchantReceipts({ search: query }).then((r) => r.data?.items ?? r.data ?? []),
    enabled: query.trim().length >= 3,
    staleTime: 30_000,
  });

  const orders: any[]   = ordersData ?? [];
  const receipts: any[] = receiptsData ?? [];
  const isLoading       = loadingOrders || loadingReceipts;

  if (query.trim().length < 3) {
    return (
      <div className="pt-16 text-center px-8">
        <Search size={40} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
        <p className="font-bold" style={{ color: "#111111" }}>Rechercher un client</p>
        <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
          Saisissez un numéro de téléphone ou un nom (3 caractères minimum)
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="pt-16 flex flex-col items-center gap-4">
        <div className="w-8 h-8 rounded-full border-3 border-t-transparent animate-spin"
          style={{ borderColor: "var(--color-action) transparent transparent transparent", borderWidth: 3 }} />
        <p className="text-sm" style={{ color: "var(--tx-muted)" }}>Recherche en cours…</p>
      </div>
    );
  }

  if (!orders.length && !receipts.length) {
    return (
      <div className="pt-16 text-center px-8">
        <User size={40} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
        <p className="font-bold" style={{ color: "#111111" }}>Aucun résultat</p>
        <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
          Aucun client trouvé pour « {query} »
        </p>
      </div>
    );
  }

  /* Dédupliquer le nom client depuis les commandes */
  const customerName = orders[0]?.customer_name || receipts[0]?.customer_name || query;
  const customerPhone = orders[0]?.customer_phone || "";

  return (
    <div className="px-4 pt-4 space-y-4 pb-8">

      {/* ─── Fiche client ─── */}
      <div
        className="rounded-2xl px-4 py-4 flex items-center gap-3"
        style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
      >
        <div
          className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 text-xl font-semibold"
          style={{ background: "var(--n-100)", color: "#111111" }}
        >
          {customerName[0]?.toUpperCase() ?? "?"}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-base" style={{ color: "#111111" }}>{customerName}</p>
          {customerPhone && (
            <div className="flex items-center gap-1.5 mt-0.5">
              <Phone size={12} style={{ color: "var(--tx-muted)" }} />
              <p className="text-sm font-mono" style={{ color: "var(--tx-muted)" }}>{customerPhone}</p>
            </div>
          )}
        </div>
        <div className="text-right flex-shrink-0">
          <p className="font-semibold text-lg" style={{ color: "#111111" }}>{orders.length}</p>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>commandes</p>
        </div>
      </div>

      {/* ─── Commandes (lecture seule) ─── */}
      {orders.length > 0 && (
        <div>
          <p className="section-label mb-2">Commandes</p>
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
          >
            {orders.map((order, i) => (
              <div
                key={order.id}
                className="flex items-center gap-3 px-4 py-3.5"
                style={{ borderBottom: i < orders.length - 1 ? "1px solid var(--bd)" : "none" }}
              >
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "rgba(34,87,255,0.08)" }}
                >
                  <Package size={16} style={{ color: "var(--p-500)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-bold text-sm" style={{ color: "#111111" }}>{order.order_number}</p>
                    <StatusBadge status={order.status} />
                  </div>
                  <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {order.items_count} article{(order.items_count ?? 0) > 1 ? "s" : ""}
                    {order.created_at ? ` · ${new Date(order.created_at).toLocaleDateString("fr-FR")}` : ""}
                  </p>
                </div>
                <div className="flex-shrink-0 text-right">
                  <p className="font-bold text-sm" style={{ color: "#111111" }}>
                    {order.total_xof?.toLocaleString("fr-FR")} F
                  </p>
                  <p className="text-[10px]" style={{ color: "var(--tx-muted)" }}>
                    {order.type === "click_collect" ? "Retrait" : order.type === "scan_go" ? "Scan & Go" : "Livraison"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Reçus (lecture seule) ─── */}
      {receipts.length > 0 && (
        <div>
          <p className="section-label mb-2">Reçus</p>
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
          >
            {receipts.map((receipt, i) => (
              <div
                key={receipt.id}
                className="flex items-center gap-3 px-4 py-3.5"
                style={{ borderBottom: i < receipts.length - 1 ? "1px solid var(--bd)" : "none" }}
              >
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "rgba(0,214,143,0.08)" }}
                >
                  <Receipt size={16} style={{ color: "var(--s-600)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-sm" style={{ color: "#111111" }}>{receipt.receipt_number}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {receipt.store_name}
                    {receipt.created_at ? ` · ${new Date(receipt.created_at).toLocaleDateString("fr-FR")}` : ""}
                  </p>
                </div>
                <p className="font-bold text-sm flex-shrink-0" style={{ color: "#111111" }}>
                  {receipt.total_xof?.toLocaleString("fr-FR")} F
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Note lecture seule */}
      <div
        className="flex items-center gap-2 px-4 py-3 rounded-2xl"
        style={{ background: "rgba(34,87,255,0.06)", border: "1px solid rgba(34,87,255,0.12)" }}
      >
        <AlertCircle size={14} style={{ color: "var(--p-500)" }} className="flex-shrink-0" />
        <p className="text-xs" style={{ color: "var(--p-600)" }}>
          Vue lecture seule. Pour modifier une commande, contactez le responsable.
        </p>
      </div>
    </div>
  );
}

/* ── Page principale Call Center ── */
export default function CallCenterPage() {
  const [search, setSearch] = useState("");
  const [query,  setQuery]  = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(search.trim());
  };

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      {/* ─── Header ─── */}
      <div
        className="px-5 pt-5 pb-4"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0"
            style={{ background: "rgba(34,87,255,0.08)" }}
          >
            <Phone size={20} style={{ color: "var(--p-500)" }} />
          </div>
          <div>
            <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>Call Center</h1>
            <p className="text-xs" style={{ color: "var(--tx-muted)" }}>Recherche client · Vue lecture seule</p>
          </div>
        </div>

        {/* Barre de recherche */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <div
            className="flex-1 flex items-center gap-3 px-4 py-3 rounded-2xl"
            style={{ background: "var(--n-50)", border: "1.5px solid var(--bd)" }}
          >
            <Search size={16} style={{ color: "var(--n-400)" }} className="flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Téléphone ou nom du client…"
              className="flex-1 bg-transparent text-sm outline-none"
              style={{ color: "#111111" }}
            />
            {search && (
              <button
                type="button"
                onClick={() => { setSearch(""); setQuery(""); inputRef.current?.focus(); }}
                className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: "var(--n-300)", color: "white" }}
              >
                <X size={12} />
              </button>
            )}
          </div>
          <button
            type="submit"
            className="px-4 py-3 rounded-2xl font-bold text-sm text-white flex-shrink-0"
            style={{ background: "#111111" }}
          >
            Chercher
          </button>
        </form>
      </div>

      {/* ─── Résultats ─── */}
      <CustomerDetail query={query} />
    </div>
  );
}
