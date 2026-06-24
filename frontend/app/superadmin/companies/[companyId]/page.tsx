"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Building2,
  CheckCircle,
  Mail,
  Phone,
  ShieldAlert,
  Sparkles,
  Store,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { companiesApi, storesApi } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmModal } from "@/components/ui/confirm-modal";

const COMPANY_TYPE_LABELS: Record<string, string> = {
  supermarket: "Supermarche",
  restaurant: "Restaurant",
  proximity: "Proximite",
  pharmacy: "Pharmacie",
  boutique: "Boutique",
  other: "Autre",
};

const SUB_STATUS: Record<string, { label: string; bg: string; color: string }> = {
  active: { label: "Abonnement actif", bg: "rgba(0,214,143,0.1)", color: "var(--s-600)" },
  trial: { label: "Periode d'essai", bg: "rgba(34,87,255,0.08)", color: "var(--p-600)" },
  suspended: { label: "Abonnement suspendu", bg: "rgba(220,38,38,0.08)", color: "#DC2626" },
  cancelled: { label: "Abonnement annule", bg: "rgba(110,122,138,0.08)", color: "var(--tx-muted)" },
};

export default function SuperAdminCompanyDetailPage() {
  const params = useParams<{ companyId: string }>();
  const queryClient = useQueryClient();
  const companyId = params.companyId;
  const [confirmOpen, setConfirmOpen] = useState(false);

  const { data: company, isLoading } = useQuery({
    queryKey: ["superadmin-company", companyId],
    queryFn: () => companiesApi.getById(companyId).then((r) => r.data),
    enabled: Boolean(companyId),
  });

  const suspendMutation = useMutation({
    mutationFn: (suspend: boolean) => storesApi.suspendCompany(companyId, suspend),
    onSuccess: (_, suspend) => {
      toast.success(suspend ? "Entreprise suspendue" : "Entreprise reactivee");
      queryClient.invalidateQueries({ queryKey: ["superadmin-company", companyId] });
      queryClient.invalidateQueries({ queryKey: ["admin-companies"] });
      queryClient.invalidateQueries({ queryKey: ["platform-stats"] });
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur"),
  });

  const isSuspended = company?.is_suspended ?? !company?.is_active;

  if (isLoading) {
    return (
      <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
        <div className="px-4 pt-16 space-y-4">
          <div className="skeleton h-44 w-full rounded-[32px]" />
          <div className="skeleton h-28 w-full rounded-3xl" />
        </div>
      </div>
    );
  }

  if (!company) {
    return (
      <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
        <div className="px-5 pt-5 pb-4 flex items-center gap-3">
          <Link href="/superadmin/companies" style={{ color: "var(--tx-muted)" }}>
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>
            Entreprise
          </h1>
        </div>
        <div className="flex flex-col items-center justify-center px-6 py-24 text-center">
          <Building2 size={64} className="mb-4" style={{ color: "var(--bd)" }} />
          <p className="text-base font-black" style={{ color: "var(--tx-head)" }}>
            Entreprise introuvable
          </p>
          <p className="mt-2 text-sm" style={{ color: "var(--tx-muted)" }}>
            L'identifiant fourni ne correspond a aucune entreprise connue.
          </p>
          <Link
            href="/superadmin/companies"
            className="mt-5 rounded-2xl px-6 py-3 text-sm font-black text-white"
            style={{ background: "var(--p-500)" }}
          >
            Retour a la liste
          </Link>
        </div>
      </div>
    );
  }

  const sub = SUB_STATUS[company.subscription_status] ?? {
    label: company.subscription_status || "Aucun abonnement",
    bg: "rgba(110,122,138,0.08)",
    color: "var(--tx-muted)",
  };

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div className="px-4 pt-4 pb-6">
        <div
          className="overflow-hidden rounded-[32px] p-5 text-white relative"
          style={{ background: "linear-gradient(145deg, #0D1227 0%, #1333B3 55%, #00AB72 100%)", boxShadow: "0 18px 42px rgba(13,18,39,0.18)" }}
        >
          <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-white/10" />
          <div className="absolute right-10 bottom-0 h-20 w-20 rounded-full bg-white/10" />
          <div className="relative">
            <div className="flex items-center gap-3">
              <Link href="/superadmin/companies" className="rounded-full bg-white/14 p-2 text-white">
                <ArrowLeft size={18} />
              </Link>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-1 text-[11px] font-black uppercase tracking-[0.16em]">
                <Sparkles size={14} />
                Fiche entreprise
              </div>
            </div>

            <div className="mt-6 flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h1 className="truncate text-3xl font-black">{company.name}</h1>
                <p className="mt-2 text-sm text-white/78">
                  {COMPANY_TYPE_LABELS[company.type] ?? company.type} · {company.country}
                </p>
              </div>
              {isSuspended && (
                <span className="shrink-0 rounded-full bg-red-500/20 px-3 py-1 text-xs font-black uppercase tracking-[0.12em] text-red-100">
                  Suspendue
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          {[
            { icon: Store, label: "Boutiques", value: company.stores_count ?? "—", color: "var(--p-500)" },
            { icon: TrendingUp, label: "Cmd / 30 jours", value: company.orders_count_30d ?? "—", color: "var(--s-500)" },
          ].map(({ icon: Icon, label, value, color }) => (
            <div key={label} className="rounded-[24px] p-4 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
              <Icon size={20} className="mx-auto mb-2" style={{ color }} />
              <p className="text-2xl font-black" style={{ color: "var(--tx-head)" }}>{value}</p>
              <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--tx-muted)" }}>{label}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="px-4 pb-6 space-y-4">
        <div className="rounded-[28px] p-4 flex items-center gap-3" style={{ background: sub.bg, border: `1px solid ${sub.color}25` }}>
          <CheckCircle size={20} style={{ color: sub.color }} />
          <div>
            <p className="text-sm font-black" style={{ color: sub.color }}>{sub.label}</p>
            {company.subscription_expires_at && (
              <p className="mt-1 text-xs" style={{ color: sub.color, opacity: 0.78 }}>
                Expire le {new Date(company.subscription_expires_at).toLocaleDateString("fr-FR", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </p>
            )}
          </div>
        </div>

        <div className="rounded-[28px] p-5 space-y-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}>
          <p className="text-xs font-black uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
            Coordonnees
          </p>
          {[
            { icon: Mail, value: company.contact_email, label: "Email" },
            { icon: Phone, value: company.contact_phone, label: "Telephone" },
          ].map(({ icon: Icon, value, label }) => (
            <div key={label} className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl" style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}>
                <Icon size={16} />
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-[0.12em]" style={{ color: "var(--tx-muted)" }}>
                  {label}
                </p>
                <p className="mt-0.5 text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
                  {value || "Non renseigne"}
                </p>
              </div>
            </div>
          ))}
        </div>

        {company.revenue_xof_30d != null && (
          <div className="rounded-[28px] p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}>
            <p className="text-xs font-black uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
              Chiffre d'affaires
            </p>
            <p className="mt-3 text-3xl font-black" style={{ color: "var(--p-500)" }}>
              {company.revenue_xof_30d.toLocaleString("fr-FR")} F
            </p>
            <p className="mt-1 text-sm" style={{ color: "var(--tx-muted)" }}>
              total sur les 30 derniers jours
            </p>
          </div>
        )}

        <div className="rounded-[28px] p-5 flex items-center gap-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}>
          <ShieldAlert size={18} style={{ color: isSuspended ? "#DC2626" : "var(--s-500)" }} />
          <div className="flex-1">
            <p className="text-sm font-black" style={{ color: "var(--tx-head)" }}>
              Acces plateforme
            </p>
            <p className="mt-1 text-xs leading-5" style={{ color: "var(--tx-muted)" }}>
              {isSuspended
                ? "Acces revoque : l'entreprise ne peut plus se connecter."
                : "Acces actif : l'entreprise peut utiliser Fiissa normalement."}
            </p>
          </div>
        </div>

        <button
          onClick={() => setConfirmOpen(true)}
          disabled={suspendMutation.isPending}
          className="w-full rounded-[24px] py-4 font-black text-sm flex items-center justify-center gap-2"
          style={{
            background: isSuspended ? "rgba(0,214,143,0.1)" : "#FEF2F2",
            color: isSuspended ? "var(--s-600)" : "#DC2626",
            border: `1px solid ${isSuspended ? "rgba(0,214,143,0.26)" : "#FCA5A5"}`,
          }}
        >
          {isSuspended ? (
            <>
              <CheckCircle size={16} /> Reactiver l'entreprise
            </>
          ) : (
            <>
              <XCircle size={16} /> Suspendre l'entreprise
            </>
          )}
        </button>
      </div>

      <ConfirmModal
        open={confirmOpen}
        title={isSuspended ? "Reactiver l'entreprise" : "Suspendre l'entreprise"}
        message={
          isSuspended
            ? `Reactiver ${company.name} ? L'acces a Fiissa sera retabli immediatement.`
            : `Suspendre ${company.name} ? Tous les acces seront revoques immediatement.`
        }
        confirmLabel={isSuspended ? "Reactiver" : "Suspendre"}
        variant={isSuspended ? "info" : "danger"}
        onConfirm={() => {
          setConfirmOpen(false);
          suspendMutation.mutate(!isSuspended);
        }}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
