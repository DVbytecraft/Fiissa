"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Calendar, CheckCircle, ChevronRight, CreditCard, XCircle } from "lucide-react";
import { toast } from "sonner";
import { companiesApi } from "@/lib/api";

export default function MerchantSubscriptionPage() {
  const queryClient = useQueryClient();

  const { data: subscription, isLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => companiesApi.getMySubscription().then((response) => response.data),
  });

  const { data: plansData } = useQuery({
    queryKey: ["subscription-plans"],
    queryFn: () => companiesApi.getPlans().then((response) => response.data),
  });

  const { data: invoicesData } = useQuery({
    queryKey: ["subscription-invoices"],
    queryFn: () => companiesApi.getMySubscriptionInvoices().then((response) => response.data),
  });

  const { data: renewalsData } = useQuery({
    queryKey: ["subscription-renewals"],
    queryFn: () => companiesApi.getMySubscriptionRenewals().then((response) => response.data),
  });

  const changePlanMutation = useMutation({
    mutationFn: (planCode: string) => companiesApi.changeSubscription(planCode),
    onSuccess: () => {
      toast.success("Plan mis a jour");
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
      queryClient.invalidateQueries({ queryKey: ["subscription-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["subscription-renewals"] });
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur abonnement"),
  });

  const payInvoiceMutation = useMutation({
    mutationFn: (invoiceId: string) => companiesApi.payMySubscriptionInvoice(invoiceId),
    onSuccess: () => {
      toast.success("Facture marquee comme payee");
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
      queryClient.invalidateQueries({ queryKey: ["subscription-invoices"] });
      queryClient.invalidateQueries({ queryKey: ["subscription-renewals"] });
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur facture"),
  });

  const plans = useMemo(() => {
    const items = plansData?.items ?? [];
    return items.map((plan: any, index: number) => ({
      id: plan.code,
      name: plan.name,
      price: plan.amount_xof ?? 0,
      desc: plan.billing_cycle === "yearly" ? "Facturation annuelle" : "Facturation mensuelle",
      features: Array.isArray(plan.features) ? plan.features : Object.keys(plan.features || {}),
      unavailable: [],
      recommended: index === 1,
    }));
  }, [plansData]);

  const invoices = invoicesData?.items ?? [];
  const renewals = renewalsData?.items ?? [];

  const currentPlan = subscription?.plan || "pro";
  const status = subscription?.status || "active";
  const expirationSource =
    subscription?.expires_at || subscription?.current_period_end || subscription?.trial_ends_at;
  const expiresAt = expirationSource
    ? new Date(expirationSource).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;
  const daysLeft = expirationSource
    ? Math.ceil((new Date(expirationSource).getTime() - Date.now()) / 86400000)
    : null;

  const isExpiringSoon = daysLeft !== null && daysLeft <= 14 && daysLeft > 0;
  const isExpired = status === "expired" || status === "cancelled" || (daysLeft !== null && daysLeft <= 0);
  const isTrial = status === "trial";

  return (
    <div className="min-h-screen pb-24" style={{ background: "var(--bg-app)" }}>
      <div
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
        className="px-6 pt-12 pb-6"
      >
        <h1 style={{ color: "var(--tx-head)" }} className="text-xl font-bold mb-1">
          Abonnement
        </h1>
        <p style={{ color: "var(--tx-muted)" }} className="text-sm">
          Gere ton plan Fiissa
        </p>
      </div>

      <div className="px-4 py-4 space-y-4">
        {isLoading ? (
          <div style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
            <div className="skeleton h-24 w-full" />
          </div>
        ) : (
          <div
            style={{
              background: isExpired
                ? "rgba(220,38,38,0.04)"
                : isExpiringSoon
                  ? "rgba(245,158,11,0.06)"
                  : "rgba(0,214,143,0.06)",
              border: `1px solid ${
                isExpired
                  ? "rgba(220,38,38,0.2)"
                  : isExpiringSoon
                    ? "rgba(245,158,11,0.2)"
                    : "rgba(0,214,143,0.2)"
              }`,
            }}
            className="rounded-2xl p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    style={{
                      background: isExpired ? "#DC2626" : isExpiringSoon ? "#F59E0B" : "var(--s-500)",
                    }}
                    className="text-white text-xs font-bold px-2.5 py-0.5 rounded-full uppercase"
                  >
                    {isTrial ? "Essai" : currentPlan.toUpperCase()}
                  </span>
                  {isExpired && <span className="text-xs font-semibold text-red-500">Expire</span>}
                  {isExpiringSoon && !isExpired && (
                    <span className="text-xs font-semibold text-amber-600">Expire dans {daysLeft}j</span>
                  )}
                </div>
                {expiresAt && (
                  <p style={{ color: "var(--tx-muted)" }} className="text-sm flex items-center gap-1.5 mt-1">
                    <Calendar size={14} />
                    Expire le {expiresAt}
                  </p>
                )}
              </div>
              {isExpired || isExpiringSoon ? (
                <AlertTriangle size={24} className={isExpired ? "text-red-500" : "text-amber-500"} />
              ) : (
                <CheckCircle size={24} style={{ color: "var(--s-500)" }} />
              )}
            </div>
          </div>
        )}

        <div>
          <h2 style={{ color: "var(--tx-head)" }} className="font-bold text-base mb-3 px-1">
            Changer de plan
          </h2>
          <div className="space-y-3">
            {plans.map((plan: any) => {
              const isCurrent = plan.id === currentPlan;
              return (
                <div
                  key={plan.id}
                  style={{
                    background: "var(--bg-card)",
                    border: `2px solid ${
                      isCurrent ? "var(--p-500)" : plan.recommended ? "rgba(34,87,255,0.15)" : "var(--bd)"
                    }`,
                  }}
                  className="rounded-2xl overflow-hidden"
                >
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 style={{ color: "var(--tx-head)" }} className="font-bold text-base">
                            {plan.name}
                          </h3>
                          {plan.recommended && !isCurrent && (
                            <span
                              style={{ background: "var(--p-500)" }}
                              className="text-white text-xs font-bold px-2 py-0.5 rounded-full"
                            >
                              Recommande
                            </span>
                          )}
                          {isCurrent && (
                            <span
                              style={{ background: "rgba(0,214,143,0.1)", color: "var(--s-500)" }}
                              className="text-xs font-bold px-2 py-0.5 rounded-full"
                            >
                              Actuel
                            </span>
                          )}
                        </div>
                        <p style={{ color: "var(--tx-muted)" }} className="text-xs mt-0.5">
                          {plan.desc}
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <p style={{ color: "var(--tx-head)" }} className="text-xl font-semibold">
                          {plan.price.toLocaleString("fr-FR")} F
                        </p>
                        <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                          / cycle
                        </p>
                      </div>
                    </div>

                    <ul className="space-y-1.5 mb-3">
                      {plan.features.map((feature: string) => (
                        <li key={feature} className="flex items-center gap-2 text-sm">
                          <CheckCircle size={14} style={{ color: "var(--s-500)" }} className="shrink-0" />
                          <span style={{ color: "var(--tx-head)" }}>{feature}</span>
                        </li>
                      ))}
                      {plan.unavailable.map((feature: string) => (
                        <li key={feature} className="flex items-center gap-2 text-sm">
                          <XCircle size={14} style={{ color: "var(--tx-muted)" }} className="shrink-0" />
                          <span style={{ color: "var(--tx-muted)" }}>{feature}</span>
                        </li>
                      ))}
                    </ul>

                    {!isCurrent && (
                      <button
                        onClick={() => changePlanMutation.mutate(plan.id)}
                        disabled={changePlanMutation.isPending}
                        style={
                          plan.recommended
                            ? { background: "var(--p-500)", boxShadow: "var(--sh-brand)" }
                            : { background: "var(--bg-app)", border: "1px solid var(--bd)" }
                        }
                        className="w-full py-2.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        <span style={{ color: plan.recommended ? "#fff" : "var(--tx-head)" }}>
                          Passer au plan {plan.name}
                        </span>
                        <ChevronRight
                          size={16}
                          style={{ color: plan.recommended ? "#fff" : "var(--tx-muted)" }}
                        />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-3">
          <h2 style={{ color: "var(--tx-head)" }} className="font-bold text-base px-1">
            Factures d'abonnement
          </h2>
          {!invoices.length ? (
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }} className="rounded-2xl p-4">
              <p style={{ color: "var(--tx-muted)" }} className="text-sm">
                Aucune facture d'abonnement pour le moment.
              </p>
            </div>
          ) : (
            invoices.slice(0, 5).map((invoice: any) => (
              <div key={invoice.id} style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }} className="rounded-2xl p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p style={{ color: "var(--tx-head)" }} className="font-bold text-sm">
                      {invoice.invoice_number}
                    </p>
                    <p style={{ color: "var(--tx-muted)" }} className="text-xs mt-0.5">
                      Statut: {invoice.status}
                    </p>
                  </div>
                  <p style={{ color: "var(--p-500)" }} className="font-semibold text-base">
                    {(invoice.total_xof ?? invoice.amount_xof ?? 0).toLocaleString("fr-FR")} F
                  </p>
                </div>
                {invoice.status !== "paid" && (
                  <button
                    onClick={() => payInvoiceMutation.mutate(invoice.id)}
                    disabled={payInvoiceMutation.isPending}
                    style={{ background: "var(--p-500)" }}
                    className="mt-3 w-full py-2.5 text-white rounded-xl font-semibold text-sm disabled:opacity-50"
                  >
                    {payInvoiceMutation.isPending ? "Traitement..." : "Marquer comme payee"}
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        <div className="space-y-3">
          <h2 style={{ color: "var(--tx-head)" }} className="font-bold text-base px-1">
            Historique des renouvellements
          </h2>
          {!renewals.length ? (
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }} className="rounded-2xl p-4">
              <p style={{ color: "var(--tx-muted)" }} className="text-sm">
                Aucun renouvellement enregistre.
              </p>
            </div>
          ) : (
            renewals.slice(0, 5).map((renewal: any) => (
              <div key={renewal.id} style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }} className="rounded-2xl p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p style={{ color: "var(--tx-head)" }} className="font-bold text-sm">
                      {renewal.status}
                    </p>
                    <p style={{ color: "var(--tx-muted)" }} className="text-xs mt-0.5">
                      {renewal.previous_period_end
                        ? `Ancienne fin: ${new Date(renewal.previous_period_end).toLocaleDateString("fr-FR")}`
                        : "Aucune periode precedente"}
                    </p>
                    <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                      {renewal.new_period_end
                        ? `Nouvelle fin: ${new Date(renewal.new_period_end).toLocaleDateString("fr-FR")}`
                        : "Nouvelle date non definie"}
                    </p>
                  </div>
                  <span
                    style={{
                      background:
                        renewal.status === "processed"
                          ? "rgba(0,214,143,0.1)"
                          : renewal.status === "failed"
                            ? "rgba(220,38,38,0.08)"
                            : "rgba(245,158,11,0.08)",
                      color:
                        renewal.status === "processed"
                          ? "var(--s-500)"
                          : renewal.status === "failed"
                            ? "#DC2626"
                            : "#D97706",
                    }}
                    className="text-xs font-bold px-2 py-0.5 rounded-full"
                  >
                    {renewal.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        <div
          style={{ background: "rgba(34,87,255,0.04)", border: "1px solid rgba(34,87,255,0.1)" }}
          className="rounded-2xl p-4"
        >
          <div className="flex items-start gap-3">
            <CreditCard size={20} style={{ color: "var(--p-500)" }} className="shrink-0 mt-0.5" />
            <div>
              <p style={{ color: "var(--tx-head)" }} className="text-sm font-semibold mb-1">
                Paiement par Mobile Money
              </p>
              <p style={{ color: "var(--tx-muted)" }} className="text-xs leading-relaxed">
                Les abonnements Fiissa sont payables par Wave, Orange Money, Free Money ou MTN MoMo.
                Contacte l'equipe si tu as besoin d'un accompagnement.
              </p>
              <a
                href="mailto:support@fiissa.com"
                style={{ color: "var(--p-500)" }}
                className="text-xs font-semibold mt-2 block"
              >
                support@fiissa.com {"->"}
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
