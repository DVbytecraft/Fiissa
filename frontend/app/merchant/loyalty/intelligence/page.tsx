"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw, Users, TrendingUp, AlertTriangle, Clock } from "lucide-react";
import { loyaltyApi } from "@/lib/api";
import { toast } from "sonner";

const SEGMENT_CONFIG: Record<string, { label: string; bg: string; color: string; icon: any; desc: string }> = {
  vip:       { label: "VIP",          bg: "rgba(245,158,11,0.1)",  color: "#D97706",       icon: TrendingUp,    desc: "Acheteurs fréquents, panier élevé" },
  loyal:     { label: "Fidèle",       bg: "rgba(0,214,143,0.1)",   color: "var(--s-600)",  icon: Users,         desc: "Clients réguliers et engagés" },
  promising: { label: "Prometteur",   bg: "rgba(34,87,255,0.08)",  color: "var(--p-500)",  icon: TrendingUp,    desc: "Nouveaux avec bonne fréquence" },
  at_risk:   { label: "À risque",     bg: "rgba(249,115,22,0.1)",  color: "#EA580C",       icon: AlertTriangle, desc: "Actifs autrefois, en baisse d'activité" },
  dormant:   { label: "Inactif",      bg: "rgba(107,114,128,0.1)", color: "var(--tx-muted)", icon: Clock,       desc: "N'a pas commandé depuis longtemps" },
  new:       { label: "Nouveau",      bg: "rgba(139,92,246,0.1)",  color: "#7C3AED",       icon: Users,         desc: "Client récemment inscrit" },
};

function SegmentBadge({ segment }: { segment: string }) {
  const cfg = SEGMENT_CONFIG[segment] ?? { label: segment, bg: "var(--n-100)", color: "var(--tx-muted)", icon: Users, desc: "" };
  const Icon = cfg.icon;
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full flex-shrink-0"
      style={{ background: cfg.bg, color: cfg.color }}
    >
      <Icon size={10} />
      {cfg.label}
    </span>
  );
}

export default function LoyaltyIntelligencePage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["loyalty-intelligence"],
    queryFn: () => loyaltyApi.getCustomerScores().then((r) => r.data),
  });

  const recomputeMutation = useMutation({
    mutationFn: () => loyaltyApi.recomputeScores(),
    onSuccess: () => {
      toast.success("Recalcul lancé — les scores seront mis à jour sous peu");
      queryClient.invalidateQueries({ queryKey: ["loyalty-intelligence"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur lors du recalcul"),
  });

  const customers: any[] = Array.isArray(data) ? data : data?.items ?? data?.customers ?? [];

  const segmentCounts = customers.reduce((acc: Record<string, number>, c: any) => {
    const seg = c.rfm_segment ?? c.segment ?? "unknown";
    acc[seg] = (acc[seg] ?? 0) + 1;
    return acc;
  }, {});

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
          <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>Intelligence clients</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>Segments RFM — {customers.length} clients analysés</p>
        </div>
        <button
          onClick={() => recomputeMutation.mutate()}
          disabled={recomputeMutation.isPending}
          className="flex items-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold"
          style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
        >
          <RefreshCw size={13} className={recomputeMutation.isPending ? "animate-spin" : ""} />
          Recalculer
        </button>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Résumé segments */}
        {Object.keys(segmentCounts).length > 0 && (
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(segmentCounts).map(([seg, count]) => {
              const cfg = SEGMENT_CONFIG[seg] ?? { label: seg, bg: "var(--n-100)", color: "var(--tx-muted)", icon: Users, desc: "" };
              const Icon = cfg.icon;
              return (
                <div
                  key={seg}
                  className="rounded-2xl p-3 text-center"
                  style={{ background: cfg.bg, border: `1px solid ${cfg.color}20` }}
                >
                  <Icon size={18} className="mx-auto mb-1" style={{ color: cfg.color }} />
                  <p className="text-xl font-black" style={{ color: cfg.color }}>{count}</p>
                  <p className="text-[10px] font-semibold mt-0.5" style={{ color: cfg.color }}>{cfg.label}</p>
                </div>
              );
            })}
          </div>
        )}

        {/* Légende segments */}
        <div className="rounded-2xl p-4 space-y-2" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <p className="text-[10px] font-black uppercase tracking-[0.14em] mb-3" style={{ color: "var(--tx-muted)" }}>Légende RFM</p>
          {Object.entries(SEGMENT_CONFIG).map(([key, cfg]) => {
            const Icon = cfg.icon;
            return (
              <div key={key} className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: cfg.bg }}>
                  <Icon size={13} style={{ color: cfg.color }} />
                </div>
                <div>
                  <p className="text-xs font-bold" style={{ color: cfg.color }}>{cfg.label}</p>
                  <p className="text-[11px]" style={{ color: "var(--tx-muted)" }}>{cfg.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Liste clients */}
        <p className="text-[10px] font-black uppercase tracking-[0.14em]" style={{ color: "var(--tx-muted)" }}>
          Clients ({customers.length})
        </p>

        {isLoading && (
          <div className="space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-16 w-full rounded-2xl" />
            ))}
          </div>
        )}

        {!isLoading && customers.length === 0 && (
          <div className="text-center py-16">
            <Users size={52} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p className="font-semibold" style={{ color: "var(--tx-muted)" }}>Aucune donnée disponible</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
              Lancez un recalcul pour générer les scores RFM de vos clients.
            </p>
            <button
              onClick={() => recomputeMutation.mutate()}
              disabled={recomputeMutation.isPending}
              className="mt-4 py-2.5 px-6 rounded-full text-sm font-bold text-white"
              style={{ background: "var(--p-500)" }}
            >
              {recomputeMutation.isPending ? "Calcul en cours..." : "Lancer le calcul"}
            </button>
          </div>
        )}

        <div className="space-y-2">
          {customers.map((customer: any, idx: number) => {
            const segment = customer.rfm_segment ?? customer.segment ?? "unknown";
            const name = customer.customer_name ?? customer.name ?? customer.email ?? `Client #${idx + 1}`;
            const points = customer.total_points ?? customer.points_balance ?? 0;
            const orders = customer.order_count ?? customer.total_orders ?? 0;
            const lastOrder = customer.last_order_at ?? customer.last_purchase_at;
            const rfmScore = customer.rfm_score ?? null;

            return (
              <div
                key={customer.customer_id ?? customer.id ?? idx}
                className="rounded-2xl p-4 flex items-center gap-3"
                style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 font-black text-sm"
                  style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
                >
                  {String(name)[0]?.toUpperCase() ?? "C"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-bold text-sm truncate" style={{ color: "var(--tx-head)" }}>{name}</p>
                    <SegmentBadge segment={segment} />
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 text-xs" style={{ color: "var(--tx-muted)" }}>
                    <span>{orders} commandes</span>
                    <span>·</span>
                    <span>{points.toLocaleString("fr-FR")} pts</span>
                    {rfmScore !== null && (
                      <>
                        <span>·</span>
                        <span>Score {rfmScore}</span>
                      </>
                    )}
                  </div>
                  {lastOrder && (
                    <p className="text-[11px] mt-0.5" style={{ color: "var(--tx-muted)" }}>
                      Dernière commande : {new Date(lastOrder).toLocaleDateString("fr-FR")}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="h-6" />
      </div>
    </div>
  );
}
