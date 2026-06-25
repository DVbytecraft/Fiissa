"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle,
  Circle,
  Package,
  Tag,
  Zap,
} from "lucide-react";
import { ordersApi } from "@/lib/api";
import { toast } from "sonner";

/* Génère un code sac type #B-42 */
function generateSackCode(): string {
  const letter = String.fromCharCode(65 + Math.floor(Math.random() * 26));
  const num    = Math.floor(Math.random() * 99) + 1;
  return `#${letter}-${String(num).padStart(2, "0")}`;
}

type PickState = "picking" | "validated";

export default function OrderPickPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const router      = useRouter();

  const [checked, setChecked]       = useState<Record<string, boolean>>({});
  const [pickState, setPickState]   = useState<PickState>("picking");
  const [sackCode, setSackCode]     = useState<string>("");

  const { data: order, isLoading } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => ordersApi.getOne(orderId).then((r) => r.data),
    enabled: !!orderId,
  });

  const readyMutation = useMutation({
    mutationFn: () => ordersApi.updateStatus(orderId, "ready"),
    onSuccess: () => {
      const code = generateSackCode();
      setSackCode(code);
      setPickState("validated");
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur"),
  });

  const toggle = useCallback((id: string) => {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const items: any[]   = order?.items ?? [];
  const checkedCount   = items.filter((it) => checked[it.id ?? it.product_id]).length;
  const allChecked     = items.length > 0 && checkedCount === items.length;

  /* ── Loading ── */
  if (isLoading) {
    return (
      <div style={{ background: "var(--bg-app)", minHeight: "100vh" }} className="flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-3 border-t-transparent animate-spin"
          style={{ borderColor: "var(--color-action) transparent transparent transparent", borderWidth: 3 }} />
      </div>
    );
  }

  if (!order) return null;

  /* ══════════ ÉTAT VALIDÉ ══════════ */
  if (pickState === "validated") {
    return (
      <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
        <header
          className="sticky top-0 z-40 flex items-center gap-3 px-5"
          style={{ height: 56, background: "rgba(255,255,255,0.92)", backdropFilter: "blur(20px)", borderBottom: "1px solid var(--bd)" }}
        >
          <button
            onClick={() => router.push("/merchant/orders")}
            className="w-9 h-9 rounded-full flex items-center justify-center"
            style={{ background: "var(--n-100)" }}
          >
            <ArrowLeft size={18} style={{ color: "#111111" }} />
          </button>
          <p className="font-black text-base" style={{ color: "#111111" }}>Sac validé</p>
        </header>

        <div className="px-5 pt-12 pb-8 flex flex-col items-center text-center">
          {/* Icône succès */}
          <div
            className="w-24 h-24 rounded-full flex items-center justify-center mb-6"
            style={{ background: "rgba(0,214,143,0.10)" }}
          >
            <CheckCircle size={52} style={{ color: "var(--s-500)" }} />
          </div>

          <h1 className="text-3xl font-black" style={{ color: "#111111" }}>Sac prêt !</h1>
          <p className="text-sm mt-2" style={{ color: "var(--tx-muted)" }}>
            {order.order_number} · {items.length} article{items.length > 1 ? "s" : ""}
          </p>

          {/* Code sac */}
          <div
            className="mt-8 w-full rounded-3xl p-6 text-center"
            style={{ background: "#111111" }}
          >
            <div className="flex items-center justify-center gap-2 mb-3">
              <Tag size={16} className="text-white/60" />
              <p className="text-sm font-bold text-white/60 uppercase tracking-widest">Code sac</p>
            </div>
            <p className="text-6xl font-black text-white tracking-tight">{sackCode}</p>
            <p className="text-white/40 text-xs mt-3 font-mono">
              Collez cette étiquette sur le sac du client
            </p>
          </div>

          {/* Récap articles */}
          <div className="w-full mt-5 rounded-2xl overflow-hidden" style={{ background: "#fff", border: "1px solid var(--bd)" }}>
            {items.map((item, i) => (
              <div
                key={item.id ?? item.product_id}
                className="flex items-center gap-3 px-4 py-3"
                style={{ borderBottom: i < items.length - 1 ? "1px solid var(--bd)" : "none" }}
              >
                <CheckCircle size={16} style={{ color: "var(--s-500)" }} className="flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm truncate" style={{ color: "#111111" }}>{item.product_name ?? item.name}</p>
                  {item.weight_grams && (
                    <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{item.weight_grams}g</p>
                  )}
                </div>
                <p className="font-bold text-sm flex-shrink-0" style={{ color: "#111111" }}>×{item.quantity}</p>
              </div>
            ))}
          </div>

          <button
            onClick={() => router.push("/merchant/orders")}
            className="w-full mt-6 py-4 rounded-2xl font-bold text-white transition-all active:scale-95"
            style={{ background: "#111111" }}
          >
            Retour aux commandes
          </button>
        </div>
      </div>
    );
  }

  /* ══════════ ÉTAT PICKING ══════════ */
  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      {/* ─── Header ─── */}
      <header
        className="sticky top-0 z-40 flex items-center gap-3 px-5"
        style={{
          height: 56,
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--bd)",
        }}
      >
        <button
          onClick={() => router.back()}
          className="w-9 h-9 rounded-full flex items-center justify-center"
          style={{ background: "var(--n-100)" }}
        >
          <ArrowLeft size={18} style={{ color: "#111111" }} />
        </button>
        <div className="flex-1 min-w-0">
          <p className="font-black text-base" style={{ color: "#111111" }}>Préparation</p>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
            {order.order_number} · {order.customer_name}
          </p>
        </div>
        {/* Compteur */}
        <div
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-black"
          style={{ background: allChecked ? "rgba(0,214,143,0.12)" : "var(--n-100)", color: allChecked ? "var(--s-600)" : "#111111" }}
        >
          {checkedCount}/{items.length}
        </div>
      </header>

      {/* ─── Info commande ─── */}
      <div className="px-4 pt-4">
        <div
          className="rounded-2xl px-4 py-3 flex items-center gap-3"
          style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
        >
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: "rgba(34,87,255,0.08)" }}
          >
            <Package size={18} style={{ color: "var(--p-500)" }} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-bold text-sm" style={{ color: "#111111" }}>
              {order.customer_name || "Client"}
            </p>
            <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
              {order.type === "click_collect" ? "Click & Collect" : order.type === "scan_go" ? "Scan & Go" : "Livraison"}
              {order.notes ? ` · ${order.notes}` : ""}
            </p>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="font-black text-sm" style={{ color: "#111111" }}>
              {order.total_xof?.toLocaleString("fr-FR")} F
            </p>
            <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{items.length} article{items.length > 1 ? "s" : ""}</p>
          </div>
        </div>
      </div>

      {/* ─── Checklist articles ─── */}
      <div className="px-4 pt-4">
        <p className="section-label mb-2">Articles à préparer</p>
        <div
          className="rounded-2xl overflow-hidden"
          style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
        >
          {items.length === 0 && (
            <div className="px-4 py-8 text-center">
              <Package size={28} className="mx-auto mb-2" style={{ color: "var(--n-300)" }} />
              <p className="text-sm" style={{ color: "var(--tx-muted)" }}>Aucun article dans cette commande</p>
            </div>
          )}

          {items.map((item, i) => {
            const key     = item.id ?? item.product_id ?? String(i);
            const isDone  = !!checked[key];
            return (
              <button
                key={key}
                onClick={() => toggle(key)}
                className="w-full flex items-center gap-3 px-4 py-4 text-left active:bg-gray-50 transition-colors"
                style={{ borderBottom: i < items.length - 1 ? "1px solid var(--bd)" : "none" }}
              >
                {/* Checkbox */}
                <div className="flex-shrink-0 transition-all">
                  {isDone
                    ? <CheckCircle size={24} style={{ color: "var(--s-500)" }} />
                    : <Circle size={24} style={{ color: "var(--n-300)" }} />
                  }
                </div>

                {/* Produit */}
                <div className="flex-1 min-w-0">
                  <p
                    className="font-bold text-sm transition-colors"
                    style={{ color: isDone ? "var(--tx-muted)" : "#111111", textDecoration: isDone ? "line-through" : "none" }}
                  >
                    {item.product_name ?? item.name}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {item.weight_grams ? `${item.weight_grams}g · ` : ""}
                    {item.price_xof?.toLocaleString("fr-FR") ?? ""} F
                  </p>
                </div>

                {/* Quantité */}
                <div
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-sm font-black flex-shrink-0"
                  style={{
                    background: isDone ? "rgba(0,214,143,0.10)" : "var(--n-100)",
                    color: isDone ? "var(--s-600)" : "#111111",
                  }}
                >
                  ×{item.quantity}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ─── Action fixe en bas ─── */}
      <div
        className="fixed bottom-0 left-0 right-0 px-4 pt-3 pb-6 md:pl-64 md:pr-8"
        style={{ background: "rgba(255,255,255,0.96)", backdropFilter: "blur(12px)", borderTop: "1px solid var(--bd)" }}
      >
        {!allChecked && (
          <p className="text-center text-xs mb-2" style={{ color: "var(--tx-muted)" }}>
            Cochez tous les articles avant de valider le sac
          </p>
        )}
        <button
          onClick={() => readyMutation.mutate()}
          disabled={!allChecked || readyMutation.isPending}
          className="w-full flex items-center justify-center gap-2 py-4 rounded-2xl font-black text-white transition-all active:scale-95 disabled:opacity-40"
          style={{
            background: allChecked ? "#111111" : "var(--n-200)",
            color: allChecked ? "#fff" : "var(--tx-muted)",
          }}
        >
          {readyMutation.isPending
            ? <><div className="w-5 h-5 rounded-full border-2 border-t-transparent animate-spin border-white" />Validation…</>
            : <><Zap size={18} />Valider le sac</>
          }
        </button>
      </div>

      {/* Spacer pour le bouton fixe */}
      <div className="h-32" />
    </div>
  );
}
