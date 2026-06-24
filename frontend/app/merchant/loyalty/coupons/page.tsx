"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Clock, Plus, Tag, TicketX } from "lucide-react";
import { loyaltyApi } from "@/lib/api";
import { toast } from "sonner";
import { useDebounce } from "@/lib/hooks";

export default function MerchantLoyaltyCouponsPage() {
  const [showForm, setShowForm] = useState(false);
  const [customerId, setCustomerId] = useState("");
  const [discountType, setDiscountType] = useState<"pct" | "fixed">("pct");
  const [discountValue, setDiscountValue] = useState("10");
  const [minOrder, setMinOrder] = useState("0");
  const [expiresAt, setExpiresAt] = useState("");
  const [searchCustomer, setSearchCustomer] = useState("");
  const debouncedSearch = useDebounce(searchCustomer, 350);

  const queryClient = useQueryClient();

  const { data: scores } = useQuery({
    queryKey: ["customer-scores", null, debouncedSearch],
    queryFn: () => loyaltyApi.getCustomerScores({ limit: 10 }).then((r) => r.data),
  });

  const issueMutation = useMutation({
    mutationFn: () =>
      loyaltyApi.issueCoupon({
        customer_id: customerId,
        discount_type: discountType,
        discount_value: parseFloat(discountValue) || 0,
        min_order_xof: parseInt(minOrder, 10) || 0,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
      }),
    onSuccess: () => {
      setCustomerId(""); setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["customer-scores"] });
      toast.success("Coupon émis — le client le recevra dans son wallet");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur émission coupon"),
  });

  const customers: any[] = scores ?? [];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div
        className="px-5 pt-4 pb-4 flex items-center gap-3"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <Link href="/merchant/loyalty" style={{ color: "var(--tx-muted)" }}>
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>Coupons</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Émettre des coupons de réduction pour vos clients
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: "var(--p-500)", color: "#fff" }}
          aria-label="Émettre un coupon"
        >
          <Plus size={18} />
        </button>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Formulaire d'émission */}
        {showForm && (
          <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Émettre un coupon</h2>

            {/* Sélection client */}
            <div>
              <label className="text-xs font-semibold mb-1.5 block" style={{ color: "var(--tx-muted)" }}>
                Client (ID ou sélection ci-dessous)
              </label>
              <input
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                placeholder="UUID du client"
                className="input-mobile font-mono text-xs"
              />
            </div>

            {/* Liste clients RFM */}
            {customers.length > 0 && (
              <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--bd)" }}>
                <p className="text-xs font-bold px-3 py-2" style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}>
                  Sélectionner un client
                </p>
                <div className="divide-y" style={{ borderColor: "var(--bg-app)" }}>
                  {customers.slice(0, 5).map((score: any) => (
                    <button
                      key={score.customer_id}
                      onClick={() => setCustomerId(score.customer_id)}
                      className="w-full flex items-center justify-between px-3 py-3 text-left active:opacity-70"
                      style={{
                        background: customerId === score.customer_id ? "var(--p-50)" : "var(--bg-card)",
                        borderLeft: customerId === score.customer_id ? "3px solid var(--p-500)" : "3px solid transparent",
                      }}
                    >
                      <div>
                        <p className="font-mono text-xs" style={{ color: "var(--tx-head)" }}>
                          {score.customer_id.slice(0, 16)}…
                        </p>
                        <p className="text-[10px] mt-0.5" style={{ color: "var(--tx-muted)" }}>
                          {score.segment} · {score.order_count} cmd · {score.total_spent_xof.toLocaleString("fr-FR")} F
                        </p>
                      </div>
                      <span className="font-black text-base" style={{ color: "var(--p-500)" }}>
                        {score.rfm_score}/15
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Type et valeur */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Type</label>
                <select
                  value={discountType}
                  onChange={(e) => setDiscountType(e.target.value as "pct" | "fixed")}
                  className="input-mobile"
                >
                  <option value="pct">Remise %</option>
                  <option value="fixed">Montant fixe (F)</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>
                  Valeur {discountType === "pct" ? "(%)" : "(F)"}
                </label>
                <input
                  value={discountValue}
                  onChange={(e) => setDiscountValue(e.target.value)}
                  className="input-mobile"
                  type="number"
                  min="0"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Achat min. (F)</label>
                <input value={minOrder} onChange={(e) => setMinOrder(e.target.value)} className="input-mobile" type="number" min="0" />
              </div>
              <div>
                <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Expire le</label>
                <input
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                  className="input-mobile"
                  type="date"
                  min={new Date().toISOString().slice(0, 10)}
                />
              </div>
            </div>

            {/* Aperçu */}
            {discountValue && (
              <div className="rounded-xl p-3 flex items-center gap-3" style={{ background: "var(--p-50)", border: "1px solid rgba(34,87,255,0.15)" }}>
                <Tag size={16} style={{ color: "var(--p-500)" }} />
                <p className="text-sm font-bold" style={{ color: "var(--p-600)" }}>
                  Coupon : {discountType === "pct" ? `−${discountValue}%` : `−${parseFloat(discountValue).toLocaleString("fr-FR")} F`}
                  {parseInt(minOrder) > 0 ? ` dès ${parseInt(minOrder).toLocaleString("fr-FR")} F` : ""}
                  {expiresAt ? ` · jusqu'au ${new Date(expiresAt).toLocaleDateString("fr-FR")}` : ""}
                </p>
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => setShowForm(false)}
                className="flex-1 py-3 rounded-xl font-semibold text-sm"
                style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}
              >
                Annuler
              </button>
              <button
                onClick={() => issueMutation.mutate()}
                disabled={!customerId || !discountValue || issueMutation.isPending}
                className="flex-1 btn-primary"
              >
                {issueMutation.isPending ? "Émission…" : "Émettre"}
              </button>
            </div>
          </div>
        )}

        {/* Info */}
        <div className="rounded-2xl p-4 flex items-start gap-3" style={{ background: "rgba(34,87,255,0.04)", border: "1px solid rgba(34,87,255,0.1)" }}>
          <Tag size={16} className="flex-shrink-0 mt-0.5" style={{ color: "var(--p-500)" }} />
          <div>
            <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>Comment fonctionnent les coupons ?</p>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--tx-muted)" }}>
              Un coupon émis apparaît instantanément dans le wallet du client (onglet Coupons).
              Il peut l'utiliser en caisse en présentant le QR code, ou l'appliquer lors d'une commande en ligne.
              Les coupons sont liés à votre enseigne uniquement.
            </p>
          </div>
        </div>

        {/* Liste clients pour ciblage */}
        <div>
          <p className="text-xs font-bold uppercase tracking-wide mb-3" style={{ color: "var(--tx-muted)" }}>
            Clients actifs — cibler pour émettre un coupon
          </p>

          {customers.length === 0 && (
            <div className="rounded-2xl p-6 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
              <TicketX size={36} className="mx-auto mb-3" style={{ color: "var(--bd)" }} />
              <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>
                Aucun client avec score RFM
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
                Recalculez les scores depuis la page Intelligence clients.
              </p>
              <Link
                href="/merchant/customers"
                className="inline-block mt-4 px-4 py-2 rounded-xl font-bold text-sm text-white"
                style={{ background: "var(--p-500)" }}
              >
                Voir les clients
              </Link>
            </div>
          )}

          <div className="space-y-2">
            {customers.map((score: any) => (
              <div
                key={score.customer_id}
                className="rounded-2xl p-4 flex items-center gap-3"
                style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-xs font-semibold" style={{ color: "var(--tx-head)" }}>
                    Client · {score.customer_id.slice(0, 12)}…
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                      style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-600)" }}
                    >
                      {score.segment}
                    </span>
                    <span className="text-[10px]" style={{ color: "var(--tx-muted)" }}>
                      {score.order_count} cmd · {score.total_spent_xof.toLocaleString("fr-FR")} F
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setCustomerId(score.customer_id);
                    setShowForm(true);
                  }}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold flex-shrink-0"
                  style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
                >
                  <Plus size={12} /> Coupon
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
