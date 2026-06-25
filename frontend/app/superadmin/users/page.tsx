"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { superadminApi, api } from "@/lib/api";
import {
  Search, UserCheck, UserPlus, UserX, Users,
  Shield, Building2, X,
} from "lucide-react";
import { toast } from "sonner";
import { ConfirmModal } from "@/components/ui/confirm-modal";

const ROLE_CONFIG: Record<string, { label: string; bg: string; color: string; dot: string }> = {
  super_admin:     { label: "Super Admin",      bg: "rgba(234,179,8,0.12)",   color: "#B45309",  dot: "#EAB308" },
  company_owner:   { label: "Propriétaire",     bg: "rgba(124,58,237,0.10)",  color: "#7C3AED",  dot: "#8B5CF6" },
  store_manager:   { label: "Gérant",           bg: "rgba(34,87,255,0.08)",   color: "var(--p-600)", dot: "var(--p-500)" },
  accountant:      { label: "Comptable",        bg: "rgba(0,214,143,0.10)",   color: "var(--s-700)", dot: "var(--s-500)" },
  preparer:        { label: "Préparateur",      bg: "rgba(245,158,11,0.10)",  color: "#D97706",  dot: "#F59E0B" },
  security_agent:  { label: "Agent sécurité",   bg: "rgba(110,122,138,0.08)", color: "var(--tx-muted)", dot: "var(--n-400)" },
  support_agent:   { label: "Support",          bg: "rgba(236,72,153,0.08)",  color: "#BE185D",  dot: "#EC4899" },
  customer:        { label: "Client",           bg: "rgba(14,165,233,0.08)",  color: "#0284C7",  dot: "#38BDF8" },
};

const AVATAR_COLORS = [
  "var(--p-500)", "var(--s-600)", "#7C3AED", "#EC4899", "#F59E0B", "#0284C7",
];

function avatarColor(name: string) {
  const idx = (name.charCodeAt(0) || 0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}

function CreateStaffModal({ onClose, companies }: { onClose: () => void; companies: any[] }) {
  const queryClient = useQueryClient();
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName]   = useState("");
  const [role, setRole]           = useState("support_agent");
  const [companyId, setCompanyId] = useState("");

  const createMutation = useMutation({
    mutationFn: () =>
      api.post("/superadmin/staff", {
        email, password,
        first_name: firstName, last_name: lastName,
        role,
        company_id: companyId || null,
      }),
    onSuccess: () => {
      toast.success("Utilisateur créé avec succès");
      queryClient.invalidateQueries({ queryKey: ["superadmin-users"] });
      onClose();
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur création"),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm flex items-end md:items-center md:justify-center">
      <div
        className="w-full md:max-w-lg rounded-t-[32px] md:rounded-[32px] p-6 space-y-4"
        style={{ background: "var(--bg-card)", boxShadow: "0 24px 64px rgba(13,18,39,0.22)" }}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>Créer un utilisateur</h2>
            <p className="mt-1 text-sm" style={{ color: "var(--tx-muted)" }}>
              Compte staff ou superadmin sur la plateforme Fiissa.
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full"
            style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
          >
            <X size={16} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="field-label">Prénom</label>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="Ibrahima" className="input-mobile" />
          </div>
          <div>
            <label className="field-label">Nom</label>
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Diallo" className="input-mobile" />
          </div>
        </div>

        <div>
          <label className="field-label">Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@domaine.com" className="input-mobile" type="email" />
        </div>

        <div>
          <label className="field-label">Mot de passe</label>
          <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Mot de passe sécurisé" className="input-mobile" type="password" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="field-label">Rôle</label>
            <select value={role} onChange={(e) => setRole(e.target.value)} className="input-mobile">
              {Object.entries(ROLE_CONFIG)
                .filter(([key]) => key !== "customer")
                .map(([key, { label }]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
            </select>
          </div>
          <div>
            <label className="field-label">Entreprise (optionnel)</label>
            <select value={companyId} onChange={(e) => setCompanyId(e.target.value)} className="input-mobile">
              <option value="">Aucune</option>
              {companies.map((c: any) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={() => createMutation.mutate()}
          disabled={!email || !password || !firstName || createMutation.isPending}
          className="btn-primary"
        >
          <UserPlus size={18} />
          {createMutation.isPending ? "Création…" : "Créer l'utilisateur"}
        </button>
      </div>
    </div>
  );
}

export default function SuperAdminUsersPage() {
  const [showCreate, setShowCreate]   = useState(false);
  const [search, setSearch]           = useState("");
  const [roleFilter, setRoleFilter]   = useState("");
  const [toggleTarget, setToggleTarget] = useState<{ userId: string; active: boolean; name: string } | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["superadmin-users"],
    queryFn: () => superadminApi.getUsers().then((r) => r.data),
  });

  const { data: companiesData } = useQuery({
    queryKey: ["superadmin-companies-lite"],
    queryFn: () => superadminApi.getCompanies().then((r) => r.data),
  });

  const toggleUserMutation = useMutation({
    mutationFn: ({ userId, active }: { userId: string; active: boolean }) =>
      active ? superadminApi.deactivateUser(userId) : superadminApi.reactivateUser(userId),
    onSuccess: (_, { active }) => {
      toast.success(active ? "Utilisateur désactivé" : "Utilisateur réactivé");
      queryClient.invalidateQueries({ queryKey: ["superadmin-users"] });
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur"),
  });

  const companies = companiesData?.items ?? [];

  const filteredItems = (data?.items ?? []).filter((user: any) => {
    const q = search.toLowerCase();
    const matchesSearch =
      !q ||
      user.first_name?.toLowerCase().includes(q) ||
      user.last_name?.toLowerCase().includes(q) ||
      user.email?.toLowerCase().includes(q);
    const matchesRole = !roleFilter || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      {/* Hero header */}
      <div className="px-5 pt-6 pb-5" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Shield size={16} style={{ color: "var(--p-500)" }} />
              <span className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
                Gestion des accès
              </span>
            </div>
            <h1 className="text-2xl font-semibold" style={{ color: "var(--tx-head)" }}>Utilisateurs</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
              {data?.total ?? "…"} compte{(data?.total ?? 0) > 1 ? "s" : ""} sur la plateforme
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl text-sm font-bold text-white transition-all active:scale-95"
            style={{ background: "var(--p-500)", boxShadow: "var(--sh-brand)" }}
          >
            <UserPlus size={16} />
            <span className="hidden sm:inline">Créer</span>
          </button>
        </div>

        {/* Barre de recherche + filtres */}
        <div className="mt-4 space-y-3">
          <div
            className="flex items-center gap-3 px-4 py-3 rounded-2xl"
            style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
          >
            <Search size={16} style={{ color: "var(--tx-muted)" }} />
            <input
              type="text"
              placeholder="Rechercher par nom ou email…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 bg-transparent text-sm outline-none"
              style={{ color: "var(--tx-head)" }}
            />
            {search && (
              <button onClick={() => setSearch("")} style={{ color: "var(--tx-muted)" }}>
                <X size={14} />
              </button>
            )}
          </div>

          <div className="flex gap-2 overflow-x-auto scrollbar-hide">
            {[
              { value: "", label: "Tous" },
              { value: "super_admin",   label: "Super Admin" },
              { value: "company_owner", label: "Propriétaires" },
              { value: "store_manager", label: "Gérants" },
              { value: "preparer",      label: "Préparateurs" },
              { value: "customer",      label: "Clients" },
            ].map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setRoleFilter(value)}
                className="shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition-all"
                style={
                  roleFilter === value
                    ? { background: "var(--tx-head)", color: "white" }
                    : { background: "var(--n-100)", color: "var(--tx-muted)" }
                }
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Liste */}
      <div className="px-4 py-4 space-y-2">
        {isLoading &&
          [...Array(5)].map((_, i) => (
            <div key={i} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}>
              <div className="flex items-center gap-3">
                <div className="skeleton w-11 h-11 rounded-full" />
                <div className="flex-1 space-y-2">
                  <div className="skeleton h-4 w-1/3" />
                  <div className="skeleton h-3 w-1/2" />
                </div>
              </div>
            </div>
          ))}

        {!isLoading && filteredItems.length === 0 && (
          <div className="text-center py-16">
            <Users size={56} style={{ color: "var(--bd)" }} className="mx-auto mb-4" />
            <p className="font-bold" style={{ color: "var(--tx-head)" }}>Aucun utilisateur trouvé</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
              {search || roleFilter ? "Essaie un autre filtre." : "Crée le premier utilisateur."}
            </p>
          </div>
        )}

        {filteredItems.map((user: any) => {
          const role   = ROLE_CONFIG[user.role] ?? { label: user.role, bg: "rgba(110,122,138,0.08)", color: "var(--tx-muted)", dot: "var(--n-400)" };
          const initials = `${user.first_name?.[0] || ""}${user.last_name?.[0] || ""}`.toUpperCase() || user.email?.[0]?.toUpperCase() || "?";
          const company  = companies.find((c: any) => c.id === user.company_id);

          return (
            <div
              key={user.id}
              className="rounded-2xl p-4 flex items-center gap-3"
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
            >
              {/* Avatar initiales */}
              <div
                className="w-11 h-11 rounded-full flex items-center justify-center font-semibold text-white text-sm shrink-0"
                style={{ background: avatarColor(user.first_name || user.email || "") }}
              >
                {initials}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
                    {user.first_name} {user.last_name}
                  </p>
                  <span
                    className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full"
                    style={{ background: role.bg, color: role.color }}
                  >
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: role.dot }} />
                    {role.label}
                  </span>
                </div>
                <p className="text-xs mt-0.5 truncate" style={{ color: "var(--tx-muted)" }}>
                  {user.email || user.phone}
                </p>
                {company && (
                  <div className="flex items-center gap-1 mt-1">
                    <Building2 size={11} style={{ color: "var(--tx-muted)" }} />
                    <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{company.name}</p>
                  </div>
                )}
              </div>

              <button
                onClick={() => setToggleTarget({ userId: user.id, active: !!user.is_active, name: `${user.first_name || ""} ${user.last_name || ""}`.trim() || user.email })}
                disabled={toggleUserMutation.isPending || user.role === "super_admin"}
                className="w-9 h-9 flex items-center justify-center rounded-xl transition-colors"
                style={
                  user.is_active
                    ? { background: "var(--s-50)", color: "var(--s-600)" }
                    : { background: "var(--error-bg)", color: "var(--error)" }
                }
                title={user.is_active ? "Désactiver" : "Réactiver"}
              >
                {user.is_active
                  ? <UserCheck size={16} />
                  : <UserX size={16} />}
              </button>
            </div>
          );
        })}
      </div>

      <ConfirmModal
        open={!!toggleTarget}
        title={toggleTarget?.active ? "Désactiver cet utilisateur" : "Réactiver cet utilisateur"}
        message={
          toggleTarget?.active
            ? `Désactiver ${toggleTarget?.name} ? L'utilisateur ne pourra plus se connecter.`
            : `Réactiver ${toggleTarget?.name} ? L'accès sera rétabli immédiatement.`
        }
        confirmLabel={toggleTarget?.active ? "Désactiver" : "Réactiver"}
        variant={toggleTarget?.active ? "danger" : "info"}
        onConfirm={() => {
          if (toggleTarget) {
            toggleUserMutation.mutate({ userId: toggleTarget.userId, active: toggleTarget.active });
            setToggleTarget(null);
          }
        }}
        onCancel={() => setToggleTarget(null)}
      />

      {showCreate && <CreateStaffModal onClose={() => setShowCreate(false)} companies={companies} />}
    </div>
  );
}
