"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  ArrowLeft,
  Award,
  ChevronDown,
  ChevronUp,
  Gift,
  RefreshCw,
  ShoppingBag,
  Star,
  TrendingDown,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { loyaltyApi } from "@/lib/api";
import { toast } from "sonner";

const SEGMENTS = [
  { key: null,        label: "Tous",       color: "var(--p-500)", bg: "var(--p-50)" },
  { key: "vip",       label: "VIP",        color: "#F59E0B",      bg: "#FFF8F0"     },
  { key: "loyal",     label: "Fidèles",    color: "#00A86B",      bg: "rgba(0,214,143,0.1)" },
  { key: "active",    label: "Actifs",     color: "var(--p-500)", bg: "var(--p-50)" },
  { key: "at_risk",   label: "À risque",   color: "#F97316",      bg: "#FFF5ED"     },
  { key: "new",       label: "Nouveaux",   color: "#8B5CF6",      bg: "#F5F0FF"     },
  { key: "inactive",  label: "Inactifs",   color: "#6B7280",      bg: "#F3F4F6"     },
] as const;

const SEGMENT_ICON: Record<string, any> = {
  vip: Star,
  loyal: TrendingUp,
  active: Zap,
  at_risk: TrendingDown,
  new: Users,
  inactive: Users,
};

// ── Composant profil fidélité ────────────────────────────────────────────────

function LoyaltyProfilePanel({ customerId }: { customerId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["customer-loyalty-profile", customerId],
    queryFn: () => loyaltyApi.getCustomerProfile(customerId).then((r) => r.data),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--bd)" }}>
        <div className="skeleton h-16 w-full rounded-xl" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div
        className="mt-3 pt-3"
        style={{ borderTop: "1px solid var(--bd)" }}
      >
        <p className="text-xs text-center" style={{ color: "var(--tx-muted)" }}>
          Impossible de charger le profil fidélité
        </p>
      </div>
    );
  }

  const segmentColor: Record<string, string> = {
    vip:      "#F59E0B",
    loyal:    "#00A86B",
    active:   "var(--p-500)",
    at_risk:  "#F97316",
    new:      "#8B5CF6",
    inactive: "#6B7280",
  };
  const segColor = segmentColor[data.segment] ?? "var(--tx-muted)";

  return (
    <div className="mt-3 pt-3 space-y-3" style={{ borderTop: "1px solid var(--bd)" }}>
      <p className="text-xs font-bold uppercase tracking-[0.12em]" style={{ color: "var(--tx-muted)" }}>
        Profil fidélité
      </p>
      <div className="grid grid-cols-3 gap-2">
        <div
          className="rounded-xl p-3 text-center"
          style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
        >
          <Award size={14} className="mx-auto mb-1" style={{ color: segColor }} />
          <p className="text-xs font-bold" style={{ color: "var(--tx-head)" }}>
            {data.segment ?? "—"}
          </p>
          <p className="text-[10px] mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Segment RFM
          </p>
        </div>
        <div
          className="rounded-xl p-3 text-center"
          style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
        >
          <Gift size={14} className="mx-auto mb-1" style={{ color: "var(--s-500)" }} />
          <p className="text-xs font-bold" style={{ color: "var(--tx-head)" }}>
            {data.total_points ?? data.points_balance ?? 0}
          </p>
          <p className="text-[10px] mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Points
          </p>
        </div>
        <div
          className="rounded-xl p-3 text-center"
          style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
        >
          <ShoppingBag size={14} className="mx-auto mb-1" style={{ color: "var(--p-500)" }} />
          <p className="text-xs font-bold" style={{ color: "var(--tx-head)" }}>
            {data.visit_count ?? data.order_count ?? 0}
          </p>
          <p className="text-[10px] mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Visites
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Page principale ──────────────────────────────────────────────────────────

export default function MerchantCustomersPage() {
  const [activeSegment, setActiveSegment] = useState<string | null>(null);
  const [expandedProfileId, setExpandedProfileId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["customer-scores", activeSegment],
    queryFn: () =>
      loyaltyApi
        .getCustomerScores(activeSegment ? { segment: activeSegment } : undefined)
        .then((r) => r.data),
  });

  const recomputeMutation = useMutation({
    mutationFn: () => loyaltyApi.recomputeScores(),
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["customer-scores"] });
      toast.success(
        `Scores recalculés — ${res.data?.computed_customers ?? 0} client(s) mis à jour`
      );
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || "Erreur lors du recalcul"),
  });

  const customers: any[] = data || [];
  const segInfo = SEGMENTS.find((s) => s.key === activeSegment) ?? SEGMENTS[0];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div
        className="px-5 pt-4 pb-4 flex items-center gap-3"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <Link href="/merchant/dashboard" style={{ color: "var(--tx-muted)" }}>
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>
            Clients
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Intelligence RFM
          </p>
        </div>
        <button
          onClick={() => recomputeMutation.mutate()}
          disabled={recomputeMutation.isPending}
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
          title="Recalculer les scores"
        >
          <RefreshCw
            size={16}
            style={{
              color: recomputeMutation.isPending ? "var(--p-500)" : "var(--tx-muted)",
              animation: recomputeMutation.isPending ? "spin 1s linear infinite" : "none",
            }}
          />
        </button>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Filtres segments */}
        <div
          className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4"
          style={{ scrollbarWidth: "none" }}
        >
          {SEGMENTS.map((seg) => (
            <button
              key={String(seg.key)}
              onClick={() => setActiveSegment(seg.key)}
              className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition-colors"
              style={{
                background: activeSegment === seg.key ? seg.color : "var(--bg-card)",
                color: activeSegment === seg.key ? "#fff" : "var(--tx-muted)",
                border: `1px solid ${activeSegment === seg.key ? seg.color : "var(--bd)"}`,
              }}
            >
              {seg.label}
            </button>
          ))}
        </div>

        {/* Compteur */}
        {customers.length > 0 && (
          <div
            className="rounded-xl p-2.5 flex items-center"
            style={{ background: segInfo.bg, border: `1px solid ${segInfo.color}30` }}
          >
            <p className="text-sm font-bold" style={{ color: segInfo.color }}>
              {customers.length} client{customers.length > 1 ? "s" : ""}
              {activeSegment ? ` — ${segInfo.label}` : " dans votre base"}
            </p>
          </div>
        )}

        {/* Liste */}
        {isLoading && (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="skeleton h-24 w-full rounded-2xl" />
            ))}
          </div>
        )}

        {!isLoading && customers.length === 0 && (
          <div
            className="rounded-2xl p-6 text-center"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <Users size={36} className="mx-auto mb-3" style={{ color: "var(--bd)" }} />
            <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>
              {activeSegment
                ? `Aucun client ${segInfo.label.toLowerCase()}`
                : "Aucun score calculé"}
            </p>
            <p className="text-xs mt-1 mb-4" style={{ color: "var(--tx-muted)" }}>
              Appuyez sur actualiser pour calculer les segments à partir de vos commandes
              confirmées.
            </p>
            <button
              onClick={() => recomputeMutation.mutate()}
              disabled={recomputeMutation.isPending}
              className="px-5 py-2.5 rounded-xl font-bold text-sm text-white"
              style={{ background: "var(--p-500)" }}
            >
              {recomputeMutation.isPending ? "Calcul…" : "Calculer maintenant"}
            </button>
          </div>
        )}

        <div className="space-y-2">
          {customers.map((score: any) => {
            const seg = SEGMENTS.find((s) => s.key === score.segment) ?? SEGMENTS[0];
            const Icon = SEGMENT_ICON[score.segment] ?? Users;
            return (
              <div
                key={score.id}
                className="rounded-2xl p-4"
                style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              >
                {/* Ligne principale */}
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: seg.bg }}
                  >
                    <Icon size={18} style={{ color: seg.color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <p
                        className="font-bold text-sm truncate"
                        style={{ color: "var(--tx-head)" }}
                      >
                        Client ·{" "}
                        <span className="font-mono text-xs">
                          {score.customer_id.slice(0, 8)}
                        </span>
                      </p>
                      <span
                        className="flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                        style={{ background: seg.bg, color: seg.color }}
                      >
                        {seg.label}
                      </span>
                    </div>
                    <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                      {score.order_count} commande{score.order_count > 1 ? "s" : ""} ·{" "}
                      {score.total_spent_xof.toLocaleString("fr-FR")} XOF
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="font-semibold text-xl" style={{ color: seg.color }}>
                      {score.rfm_score}
                    </p>
                    <p className="text-[10px]" style={{ color: "var(--tx-muted)" }}>
                      /15
                    </p>
                  </div>
                </div>

                {/* Barres RFM */}
                <div className="grid grid-cols-3 gap-2 mt-3">
                  {(
                    [
                      { label: "Récence", value: score.recency_score },
                      { label: "Fréquence", value: score.frequency_score },
                      { label: "Montant", value: score.monetary_score },
                    ] as const
                  ).map(({ label, value }) => (
                    <div
                      key={label}
                      className="rounded-lg p-2 text-center"
                      style={{ background: "var(--bg-app)" }}
                    >
                      <p
                        className="text-[10px] font-semibold mb-1.5"
                        style={{ color: "var(--tx-muted)" }}
                      >
                        {label}
                      </p>
                      <div className="flex gap-0.5 justify-center">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <div
                            key={i}
                            className="w-2.5 h-2.5 rounded-sm"
                            style={{
                              background: i <= value ? seg.color : "var(--bd)",
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Bouton profil fidélité */}
                <button
                  onClick={() =>
                    setExpandedProfileId(
                      expandedProfileId === score.customer_id ? null : score.customer_id
                    )
                  }
                  className="mt-3 w-full flex items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-bold transition-colors"
                  style={{
                    background:
                      expandedProfileId === score.customer_id
                        ? "rgba(34,87,255,0.10)"
                        : "var(--bg-app)",
                    color:
                      expandedProfileId === score.customer_id
                        ? "var(--p-500)"
                        : "var(--tx-muted)",
                    border: "1px solid var(--bd)",
                  }}
                >
                  <Award size={12} />
                  Voir profil fidélité
                  {expandedProfileId === score.customer_id ? (
                    <ChevronUp size={12} />
                  ) : (
                    <ChevronDown size={12} />
                  )}
                </button>

                {/* Panneau profil fidélité */}
                {expandedProfileId === score.customer_id && (
                  <LoyaltyProfilePanel customerId={score.customer_id} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
