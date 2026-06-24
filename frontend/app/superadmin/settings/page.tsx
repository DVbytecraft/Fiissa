"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Clock, Globe, Mail, PlusCircle, Settings, Shield, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

const PLATFORM_INFO = [
  {
    icon: Globe,
    label: "Plateforme",
    color: "var(--p-500)",
    items: [
      { key: "Nom",            value: "Fiissa" },
      { key: "Email support",  value: "support@fiissa.com" },
      { key: "Devise",         value: "XOF (FCFA)" },
      { key: "Zone UEMOA",     value: "Sénégal, Côte d'Ivoire, Mali…" },
    ],
  },
  {
    icon: Shield,
    label: "Sécurité",
    color: "#7C3AED",
    items: [
      { key: "Expiration OTP",     value: "10 minutes" },
      { key: "Tentatives max",     value: "5 avant blocage" },
      { key: "Durée session",      value: "30 jours" },
      { key: "Chiffrement",        value: "AES-256-GCM" },
    ],
  },
  {
    icon: Bell,
    label: "Notifications",
    color: "#D97706",
    items: [
      { key: "Email",  value: "Brevo SMTP / API" },
      { key: "SMS",    value: "Désactivé (V2)" },
      { key: "Webhook", value: "HMAC-SHA256 + retry x5" },
    ],
  },
];

export default function SuperAdminSettingsPage() {
  const queryClient = useQueryClient();
  const [planCode, setPlanCode]             = useState("");
  const [planName, setPlanName]             = useState("");
  const [billingCycle, setBillingCycle]     = useState("monthly");
  const [amountXof, setAmountXof]           = useState("0");
  const [commissionRate, setCommissionRate] = useState("0");

  const { data: auditLogs } = useQuery({
    queryKey: ["superadmin-audit-logs"],
    queryFn: () => api.get("/superadmin/audit-logs").then((r) => r.data),
  });

  const createPlanMutation = useMutation({
    mutationFn: () =>
      api.post("/superadmin/plans", {
        code: planCode,
        name: planName,
        billing_cycle: billingCycle,
        amount_xof: parseInt(amountXof, 10) || 0,
        commission_rate: parseFloat(commissionRate) || 0,
      }),
    onSuccess: () => {
      toast.success("Plan d'abonnement créé");
      setPlanCode(""); setPlanName(""); setBillingCycle("monthly"); setAmountXof("0"); setCommissionRate("0");
      queryClient.invalidateQueries({ queryKey: ["superadmin-audit-logs"] });
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur plan"),
  });

  const logs = Array.isArray(auditLogs) ? auditLogs : [];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      {/* Hero */}
      <div className="px-5 pt-6 pb-5" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex items-center gap-2 mb-1">
          <Settings size={16} style={{ color: "var(--p-500)" }} />
          <span className="text-xs font-black uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
            Configuration
          </span>
        </div>
        <h1 className="text-2xl font-black" style={{ color: "var(--tx-head)" }}>Paramètres plateforme</h1>
        <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
          Gouvernance globale Fiissa — plans, sécurité, notifications.
        </p>
      </div>

      <div className="px-4 py-5 space-y-4">

        {/* Infos plateforme */}
        {PLATFORM_INFO.map(({ icon: Icon, label, color, items }) => (
          <div
            key={label}
            className="rounded-2xl overflow-hidden"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
          >
            <div
              className="px-4 py-3 flex items-center gap-2"
              style={{ borderBottom: "1px solid var(--bd)", background: "var(--n-50)" }}
            >
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
                <Icon size={15} style={{ color }} />
              </div>
              <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{label}</h2>
            </div>
            <div>
              {items.map(({ key, value }, idx) => (
                <div
                  key={key}
                  className="px-4 py-3 flex items-center justify-between"
                  style={{ borderTop: idx > 0 ? "1px solid var(--bd)" : undefined }}
                >
                  <span className="text-sm" style={{ color: "var(--tx-muted)" }}>{key}</span>
                  <span className="text-sm font-semibold" style={{ color: "var(--tx-head)" }}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Créer un plan */}
        <div
          className="rounded-2xl overflow-hidden"
          style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
        >
          <div
            className="px-4 py-3 flex items-center gap-2"
            style={{ borderBottom: "1px solid var(--bd)", background: "var(--n-50)" }}
          >
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "rgba(34,87,255,0.1)" }}>
              <PlusCircle size={15} style={{ color: "var(--p-500)" }} />
            </div>
            <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Créer un plan d'abonnement</h2>
          </div>
          <div className="p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="field-label">Code</label>
                <input value={planCode} onChange={(e) => setPlanCode(e.target.value)} placeholder="ex: premium" className="input-mobile" />
              </div>
              <div>
                <label className="field-label">Nom du plan</label>
                <input value={planName} onChange={(e) => setPlanName(e.target.value)} placeholder="Premium" className="input-mobile" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="field-label">Cycle</label>
                <select value={billingCycle} onChange={(e) => setBillingCycle(e.target.value)} className="input-mobile">
                  <option value="monthly">Mensuel</option>
                  <option value="yearly">Annuel</option>
                </select>
              </div>
              <div>
                <label className="field-label">Montant (XOF)</label>
                <input value={amountXof} onChange={(e) => setAmountXof(e.target.value)} placeholder="25000" className="input-mobile" type="number" />
              </div>
            </div>
            <div>
              <label className="field-label">Taux commission (ex: 0.02)</label>
              <input value={commissionRate} onChange={(e) => setCommissionRate(e.target.value)} placeholder="0.02" className="input-mobile" />
            </div>
            <button
              onClick={() => createPlanMutation.mutate()}
              disabled={!planCode || !planName || createPlanMutation.isPending}
              className="btn-primary"
            >
              <PlusCircle size={18} />
              {createPlanMutation.isPending ? "Création…" : "Créer le plan"}
            </button>
          </div>
        </div>

        {/* Audit logs */}
        <div
          className="rounded-2xl overflow-hidden"
          style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
        >
          <div
            className="px-4 py-3 flex items-center gap-2"
            style={{ borderBottom: "1px solid var(--bd)", background: "var(--n-50)" }}
          >
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "rgba(110,122,138,0.08)" }}>
              <Clock size={15} style={{ color: "var(--tx-muted)" }} />
            </div>
            <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Audit logs récents</h2>
          </div>
          <div className="p-4">
            {!logs.length ? (
              <div className="text-center py-8">
                <Sparkles size={32} style={{ color: "var(--bd)" }} className="mx-auto mb-3" />
                <p className="text-sm font-medium" style={{ color: "var(--tx-muted)" }}>Aucun log d'audit disponible</p>
              </div>
            ) : (
              <div className="space-y-2">
                {logs.slice(0, 10).map((log: any) => (
                  <div
                    key={log.id}
                    className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl"
                    style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold truncate" style={{ color: "var(--tx-head)" }}>{log.action}</p>
                      <p className="text-xs truncate" style={{ color: "var(--tx-muted)" }}>
                        {log.resource_type || "resource"} {log.resource_id || ""}
                      </p>
                    </div>
                    <span className="text-xs shrink-0" style={{ color: "var(--tx-muted)" }}>
                      {new Date(log.created_at).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Rappel équipe technique */}
        <div
          className="rounded-2xl p-4 flex items-start gap-3"
          style={{ background: "var(--p-50)", border: "1px solid var(--p-100)" }}
        >
          <Mail size={18} style={{ color: "var(--p-500)" }} className="mt-0.5 shrink-0" />
          <p className="text-sm leading-6" style={{ color: "var(--p-700)" }}>
            Les variables d'environnement serveur sont gérées par l'équipe technique. Contacter <strong>tech@fiissa.com</strong> pour toute modification.
          </p>
        </div>
      </div>
    </div>
  );
}
