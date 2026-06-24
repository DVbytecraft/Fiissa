"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, XCircle, Phone, Hash, Building } from "lucide-react";
import { paymentsApi } from "@/lib/api";
import { toast } from "sonner";

function PaymentCard({ payment, onAction }: { payment: any; onAction: () => void }) {
  const [rejectReason, setRejectReason] = useState("");
  const [showReject, setShowReject] = useState(false);
  const queryClient = useQueryClient();

  const confirmMutation = useMutation({
    mutationFn: () => paymentsApi.confirm(payment.id, true),
    onSuccess: () => {
      toast.success("Paiement confirmé ✓");
      queryClient.invalidateQueries({ queryKey: ["pending-payments"] });
      onAction();
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur"),
  });

  const rejectMutation = useMutation({
    mutationFn: () => paymentsApi.confirm(payment.id, false, rejectReason),
    onSuccess: () => {
      toast.success("Paiement rejeté");
      setShowReject(false);
      queryClient.invalidateQueries({ queryKey: ["pending-payments"] });
      onAction();
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur"),
  });

  const operatorLabels: Record<string, string> = {
    wave: "Wave",
    orange_money: "Orange Money",
    mtn_momo: "MTN MoMo",
    moov_money: "Moov Money",
    free_money: "Free Money",
  };

  const waitMinutes = payment.submitted_at
    ? Math.floor((Date.now() - new Date(payment.submitted_at).getTime()) / 60000)
    : 0;

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between" style={{ background: "#FFFBEB", borderBottom: "1px solid #FDE68A" }}>
        <div>
          <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{payment.payment_number}</p>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>Commande en attente</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-black" style={{ color: "var(--tx-head)" }}>{payment.amount_xof?.toLocaleString("fr-FR")}</p>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>FCFA</p>
        </div>
      </div>

      {/* Détails */}
      <div className="px-4 py-3 space-y-2">
        <div className="flex items-center gap-2 text-sm">
          <Building size={14} style={{ color: "var(--tx-muted)" }} />
          <span style={{ color: "var(--tx-muted)" }}>Opérateur :</span>
          <span className="font-semibold" style={{ color: "var(--tx-head)" }}>{operatorLabels[payment.operator] || payment.operator}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Hash size={14} style={{ color: "var(--tx-muted)" }} />
          <span style={{ color: "var(--tx-muted)" }}>Référence :</span>
          <span className="font-mono font-bold" style={{ color: "var(--tx-head)" }}>{payment.transaction_ref}</span>
        </div>
        {payment.sender_phone && (
          <div className="flex items-center gap-2 text-sm">
            <Phone size={14} style={{ color: "var(--tx-muted)" }} />
            <span style={{ color: "var(--tx-muted)" }}>N° payeur :</span>
            <span className="font-semibold" style={{ color: "var(--tx-head)" }}>{payment.sender_phone}</span>
          </div>
        )}
        {waitMinutes > 0 && (
          <p className="text-xs font-medium" style={{ color: waitMinutes > 15 ? "#DC2626" : "var(--tx-muted)" }}>
            ⏱ Attendu depuis {waitMinutes} min
          </p>
        )}
      </div>

      {/* Instructions */}
      <div className="px-4 py-2 text-xs font-medium" style={{ background: "rgba(34,87,255,0.06)", color: "var(--p-500)" }}>
        Vérifiez sur votre app {operatorLabels[payment.operator] || payment.operator} que{" "}
        <strong>{payment.amount_xof?.toLocaleString("fr-FR")} FCFA</strong> ont été reçus de{" "}
        <strong>{payment.sender_phone}</strong>.
      </div>

      {/* Actions */}
      {!showReject ? (
        <div className="px-4 py-3 flex gap-3">
          <button
            onClick={() => confirmMutation.mutate()}
            disabled={confirmMutation.isPending}
            className="flex-1 py-3 text-white rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform disabled:opacity-50"
            style={{ background: "var(--s-500)", boxShadow: "var(--sh-green)" }}
          >
            {confirmMutation.isPending ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <><CheckCircle size={18} /> Confirmer</>
            )}
          </button>
          <button
            onClick={() => setShowReject(true)}
            className="flex-1 py-3 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 border-2"
            style={{ background: "#FEF2F2", color: "#DC2626", borderColor: "#FCA5A5" }}
          >
            <XCircle size={18} />
            Rejeter
          </button>
        </div>
      ) : (
        <div className="px-4 py-3 space-y-2">
          <input
            type="text"
            placeholder="Raison du rejet (obligatoire)"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            className="w-full py-3 px-3 rounded-xl text-sm outline-none border-2"
            style={{ borderColor: "#FCA5A5", color: "var(--tx-body)" }}
          />
          <div className="flex gap-2">
            <button
              onClick={() => setShowReject(false)}
              className="flex-1 py-3 rounded-xl font-semibold text-sm"
              style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}
            >
              Annuler
            </button>
            <button
              onClick={() => rejectMutation.mutate()}
              disabled={!rejectReason.trim() || rejectMutation.isPending}
              className="flex-1 py-3 text-white rounded-xl font-bold text-sm disabled:opacity-50 active:scale-95"
              style={{ background: "#DC2626" }}
            >
              {rejectMutation.isPending ? "..." : "Confirmer rejet"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MerchantPaymentsPage() {
  const queryClient = useQueryClient();

  const { data: payments, isLoading, refetch } = useQuery({
    queryKey: ["pending-payments"],
    queryFn: () => paymentsApi.getPending().then((r) => r.data),
    refetchInterval: 15000,
  });

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div className="px-5 pt-4 pb-4" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>Paiements à vérifier</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
              {payments?.length || 0} en attente
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="text-sm font-semibold py-1.5 px-3 rounded-full"
            style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
          >
            Actualiser
          </button>
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        {isLoading &&
          [...Array(2)].map((_, i) => (
            <div key={i} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}>
              <div className="skeleton h-24 w-full" />
            </div>
          ))}

        {!isLoading && payments?.length === 0 && (
          <div className="text-center py-16">
            <CheckCircle size={64} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p className="font-semibold" style={{ color: "var(--tx-muted)" }}>Aucun paiement en attente</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>Tous les paiements ont été traités</p>
          </div>
        )}

        {payments?.map((payment: any) => (
          <PaymentCard
            key={payment.id}
            payment={payment}
            onAction={() => queryClient.invalidateQueries({ queryKey: ["pending-payments"] })}
          />
        ))}
      </div>
    </div>
  );
}
