"use client";

import { useQuery } from "@tanstack/react-query";
import { superadminApi } from "@/lib/api";
import { Building2, CreditCard, ShieldCheck, Sparkles, TrendingUp, Users } from "lucide-react";

function StatBox({ label, value, icon: Icon, color }: any) {
  return (
    <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
      <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3" style={{ background: color + "18" }}>
        <Icon size={20} style={{ color }} />
      </div>
      <p className="text-2xl font-semibold" style={{ color: "var(--tx-head)" }}>{value ?? "—"}</p>
      <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>{label}</p>
    </div>
  );
}

export default function SuperAdminStatsPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["platform-stats"],
    queryFn: () => superadminApi.getStats().then((r) => r.data),
  });

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div className="px-4 pt-5 pb-4 space-y-4">
        <section className="hero-panel p-5">
          <div className="relative">
            <div className="eyebrow">
              <Sparkles size={14} />
              Global control
            </div>
            <div className="mt-4 flex items-start justify-between gap-4">
              <div>
                <h1 className="text-3xl font-semibold leading-tight">Statistiques plateforme</h1>
                <p className="mt-2 max-w-xl text-sm leading-6 text-white/75">
                  Vue consolidée Fiissa sur l&apos;activité marchande, les utilisateurs et la performance commerciale.
                </p>
              </div>
              <div className="rounded-2xl bg-white/10 px-4 py-3 text-right backdrop-blur-sm">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-white/60">Etat</p>
                <p className="mt-1 inline-flex items-center gap-2 text-sm font-semibold">
                  <ShieldCheck size={16} />
                  Plateforme active
                </p>
              </div>
            </div>
          </div>
        </section>

        <div className="surface-card p-4">
          <p className="text-sm font-bold uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
            Vue globale Fiissa
          </p>
          <p className="mt-1 text-sm leading-6" style={{ color: "var(--tx-muted)" }}>
            Les indicateurs ci-dessous sont rafraichis depuis les APIs de supervision superadmin.
          </p>
        </div>
      </div>

      <div className="px-4 pb-5">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}>
                <div className="skeleton h-10 w-10 rounded-xl mb-3" />
                <div className="skeleton h-8 w-1/2 mb-1" />
                <div className="skeleton h-4 w-3/4" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <StatBox label="Entreprises actives" value={stats?.active_companies} icon={Building2} color="var(--p-500)" />
            <StatBox label="Utilisateurs totaux" value={stats?.total_users} icon={Users} color="var(--s-500)" />
            <StatBox label="Commandes ce mois" value={stats?.orders_this_month} icon={TrendingUp} color="#F59E0B" />
            <StatBox label="Revenus (FCFA)" value={stats?.revenue_xof?.toLocaleString("fr-FR")} icon={CreditCard} color="#8B5CF6" />
          </div>
        )}

        {!isLoading && stats && (
          <div className="surface-card mt-4 p-5">
            <h2 className="text-lg font-semibold" style={{ color: "var(--tx-head)" }}>
              Lecture rapide
            </h2>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="rounded-2xl p-4" style={{ background: "rgba(34,87,255,0.08)" }}>
                <p className="text-xs font-bold uppercase tracking-[0.14em]" style={{ color: "var(--p-500)" }}>
                  Traction
                </p>
                <p className="mt-2 text-sm leading-6" style={{ color: "var(--tx-head)" }}>
                  {stats.active_companies ?? 0} entreprises actives soutiennent {stats.total_users ?? 0} utilisateurs sur la plateforme.
                </p>
              </div>
              <div className="rounded-2xl p-4" style={{ background: "rgba(0,214,143,0.1)" }}>
                <p className="text-xs font-bold uppercase tracking-[0.14em]" style={{ color: "var(--s-600)" }}>
                  Activite
                </p>
                <p className="mt-2 text-sm leading-6" style={{ color: "var(--tx-head)" }}>
                  {stats.orders_this_month ?? 0} commandes ont ete traitees sur la periode courante.
                </p>
              </div>
              <div className="rounded-2xl p-4" style={{ background: "rgba(124,58,237,0.08)" }}>
                <p className="text-xs font-bold uppercase tracking-[0.14em]" style={{ color: "#7C3AED" }}>
                  Monetaire
                </p>
                <p className="mt-2 text-sm leading-6" style={{ color: "var(--tx-head)" }}>
                  Le revenu cumule observe atteint {(stats.revenue_xof ?? 0).toLocaleString("fr-FR")} FCFA.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
