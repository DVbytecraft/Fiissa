"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  ChevronLeft,
  ExternalLink,
  MapPin,
  Package,
  Phone,
  Printer,
  QrCode,
  ReceiptText,
  Sparkles,
  Play,
  Truck,
} from "lucide-react";
import Link from "next/link";
import { ordersApi, receiptsApi } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmModal } from "@/components/ui/confirm-modal";

const STATUS_CONFIG: Record<string, { label: string; bg: string; color: string }> = {
  draft:             { label: "Brouillon",         bg: "var(--bg-app)",              color: "var(--tx-muted)" },
  pending:           { label: "En attente",         bg: "rgba(245,158,11,0.08)",      color: "#D97706" },
  awaiting_payment:  { label: "Attente paiement",   bg: "rgba(249,115,22,0.08)",      color: "#EA580C" },
  payment_submitted: { label: "Paiement soumis",    bg: "rgba(34,87,255,0.08)",       color: "var(--p-500)" },
  confirmed:         { label: "Confirmée",           bg: "rgba(34,87,255,0.08)",       color: "var(--p-500)" },
  preparing:         { label: "En préparation",      bg: "rgba(249,115,22,0.08)",      color: "#EA580C" },
  ready:             { label: "Prête",               bg: "rgba(0,214,143,0.08)",       color: "var(--s-600)" },
  out_for_delivery:  { label: "En livraison",        bg: "rgba(139,92,246,0.08)",      color: "#7C3AED" },
  delivered:         { label: "Livrée",              bg: "rgba(0,214,143,0.08)",       color: "var(--s-600)" },
  cancelled:         { label: "Annulée",             bg: "rgba(220,38,38,0.08)",       color: "#DC2626" },
  refunded:          { label: "Remboursée",          bg: "var(--bg-app)",              color: "var(--tx-muted)" },
};

const ORDER_TYPE_LABELS: Record<string, string> = {
  click_collect: "Click & Collect",
  delivery:      "Livraison",
  scan_go:       "Scan & Go",
};

const NEXT_ACTIONS: Record<string, { to: string; label: string; icon: any; bg: string } | null> = {
  confirmed:        { to: "preparing",        label: "Commencer la préparation", icon: Play,        bg: "var(--p-500)" },
  preparing:        { to: "ready",            label: "Marquer comme prête",      icon: CheckCircle, bg: "var(--s-600)" },
  ready:            { to: "out_for_delivery", label: "Expédier la commande",     icon: Truck,       bg: "#7C3AED" },
  out_for_delivery: { to: "delivered",        label: "Confirmer la livraison",   icon: CheckCircle, bg: "var(--s-600)" },
};

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirmCancel, setConfirmCancel] = useState(false);

  const { data: order, isLoading } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => ordersApi.getOne(orderId).then((r) => r.data),
  });

  const { data: receiptByOrder } = useQuery({
    queryKey: ["receipt-by-order", orderId],
    queryFn: () => receiptsApi.getByOrder(orderId).then((r) => r.data),
    enabled: Boolean(orderId),
    retry: false,
  });

  const updateMutation = useMutation({
    mutationFn: (newStatus: string) => ordersApi.updateStatus(orderId, newStatus),
    onSuccess: () => {
      toast.success("Statut mis à jour");
      queryClient.invalidateQueries({ queryKey: ["order", orderId] });
      queryClient.invalidateQueries({ queryKey: ["merchant-orders"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Transition invalide"),
  });

  const generateReceiptMutation = useMutation({
    mutationFn: (paymentId: string) => receiptsApi.generate(paymentId).then((r) => r.data),
    onSuccess: () => {
      toast.success("Reçu généré");
      queryClient.invalidateQueries({ queryKey: ["receipt-by-order", orderId] });
      queryClient.invalidateQueries({ queryKey: ["order", orderId] });
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || e.response?.data?.message || "Impossible de générer le reçu"),
  });

  const qrMutation = useMutation({
    mutationFn: (receiptId: string) => receiptsApi.getQr(receiptId).then((r) => r.data),
    onSuccess: async (payload) => {
      const absoluteUrl = `${window.location.origin}${payload.verification_url.replace("/api/v1", "")}`;
      await navigator.clipboard.writeText(absoluteUrl);
      toast.success("Lien de vérification copié");
    },
    onError: () => toast.error("Impossible de récupérer le lien QR"),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-app)" }}>
        <div className="w-10 h-10 rounded-full border-4 border-t-transparent animate-spin" style={{ borderColor: "var(--p-500) transparent transparent transparent" }} />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-6" style={{ background: "var(--bg-app)" }}>
        <Package size={56} style={{ color: "var(--bd)" }} className="mb-4" />
        <p className="font-semibold" style={{ color: "var(--tx-muted)" }}>Commande introuvable</p>
        <button onClick={() => router.back()} className="mt-4 font-semibold" style={{ color: "var(--p-500)" }}>
          Retour
        </button>
      </div>
    );
  }

  const statusCfg = STATUS_CONFIG[order.status] || STATUS_CONFIG.draft;
  const nextAction = NEXT_ACTIONS[order.status];
  const deliveryAddress =
    typeof order.delivery_address === "string"
      ? order.delivery_address
      : order.delivery_address
        ? [order.delivery_address.street, order.delivery_address.city, order.delivery_address.area]
            .filter(Boolean).join(", ")
        : null;

  const receipt = receiptByOrder || order.receipt || null;
  const canGenerateReceipt = !receipt && order.payment?.id && order.payment?.status === "confirmed";

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      {/* ── Header ── */}
      <div style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }} className="px-4 pt-6 pb-4">
        <div className="flex items-center gap-3 mb-2">
          <button onClick={() => router.back()} style={{ color: "var(--tx-muted)" }}>
            <ChevronLeft size={24} />
          </button>
          <div className="flex-1">
            <p className="text-xs font-black uppercase tracking-[0.14em]" style={{ color: "var(--tx-muted)" }}>Commande</p>
            <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>{order.order_number}</h1>
          </div>
          <span
            className="text-xs font-black px-3 py-1.5 rounded-full"
            style={{ background: statusCfg.bg, color: statusCfg.color }}
          >
            {statusCfg.label}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs" style={{ color: "var(--tx-muted)" }}>
          <span className="font-semibold">{ORDER_TYPE_LABELS[order.order_type] || order.order_type}</span>
          <span>·</span>
          <span>
            {new Date(order.created_at).toLocaleDateString("fr-FR", {
              day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
            })}
          </span>
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">

        {/* ── Carte montant ── */}
        <div
          className="rounded-3xl p-5 text-white relative overflow-hidden"
          style={{ background: "var(--fiissa-gradient)", boxShadow: "var(--sh-brand)" }}
        >
          <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-white/10" />
          <div className="absolute right-10 bottom-0 h-20 w-20 rounded-full bg-white/10" />
          <div className="relative flex items-start justify-between gap-3">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-[11px] font-black uppercase tracking-[0.16em]">
                <Sparkles size={12} />
                Commande live
              </div>
              <p className="mt-4 text-4xl font-black">
                {order.total_xof?.toLocaleString("fr-FR")} <span className="text-2xl">FCFA</span>
              </p>
              <p className="mt-1 text-sm text-white/75">
                {order.items?.length || 0} article{(order.items?.length || 0) > 1 ? "s" : ""}
              </p>
            </div>
            <div className="rounded-2xl bg-white/12 px-4 py-3 text-right backdrop-blur-sm shrink-0">
              <p className="text-[10px] font-black uppercase tracking-[0.16em] text-white/60">Type</p>
              <p className="mt-1 text-sm font-black">{ORDER_TYPE_LABELS[order.order_type] || order.order_type}</p>
            </div>
          </div>
        </div>

        {/* ── Client ── */}
        <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <p className="text-xs font-black uppercase tracking-[0.14em] mb-3" style={{ color: "var(--tx-muted)" }}>Client</p>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: "rgba(34,87,255,0.08)" }}>
                <span className="text-sm font-black" style={{ color: "var(--p-500)" }}>
                  {(order.customer_name || "C")[0].toUpperCase()}
                </span>
              </div>
              <div>
                <p className="font-black text-sm" style={{ color: "var(--tx-head)" }}>
                  {order.customer_name || "Client"}
                </p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <Phone size={12} style={{ color: "var(--tx-muted)" }} />
                  <p className="text-xs font-mono" style={{ color: "var(--tx-muted)" }}>{order.customer_phone || "—"}</p>
                </div>
              </div>
            </div>

            {deliveryAddress && (
              <div className="flex items-start gap-2 text-sm" style={{ color: "var(--tx-muted)" }}>
                <MapPin size={14} className="mt-0.5 shrink-0" />
                <span>{deliveryAddress}</span>
              </div>
            )}

            {order.pickup_code && (
              <div className="rounded-xl p-4 text-center" style={{ background: "rgba(34,87,255,0.06)", border: "1.5px dashed var(--p-500)" }}>
                <p className="text-xs font-black uppercase tracking-[0.14em] mb-2" style={{ color: "var(--p-500)" }}>
                  Code de retrait
                </p>
                <p className="font-mono text-3xl font-black tracking-[0.3em]" style={{ color: "var(--p-500)" }}>
                  {order.pickup_code}
                </p>
                <p className="text-xs mt-2" style={{ color: "var(--tx-muted)" }}>
                  Le client présente ce code pour récupérer sa commande
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ── Articles ── */}
        <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <p className="text-xs font-black uppercase tracking-[0.14em] mb-3" style={{ color: "var(--tx-muted)" }}>
            Articles ({order.items?.length || 0})
          </p>
          <div className="space-y-0">
            {order.items?.map((item: any, idx: number) => (
              <div
                key={item.id}
                className="flex items-center gap-3 py-3"
                style={{ borderBottom: idx < order.items.length - 1 ? "1px solid var(--bg-app)" : "none" }}
              >
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: "var(--bg-app)" }}>
                  <Package size={14} style={{ color: "var(--tx-muted)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate" style={{ color: "var(--tx-head)" }}>{item.product_name}</p>
                  {item.product_barcode && (
                    <p className="text-xs font-mono mt-0.5" style={{ color: "var(--tx-muted)" }}>{item.product_barcode}</p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-black" style={{ color: "var(--tx-head)" }}>
                    {(item.unit_price_xof * item.quantity).toLocaleString("fr-FR")} F
                  </p>
                  <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                    {item.quantity} × {item.unit_price_xof.toLocaleString("fr-FR")} F
                  </p>
                </div>
              </div>
            ))}
          </div>
          <div className="pt-3 mt-1 flex items-center justify-between" style={{ borderTop: "1px solid var(--bd)" }}>
            <p className="font-black text-sm" style={{ color: "var(--tx-head)" }}>Total</p>
            <p className="font-black text-xl" style={{ color: "var(--p-500)" }}>
              {order.total_xof?.toLocaleString("fr-FR")} FCFA
            </p>
          </div>
        </div>

        {/* ── Paiement ── */}
        {order.payment && (
          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <p className="text-xs font-black uppercase tracking-[0.14em] mb-3" style={{ color: "var(--tx-muted)" }}>Paiement</p>
            <div className="space-y-2">
              {[
                { label: "Opérateur",  value: order.payment.operator },
                { label: "Référence",  value: order.payment.transaction_ref, mono: true },
                { label: "Numéro",     value: order.payment.sender_phone || "—" },
              ].map(({ label, value, mono }) => (
                <div key={label} className="flex items-center justify-between">
                  <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{label}</p>
                  <p
                    className={`text-sm font-bold ${mono ? "font-mono" : ""}`}
                    style={{ color: "var(--tx-head)" }}
                  >
                    {value}
                  </p>
                </div>
              ))}
              <div className="flex items-center justify-between pt-1">
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>Statut</p>
                <span
                  className="text-xs font-black px-3 py-1 rounded-full"
                  style={{
                    background: order.payment.status === "confirmed" ? "rgba(0,214,143,0.1)" : "rgba(245,158,11,0.1)",
                    color: order.payment.status === "confirmed" ? "var(--s-600)" : "#D97706",
                  }}
                >
                  {order.payment.status === "confirmed" ? "Confirmé" : "En attente"}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ── Reçu & QR ── */}
        <div
          className="rounded-3xl p-5"
          style={{
            background: receipt
              ? "linear-gradient(180deg, rgba(0,214,143,0.10), rgba(0,214,143,0.04))"
              : "var(--bg-card)",
            border: `1px solid ${receipt ? "rgba(0,214,143,0.20)" : "var(--bd)"}`,
          }}
        >
          <div className="flex items-start gap-3">
            <div
              className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0"
              style={{
                background: receipt ? "rgba(0,214,143,0.14)" : "rgba(34,87,255,0.08)",
                color: receipt ? "var(--s-600)" : "var(--p-500)",
              }}
            >
              {receipt ? <CheckCircle size={20} /> : <ReceiptText size={20} />}
            </div>
            <div className="flex-1">
              <p className="font-black text-base" style={{ color: "var(--tx-head)" }}>
                {receipt ? "Reçu disponible" : "Reçu non généré"}
              </p>
              <p className="mt-1 text-xs leading-5" style={{ color: "var(--tx-muted)" }}>
                {receipt
                  ? `Reçu ${receipt.receipt_number} rattaché à cette commande.`
                  : "Disponible dès que le paiement est confirmé."}
              </p>
            </div>
          </div>

          {receipt ? (
            <div className="mt-4 grid grid-cols-3 gap-2">
              {receipt.pdf_url ? (
                <a
                  href={receipt.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-xs font-bold text-white"
                  style={{ background: "var(--tx-head)" }}
                >
                  <Printer size={14} />
                  PDF
                </a>
              ) : (
                <div className="flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-xs font-bold" style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}>
                  <Printer size={14} />
                  PDF...
                </div>
              )}

              <button
                onClick={() => qrMutation.mutate(receipt.id)}
                disabled={qrMutation.isPending}
                className="flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-xs font-bold"
                style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
              >
                <QrCode size={14} />
                {qrMutation.isPending ? "..." : "QR"}
              </button>

              <Link
                href={`/receipts/verify/${receipt.verification_code}`}
                className="flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-xs font-bold"
                style={{ background: "rgba(0,214,143,0.1)", color: "var(--s-600)" }}
              >
                <ExternalLink size={14} />
                Vérifier
              </Link>
            </div>
          ) : (
            <div className="mt-4">
              {canGenerateReceipt ? (
                <button
                  onClick={() => generateReceiptMutation.mutate(order.payment.id)}
                  disabled={generateReceiptMutation.isPending}
                  className="w-full py-4 rounded-2xl font-black text-white flex items-center justify-center gap-2"
                  style={{ background: "var(--s-600)" }}
                >
                  <ReceiptText size={18} />
                  {generateReceiptMutation.isPending ? "Génération..." : "Générer le reçu"}
                </button>
              ) : (
                <div className="rounded-xl px-4 py-3 text-xs" style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}>
                  La génération sera disponible une fois le paiement confirmé.
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Action principale ── */}
        {nextAction && (
          <button
            onClick={() => updateMutation.mutate(nextAction.to)}
            disabled={updateMutation.isPending}
            className="w-full py-5 rounded-2xl font-black text-lg text-white flex items-center justify-center gap-3 active:scale-95 transition-transform disabled:opacity-50"
            style={{ background: nextAction.bg, boxShadow: "var(--sh-brand)" }}
          >
            <nextAction.icon size={22} />
            {updateMutation.isPending ? "Mise à jour..." : nextAction.label}
          </button>
        )}

        {/* ── Annuler ── */}
        {["confirmed", "preparing"].includes(order.status) && (
          <button
            onClick={() => setConfirmCancel(true)}
            className="w-full py-4 rounded-2xl font-semibold"
            style={{ background: "rgba(220,38,38,0.06)", color: "#DC2626", border: "1.5px solid rgba(220,38,38,0.15)" }}
          >
            Annuler la commande
          </button>
        )}

        <div className="h-10" />
      </div>

      <ConfirmModal
        open={confirmCancel}
        title="Annuler la commande"
        message="Annuler cette commande ? Le client sera notifié. Cette action est irréversible."
        confirmLabel="Annuler la commande"
        variant="danger"
        onConfirm={() => {
          updateMutation.mutate("cancelled");
          setConfirmCancel(false);
        }}
        onCancel={() => setConfirmCancel(false)}
      />
    </div>
  );
}
