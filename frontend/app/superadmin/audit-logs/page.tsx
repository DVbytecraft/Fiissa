"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { superadminApi, companiesApi } from "@/lib/api";
import { Activity, AlertCircle, Building2, Search, Shield, User } from "lucide-react";

/* ── Couleur par type d'action ── */
const ACTION_COLORS: Record<string, { color: string; bg: string }> = {
  "company.suspended":  { color: "#DC2626", bg: "rgba(220,38,38,0.08)" },
  "company.activated":  { color: "var(--s-600)", bg: "rgba(0,214,143,0.08)" },
  "staff.created":      { color: "var(--p-500)", bg: "rgba(34,87,255,0.08)" },
  "catalog.imported":   { color: "#7C3AED", bg: "rgba(124,58,237,0.08)" },
  "order.cancelled":    { color: "#F97316", bg: "rgba(249,115,22,0.08)" },
  "payment.confirmed":  { color: "var(--s-600)", bg: "rgba(0,214,143,0.08)" },
  "auth.login":         { color: "var(--tx-muted)", bg: "var(--n-100)" },
  "auth.logout":        { color: "var(--tx-muted)", bg: "var(--n-100)" },
};

function actionStyle(action: string) {
  const key = Object.keys(ACTION_COLORS).find((k) => action.startsWith(k.split(".")[0]));
  return ACTION_COLORS[key ?? ""] ?? { color: "var(--tx-muted)", bg: "var(--n-100)" };
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "à l'instant";
  if (m < 60) return `il y a ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `il y a ${h}h`;
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

const RESOURCE_ICONS: Record<string, React.ReactNode> = {
  company: <Building2 size={14} />,
  user:    <User size={14} />,
  default: <Activity size={14} />,
};

export default function AuditLogsPage() {
  const [actionFilter, setActionFilter] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [search, setSearch] = useState("");

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ["audit-logs", actionFilter, companyFilter],
    queryFn: () =>
      superadminApi.getAuditLogs({
        action:     actionFilter || undefined,
        company_id: companyFilter || undefined,
        limit: 200,
      }).then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: companiesData } = useQuery({
    queryKey: ["superadmin-companies-simple"],
    queryFn: () => superadminApi.getCompanies().then((r) => r.data),
  });

  const companies: any[] = companiesData?.items ?? companiesData ?? [];

  const filtered: any[] = (logs ?? []).filter((l: any) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      l.action?.toLowerCase().includes(q) ||
      l.resource_type?.toLowerCase().includes(q) ||
      l.user_id?.toLowerCase().includes(q)
    );
  });

  const ACTION_GROUPS = [
    { value: "",            label: "Toutes" },
    { value: "company",     label: "Entreprises" },
    { value: "staff",       label: "Staff" },
    { value: "auth",        label: "Auth" },
    { value: "catalog",     label: "Catalogue" },
    { value: "order",       label: "Commandes" },
    { value: "payment",     label: "Paiements" },
  ];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      {/* ─── Header ─── */}
      <div className="px-5 pt-5 pb-4" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-2xl flex items-center justify-center" style={{ background: "rgba(124,58,237,0.08)" }}>
            <Shield size={20} style={{ color: "#7C3AED" }} />
          </div>
          <div>
            <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>Audit Logs</h1>
            <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
              {filtered.length} événement{filtered.length > 1 ? "s" : ""}
            </p>
          </div>
        </div>

        {/* Recherche */}
        <div className="flex items-center gap-3 px-4 py-3 rounded-2xl mb-3" style={{ background: "var(--n-50)", border: "1.5px solid var(--bd)" }}>
          <Search size={16} style={{ color: "var(--n-400)" }} className="flex-shrink-0" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher action, ressource…"
            className="flex-1 bg-transparent text-sm outline-none"
            style={{ color: "#111111" }}
          />
        </div>

        {/* Filtres action */}
        <div className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1 scrollbar-hide">
          {ACTION_GROUPS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setActionFilter(value)}
              className="shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition-colors"
              style={
                actionFilter === value
                  ? { background: "#111111", color: "#fff" }
                  : { background: "var(--n-100)", color: "var(--tx-muted)" }
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ─── Liste logs ─── */}
      <div className="px-4 py-4">
        {isLoading && (
          <div className="space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)" }}>
                <div className="skeleton h-14 w-full" />
              </div>
            ))}
          </div>
        )}

        {!isLoading && filtered.length === 0 && (
          <div className="pt-20 text-center">
            <Activity size={40} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
            <p className="font-bold" style={{ color: "#111111" }}>Aucun log trouvé</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>Modifiez les filtres ou attendez de l'activité.</p>
          </div>
        )}

        {!isLoading && filtered.length > 0 && (
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            {filtered.map((log: any, i: number) => {
              const style = actionStyle(log.action);
              const icon  = RESOURCE_ICONS[log.resource_type] ?? RESOURCE_ICONS.default;
              return (
                <div
                  key={log.id}
                  className="flex items-start gap-3 px-4 py-3"
                  style={{ borderBottom: i < filtered.length - 1 ? "1px solid var(--bd)" : "none" }}
                >
                  {/* Icon */}
                  <div
                    className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ background: style.bg, color: style.color }}
                  >
                    {icon}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className="text-xs font-black px-2 py-0.5 rounded-full font-mono"
                        style={{ background: style.bg, color: style.color }}
                      >
                        {log.action}
                      </span>
                      {log.resource_type && (
                        <span className="text-xs" style={{ color: "var(--tx-muted)" }}>
                          · {log.resource_type}
                        </span>
                      )}
                    </div>
                    <p className="text-xs mt-0.5 font-mono truncate" style={{ color: "var(--tx-muted)" }}>
                      {log.resource_id ? `id: ${log.resource_id.slice(0, 12)}…` : ""}
                      {log.user_id ? ` · user: ${log.user_id.slice(0, 8)}…` : ""}
                    </p>
                  </div>

                  {/* Time */}
                  <p className="text-[10px] flex-shrink-0 mt-1" style={{ color: "var(--tx-muted)" }}>
                    {log.created_at ? timeAgo(log.created_at) : ""}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
