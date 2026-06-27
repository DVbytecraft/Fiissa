"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Building2,
  CheckCircle,
  ChevronRight,
  Clock,
  Plus,
  Search,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import { companiesApi, storesApi, superadminApi } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmModal } from "@/components/ui/confirm-modal";
import { useDebounce } from "@/lib/hooks";

const COMPANY_TYPE_LABELS: Record<string, string> = {
  supermarket: "Supermarche",
  restaurant: "Restaurant",
  proximity: "Proximite",
  pharmacy: "Pharmacie",
  boutique: "Boutique",
  other: "Autre",
};

const SUB_STATUS: Record<string, { label: string; bg: string; color: string }> = {
  active: { label: "Active", bg: "rgba(0,214,143,0.1)", color: "var(--s-500)" },
  trial: { label: "Essai", bg: "rgba(34,87,255,0.08)", color: "var(--p-500)" },
  suspended: { label: "Suspendue", bg: "rgba(220,38,38,0.08)", color: "#DC2626" },
  cancelled: { label: "Annulee", bg: "rgba(110,122,138,0.08)", color: "var(--tx-muted)" },
};

const COMPANY_TYPES = ["supermarket", "restaurant", "proximity", "pharmacy", "boutique", "other"];

type ConfirmAction = {
  companyId: string;
  companyName: string;
  suspend: boolean;
};

type PageTab = "companies" | "requests";

function CreateCompanyModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [type, setType] = useState("boutique");
  const [country, setCountry] = useState("SN");
  const [currency, setCurrency] = useState("XOF");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");

  const createMutation = useMutation({
    mutationFn: () =>
      companiesApi.create({
        name,
        type,
        country,
        currency,
        contact_email: contactEmail || null,
        contact_phone: contactPhone || null,
      }),
    onSuccess: () => {
      toast.success("Entreprise creee");
      queryClient.invalidateQueries({ queryKey: ["admin-companies"] });
      queryClient.invalidateQueries({ queryKey: ["platform-stats"] });
      onClose();
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur creation"),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm flex items-end md:items-center md:justify-center">
      <div
        className="w-full md:max-w-xl rounded-t-[32px] md:rounded-[32px] p-6 space-y-4"
        style={{ background: "var(--bg-card)", boxShadow: "0 24px 64px rgba(13,18,39,0.22)" }}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>
              Creer une entreprise
            </h2>
            <p className="mt-1 text-sm" style={{ color: "var(--tx-muted)" }}>
              Ouvre un nouvel espace marchand avec son abonnement d'essai initial.
            </p>
          </div>
          <button onClick={onClose} className="rounded-full px-3 py-1 text-sm font-bold" style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}>
            Fermer
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nom de l'entreprise" className="input-mobile md:col-span-2" />
          <select value={type} onChange={(e) => setType(e.target.value)} className="input-mobile">
            {COMPANY_TYPES.map((value) => (
              <option key={value} value={value}>
                {COMPANY_TYPE_LABELS[value] || value}
              </option>
            ))}
          </select>
          <input value={country} onChange={(e) => setCountry(e.target.value.toUpperCase())} placeholder="Pays" className="input-mobile" maxLength={2} />
          <input value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} placeholder="Devise" className="input-mobile" maxLength={3} />
          <input value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} placeholder="Email contact" className="input-mobile" type="email" />
          <input value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} placeholder="Telephone contact" className="input-mobile md:col-span-2" />
        </div>

        <button
          onClick={() => createMutation.mutate()}
          disabled={!name.trim() || createMutation.isPending}
          className="btn-primary"
        >
          <Plus size={18} />
          {createMutation.isPending ? "Creation..." : "Creer l'entreprise"}
        </button>
      </div>
    </div>
  );
}

export default function SuperAdminCompaniesPage() {
  const [activeTab, setActiveTab] = useState<PageTab>("companies");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const queryClient = useQueryClient();

  const debouncedSearch = useDebounce(search, 350);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-companies", debouncedSearch, statusFilter],
    queryFn: () =>
      superadminApi
        .getCompanies({ search: debouncedSearch, status: statusFilter || undefined })
        .then((r) => r.data),
  });

  const { data: platformStats } = useQuery({
    queryKey: ["platform-stats"],
    queryFn: () => superadminApi.getStats().then((r) => r.data),
  });

  const { data: requestsData, isLoading: requestsLoading } = useQuery({
    queryKey: ["registration-requests"],
    queryFn: () => superadminApi.getRegistrationRequests({ status: "pending" }).then((r) => r.data),
    enabled: activeTab === "requests",
  });
  const registrationRequests = requestsData?.items ?? [];

  const approveMutation = useMutation({
    mutationFn: (requestId: string) => superadminApi.approveRegistrationRequest(requestId),
    onSuccess: () => {
      toast.success("Demande approuvée — compte créé");
      queryClient.invalidateQueries({ queryKey: ["registration-requests"] });
      queryClient.invalidateQueries({ queryKey: ["admin-companies"] });
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur approbation"),
  });

  const rejectMutation = useMutation({
    mutationFn: (requestId: string) => superadminApi.rejectRegistrationRequest(requestId),
    onSuccess: () => {
      toast.success("Demande rejetée");
      queryClient.invalidateQueries({ queryKey: ["registration-requests"] });
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur rejet"),
  });

  const suspendMutation = useMutation({
    mutationFn: ({ companyId, suspend }: { companyId: string; suspend: boolean }) =>
      storesApi.suspendCompany(companyId, suspend),
    onSuccess: (_, { suspend }) => {
      toast.success(suspend ? "Entreprise suspendue" : "Entreprise reactivee");
      queryClient.invalidateQueries({ queryKey: ["admin-companies"] });
      queryClient.invalidateQueries({ queryKey: ["platform-stats"] });
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur"),
  });

  const handleConfirm = () => {
    if (!confirmAction) return;
    suspendMutation.mutate({ companyId: confirmAction.companyId, suspend: confirmAction.suspend });
    setConfirmAction(null);
  };

  const companies = data?.items ?? [];

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      <div
        className="px-6 pt-8 pb-5"
        style={{ background: "linear-gradient(180deg, #0D1227 0%, #1333B3 100%)" }}
      >
        <div
          className="rounded-[32px] p-5 text-white relative overflow-hidden"
          style={{ background: "linear-gradient(145deg, rgba(255,255,255,0.14), rgba(255,255,255,0.06))", border: "1px solid rgba(255,255,255,0.14)" }}
        >
          <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-white/10" />
          <div className="absolute right-10 bottom-0 h-16 w-16 rounded-full bg-white/10" />
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]">
                <Sparkles size={14} />
                Pilotage plateforme
              </div>
              <h1 className="mt-4 text-3xl font-semibold leading-tight">Entreprises Fiissa</h1>
              <p className="mt-2 text-sm text-white/75">
                Recherche, creation et supervision des comptes marchands.
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="shrink-0 rounded-2xl px-4 py-3 text-sm font-semibold"
              style={{ background: "rgba(255,255,255,0.95)", color: "#0D1227" }}
            >
              <span className="inline-flex items-center gap-2">
                <Plus size={16} />
                Nouvelle
              </span>
            </button>
          </div>
        </div>

        {platformStats && (
          <div className="mt-4 grid grid-cols-3 gap-3">
            {[
              { label: "Entreprises", value: platformStats.total_companies, color: "var(--tx-head)", bg: "rgba(255,255,255,0.95)" },
              { label: "Actives", value: platformStats.active_companies, color: "var(--s-700)", bg: "rgba(0,214,143,0.12)" },
              {
                label: "CA total",
                value: `${((platformStats.total_revenue_xof ?? 0) / 1_000_000).toFixed(1)}M F`,
                color: "var(--p-600)",
                bg: "rgba(34,87,255,0.12)",
              },
            ].map(({ label, value, color, bg }) => (
              <div key={label} className="rounded-2xl p-3 text-center" style={{ background: bg }}>
                <p className="text-xl font-semibold" style={{ color }}>{value}</p>
                <p className="mt-0.5 text-xs" style={{ color: "rgba(100,116,139,0.9)" }}>{label}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Onglets */}
      <div className="flex px-4 pt-4 gap-2">
        {[
          { key: "companies" as PageTab, label: "Entreprises" },
          { key: "requests" as PageTab, label: "Demandes", badge: registrationRequests.length },
        ].map(({ key, label, badge }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-bold transition-colors"
            style={
              activeTab === key
                ? { background: "var(--p-500)", color: "#fff" }
                : { background: "var(--bg-card)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }
            }
          >
            {label}
            {badge != null && badge > 0 && (
              <span
                className="inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-semibold"
                style={{ background: "rgba(245,158,11,0.2)", color: "#D97706" }}
              >
                {badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Contenu : onglet Demandes d'inscription */}
      {activeTab === "requests" && (
        <div className="px-4 py-4 space-y-3">
          {requestsLoading && [...Array(2)].map((_, i) => (
            <div key={i} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
              <div className="skeleton h-20 w-full" />
            </div>
          ))}

          {!requestsLoading && registrationRequests.length === 0 && (
            <div className="text-center py-16">
              <Clock size={56} style={{ color: "var(--bd)" }} className="mx-auto mb-4" />
              <p style={{ color: "var(--tx-head)" }} className="font-bold">Aucune demande en attente</p>
              <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
                Les nouvelles inscriptions marchandes apparaîtront ici.
              </p>
            </div>
          )}

          {registrationRequests.map((req: any) => (
            <div
              key={req.id}
              className="rounded-[28px] overflow-hidden"
              style={{ background: "var(--bg-card)", border: "1px solid rgba(245,158,11,0.25)", boxShadow: "var(--sh-sm)" }}
            >
              <div className="px-4 py-4 flex items-start gap-3">
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
                  style={{ background: "rgba(245,158,11,0.1)" }}
                >
                  <Building2 size={22} style={{ color: "#D97706" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>{req.company_name}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {req.email} {req.phone ? `· ${req.phone}` : ""}
                  </p>
                  {req.company_type && (
                    <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
                      {COMPANY_TYPE_LABELS[req.company_type] ?? req.company_type}
                    </p>
                  )}
                  <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
                    Soumis le {new Date(req.created_at).toLocaleDateString("fr-FR")}
                  </p>
                </div>
              </div>
              <div
                className="px-4 py-3 flex gap-3"
                style={{ background: "var(--bg-app)", borderTop: "1px solid var(--bd)" }}
              >
                <button
                  onClick={() => approveMutation.mutate(req.id)}
                  disabled={approveMutation.isPending}
                  className="flex items-center gap-1.5 text-xs font-bold"
                  style={{ color: "var(--s-600)" }}
                >
                  <ThumbsUp size={14} /> Approuver
                </button>
                <button
                  onClick={() => rejectMutation.mutate(req.id)}
                  disabled={rejectMutation.isPending}
                  className="flex items-center gap-1.5 text-xs font-bold ml-4"
                  style={{ color: "#DC2626" }}
                >
                  <ThumbsDown size={14} /> Rejeter
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Contenu : onglet Entreprises */}
      {activeTab === "companies" && (
      <div className="px-4 py-4 space-y-4">
        <div
          className="rounded-[28px] p-4"
          style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
        >
          <div className="relative mb-3">
            <Search size={16} style={{ color: "var(--tx-muted)" }} className="absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Rechercher une entreprise..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ background: "var(--bg-app)", color: "var(--tx-head)" }}
              className="w-full pl-9 pr-4 py-3 rounded-2xl text-sm outline-none"
            />
          </div>

          <div className="flex gap-2 overflow-x-auto scrollbar-hide">
            {[
              { value: "", label: "Toutes" },
              { value: "active", label: "Actives" },
              { value: "trial", label: "Essai" },
              { value: "suspended", label: "Suspendues" },
            ].map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setStatusFilter(value)}
                style={
                  statusFilter === value
                    ? { background: "var(--tx-head)", color: "#fff" }
                    : { background: "var(--bg-app)", color: "var(--tx-muted)" }
                }
                className="shrink-0 px-4 py-2 rounded-full text-sm font-bold"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {isLoading &&
          [...Array(3)].map((_, index) => (
            <div key={index} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
              <div className="skeleton h-20 w-full" />
            </div>
          ))}

        {companies.map((company: any) => {
          const sub = SUB_STATUS[company.subscription_status] ?? {
            label: company.subscription_status || "Sans abonnement",
            bg: "rgba(110,122,138,0.08)",
            color: "var(--tx-muted)",
          };

          return (
            <div
              key={company.id}
              style={{
                background: "var(--bg-card)",
                border: `1px solid ${company.is_suspended ? "rgba(220,38,38,0.25)" : "var(--bd)"}`,
                boxShadow: "var(--sh-sm)",
              }}
              className="rounded-[28px] overflow-hidden"
            >
              <Link href={`/superadmin/companies/${company.id}`}>
                <div className="px-4 py-4 flex items-start gap-3 active:opacity-80">
                  <div
                    style={{ background: "rgba(34,87,255,0.08)" }}
                    className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
                  >
                    <Building2 size={22} style={{ color: "var(--p-500)" }} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p style={{ color: "var(--tx-head)" }} className="font-semibold text-sm truncate">
                        {company.name}
                      </p>
                      <span
                        style={{ background: sub.bg, color: sub.color }}
                        className="text-xs font-bold px-2 py-1 rounded-full shrink-0"
                      >
                        {sub.label}
                      </span>
                    </div>
                    <p style={{ color: "var(--tx-muted)" }} className="text-xs mt-0.5">
                      {COMPANY_TYPE_LABELS[company.type] ?? company.type} · {company.stores_count} boutique{company.stores_count > 1 ? "s" : ""}
                    </p>
                    <div className="flex items-center gap-3 mt-2">
                      <span style={{ color: "var(--tx-muted)" }} className="text-xs">
                        {company.orders_count_30d ?? 0} cmd/30j
                      </span>
                      <span style={{ color: "var(--p-500)" }} className="text-xs font-bold">
                        {(company.revenue_xof_30d ?? 0).toLocaleString("fr-FR")} F
                      </span>
                    </div>
                  </div>

                  <ChevronRight size={16} style={{ color: "var(--bd)" }} className="mt-1 shrink-0" />
                </div>
              </Link>

              <div
                style={{ background: "var(--bg-app)", borderTop: "1px solid var(--bd)" }}
                className="px-4 py-3 flex gap-3 items-center"
              >
                <button
                  onClick={() =>
                    setConfirmAction({
                      companyId: company.id,
                      companyName: company.name,
                      suspend: !company.is_suspended,
                    })
                  }
                  disabled={suspendMutation.isPending}
                  style={{ color: company.is_suspended ? "var(--s-500)" : "#DC2626" }}
                  className="flex items-center gap-1.5 text-xs font-bold"
                >
                  {company.is_suspended ? (
                    <>
                      <CheckCircle size={14} /> Reactiver
                    </>
                  ) : (
                    <>
                      <XCircle size={14} /> Suspendre
                    </>
                  )}
                </button>

                {company.subscription_status === "cancelled" && (
                  <span className="flex items-center gap-1.5 text-xs font-bold ml-auto" style={{ color: "#D97706" }}>
                    <AlertTriangle size={14} />
                    Abonnement a revoir
                  </span>
                )}
              </div>
            </div>
          );
        })}

        {!isLoading && companies.length === 0 && (
          <div className="text-center py-16">
            <Building2 size={64} style={{ color: "var(--bd)" }} className="mx-auto mb-4" />
            <p style={{ color: "var(--tx-muted)" }}>Aucune entreprise trouvee</p>
          </div>
        )}
      </div>
      )}

      <ConfirmModal
        open={!!confirmAction}
        title={confirmAction?.suspend ? "Suspendre l'entreprise" : "Reactiver l'entreprise"}
        message={
          confirmAction?.suspend
            ? `Suspendre ${confirmAction?.companyName} ? L'entreprise ne pourra plus acceder a Fiissa.`
            : `Reactiver ${confirmAction?.companyName} ? L'acces sera retabli immediatement.`
        }
        confirmLabel={confirmAction?.suspend ? "Suspendre" : "Reactiver"}
        variant={confirmAction?.suspend ? "danger" : "info"}
        onConfirm={handleConfirm}
        onCancel={() => setConfirmAction(null)}
      />

      {showCreateModal && <CreateCompanyModal onClose={() => setShowCreateModal(false)} />}
    </div>
  );
}
