"use client";

export type OrderStatus =
  | "draft" | "pending" | "awaiting_payment" | "payment_submitted"
  | "confirmed" | "preparing" | "ready" | "out_for_delivery"
  | "delivered" | "cancelled" | "refunded";

const STATUS_CONFIG: Record<string, { label: string; bg: string; color: string }> = {
  draft:             { label: "Brouillon",         bg: "rgba(110,122,138,0.1)",  color: "var(--tx-muted)" },
  pending:           { label: "En attente",         bg: "rgba(245,158,11,0.1)",   color: "#D97706" },
  awaiting_payment:  { label: "Paiement attendu",   bg: "rgba(245,158,11,0.1)",   color: "#D97706" },
  payment_submitted: { label: "Paiement soumis",    bg: "rgba(34,87,255,0.08)",   color: "var(--p-600)" },
  confirmed:         { label: "Confirmée",          bg: "rgba(34,87,255,0.08)",   color: "var(--p-600)" },
  preparing:         { label: "En préparation",     bg: "rgba(245,158,11,0.08)",  color: "#D97706" },
  ready:             { label: "Prête",              bg: "rgba(0,214,143,0.1)",    color: "var(--s-600)" },
  out_for_delivery:  { label: "En livraison",       bg: "rgba(34,87,255,0.08)",   color: "var(--p-500)" },
  delivered:         { label: "Livrée",             bg: "rgba(0,214,143,0.1)",    color: "var(--s-600)" },
  cancelled:         { label: "Annulée",            bg: "rgba(220,38,38,0.08)",   color: "#DC2626" },
  refunded:          { label: "Remboursée",         bg: "rgba(220,38,38,0.08)",   color: "#DC2626" },
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    bg: "rgba(110,122,138,0.1)",
    color: "var(--tx-muted)",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${className}`}
      style={{ background: config.bg, color: config.color }}
    >
      {config.label}
    </span>
  );
}

export function getStatusLabel(status: string): string {
  return STATUS_CONFIG[status]?.label ?? status;
}
