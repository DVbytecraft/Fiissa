"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck, ChevronRight, CreditCard, Plus, Sparkles, X,
} from "lucide-react";
import { companiesApi, superadminApi } from "@/lib/api";
import { toast } from "sonner";

const BILLING_CYCLES = [
  { value: "monthly",  label: "Mensuel" },
  { value: "yearly",   label: "Annuel" },
  { value: "free",     label: "Gratuit" },
];

const FEATURE_DEFAULTS: Record<string, boolean> = {
  scan_go:        true,
  click_collect:  true,
  delivery:       false,
  loyalty:        false,
  webhooks:       false,
  multi_store:    false,
  api_access:     false,
  custom_receipt: false,
};

function CreatePlanModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [code,           setCode]           = useState("");
  const [name,           setName]           = useState("");
  const [billingCycle,   setBillingCycle]   = useState("monthly");
  const [amountXof,      setAmountXof]      = useState("0");
  const [commissionRate, setCommissionRate] = useState("0");
  const [features,       setFeatures]       = useState<Record<string, boolean>>({ ...FEATURE_DEFAULTS });

  const createMutation = useMutation({
    mutationFn: () =>
      superadminApi.createPlan({
        code:            code.trim().toLowerCase().replace(/\s+/g, "_"),
        name:            name.trim(),
        billing_cycle:   billingCycle,
        amount_xof:      parseInt(amountXof) || 0,
        commission_rate: parseFloat(commissionRate) || 0,
        features,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      toast.success("Plan créé");
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur création plan"),
  });

  const canSubmit = name.trim() && code.trim() && !createMutation.isPending;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center md:items-center"
      style={{ background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full md:max-w-lg rounded-t-3xl md:rounded-3xl overflow-y-auto"
        style={{ background: "#FFFFFF", maxHeight: "90dvh" }}
      >
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <h2 className="text-xl font-black" style={{ color: "#111111" }}>Nouveau plan</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ background: "var(--n-100)" }}
          >
            <X size={16} style={{ color: "#111111" }} />
          </button>
        </div>

        <div className="px-5 space-y-4 pb-6">
          <div>
            <p className="section-label mb-2">Nom du plan *</p>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex : Starter" className="input-mobile" />
          </div>

          <div>
            <p className="section-label mb-2">Code technique *</p>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value.toLowerCase().replace(/\s+/g, "_"))}
              placeholder="Ex : starter"
              className="input-mobile font-mono"
            />
          </div>

          <div>
            <p className="section-label mb-2">Cycle de facturation</p>
            <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--bd)" }}>
              {BILLING_CYCLES.map((bc, i) => (
                <button
                  key={bc.value}
                  onClick={() => setBillingCycle(bc.value)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left"
                  style={{ borderBottom: i < BILLING_CYCLES.length - 1 ? "1px solid var(--bd)" : "none", background: billingCycle === bc.value ? "var(--n-50)" : "#fff" }}
                >
                  <span className="text-sm font-bold" style={{ color: "#111111" }}>{bc.label}</span>
                  <div
                    className="w-5 h-5 rounded-full border-2 flex items-center justify-center"
                    style={{ borderColor: billingCycle === bc.value ? "#111111" : "var(--bd)", background: billingCycle === bc.value ? "#111111" : "transparent" }}
                  >
                    {billingCycle === bc.value && <div className="w-2 h-2 rounded-full bg-white" />}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="section-label mb-2">Tarif mensuel (FCFA)</p>
              <input type="number" value={amountXof} onChange={(e) => setAmountXof(e.target.value)} className="input-mobile" min="0" />
            </div>
            <div>
              <p className="section-label mb-2">Commission (%)</p>
              <input type="number" value={commissionRate} onChange={(e) => setCommissionRate(e.target.value)} className="input-mobile" min="0" max="100" step="0.1" />
            </div>
          </div>

          <div>
            <p className="section-label mb-2">Fonctionnalités incluses</p>
            <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--bd)" }}>
              {Object.entries(features).map(([key, val], i, arr) => (
                <div
                  key={key}
                  className="flex items-center justify-between px-4 py-3"
                  style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--bd)" : "none" }}
                >
                  <p className="text-sm font-bold" style={{ color: "#111111" }}>
                    {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </p>
                  <button
                    onClick={() => setFeatures((prev) => ({ ...prev, [key]: !prev[key] }))}
                    className="relative w-11 h-6 rounded-full transition-colors flex-shrink-0"
                    style={{ background: val ? "#111111" : "var(--n-200)" }}
                  >
                    <div
                      className="absolute top-1 w-4 h-4 rounded-full bg-white transition-all"
                      style={{ left: val ? "calc(100% - 20px)" : 4 }}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => createMutation.mutate()}
            disabled={!canSubmit}
            className="btn-primary w-full"
          >
            {createMutation.isPending ? "Création…" : "Créer le plan"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SuperAdminPlansPage() {
  const [showCreate, setShowCreate] = useState(false);

  const { data: plansData, isLoading } = useQuery({
    queryKey: ["plans"],
    queryFn: () => companiesApi.getPlans().then((r) => r.data),
  });

  const plans: any[] = Array.isArray(plansData) ? plansData : plansData?.items ?? [];

  const CYCLE_LABELS: Record<string, string> = { monthly: "Mensuel", yearly: "Annuel", free: "Gratuit" };

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      <div className="px-5 pt-5 pb-4" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl flex items-center justify-center" style={{ background: "rgba(34,87,255,0.08)" }}>
              <CreditCard size={20} style={{ color: "var(--p-500)" }} />
            </div>
            <div>
              <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>Plans</h1>
              <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{plans.length} plan{plans.length > 1 ? "s" : ""} disponible{plans.length > 1 ? "s" : ""}</p>
            </div>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-bold text-white"
            style={{ background: "#111111" }}
          >
            <Plus size={14} />
            Créer
          </button>
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        {isLoading && (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}>
                <div className="skeleton h-16 w-full" />
              </div>
            ))}
          </div>
        )}

        {!isLoading && plans.length === 0 && (
          <div className="pt-20 text-center">
            <CreditCard size={40} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
            <p className="font-bold" style={{ color: "#111111" }}>Aucun plan créé</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>Créez votre premier plan tarifaire.</p>
            <button onClick={() => setShowCreate(true)} className="btn-primary mt-4 mx-auto" style={{ maxWidth: 200 }}>
              Créer un plan
            </button>
          </div>
        )}

        {plans.map((plan) => {
          const features = plan.features ?? {};
          const enabledCount = Object.values(features).filter(Boolean).length;
          return (
            <div
              key={plan.id}
              className="rounded-2xl overflow-hidden"
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
            >
              <div className="px-4 py-4 flex items-start gap-3">
                <div
                  className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0"
                  style={{ background: plan.amount_xof === 0 ? "rgba(0,214,143,0.1)" : "rgba(34,87,255,0.08)" }}
                >
                  {plan.amount_xof === 0
                    ? <Sparkles size={20} style={{ color: "var(--s-600)" }} />
                    : <BadgeCheck size={20} style={{ color: "var(--p-500)" }} />
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-black text-base" style={{ color: "#111111" }}>{plan.name}</p>
                    <span
                      className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full"
                      style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
                    >
                      {plan.code}
                    </span>
                  </div>
                  <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {CYCLE_LABELS[plan.billing_cycle] ?? plan.billing_cycle}
                    {plan.commission_rate > 0 ? ` · ${plan.commission_rate}% commission` : ""}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="font-black text-lg" style={{ color: "#111111" }}>
                    {plan.amount_xof === 0 ? "Gratuit" : `${(plan.amount_xof ?? 0).toLocaleString("fr-FR")} F`}
                  </p>
                  <p className="text-[10px]" style={{ color: "var(--tx-muted)" }}>
                    {enabledCount} fonctionnalité{enabledCount > 1 ? "s" : ""}
                  </p>
                </div>
              </div>

              {Object.keys(features).length > 0 && (
                <div className="px-4 pb-3 flex flex-wrap gap-1.5">
                  {Object.entries(features)
                    .filter(([, v]) => v)
                    .map(([k]) => (
                      <span
                        key={k}
                        className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                        style={{ background: "var(--n-100)", color: "var(--tx-body)" }}
                      >
                        {k.replace(/_/g, " ")}
                      </span>
                    ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {showCreate && <CreatePlanModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
