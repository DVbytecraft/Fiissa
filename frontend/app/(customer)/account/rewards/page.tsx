"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BadgePercent, Gift, Sparkles } from "lucide-react";
import { loyaltyApi } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmModal } from "@/components/ui/confirm-modal";

export default function RewardsPage() {
  const [redeemTarget, setRedeemTarget] = useState<{
    cardId: string;
    cardNumber: string;
    reward: any;
  } | null>(null);
  const queryClient = useQueryClient();

  const { data: cards, isLoading } = useQuery({
    queryKey: ["my-loyalty-cards"],
    queryFn: () => loyaltyApi.getMyCards().then((r) => r.data),
  });

  const nativeCards: any[] = (cards ?? []).filter((c: any) => c.card_type === "native" && c.program_id);

  const { data: rewardsMap } = useQuery({
    queryKey: ["card-rewards", nativeCards.map((c: any) => c.program_id).join(",")],
    queryFn: async () => {
      const entries = await Promise.all(
        nativeCards.map(async (card: any) => {
          const res = await loyaltyApi.getRewards(card.program_id).then((r) => r.data);
          return [card.program_id, res] as [string, any[]];
        })
      );
      return Object.fromEntries(entries);
    },
    enabled: nativeCards.length > 0,
  });

  const redeemMutation = useMutation({
    mutationFn: ({
      cardId,
      reward,
    }: {
      cardId: string;
      reward: any;
    }) =>
      loyaltyApi.redeemPoints(cardId, {
        card_id: cardId,
        points_amount: reward.points_cost,
        reward_id: reward.id,
        description: `Récompense : ${reward.name}`,
      }),
    onSuccess: () => {
      toast.success("Récompense réclamée — un coupon vous sera attribué par le marchand");
      queryClient.invalidateQueries({ queryKey: ["my-loyalty-cards"] });
      queryClient.invalidateQueries({ queryKey: ["my-coupons"] });
      setRedeemTarget(null);
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || "Erreur lors de l'échange"),
  });

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div
        className="px-5 pt-4 pb-4 flex items-center gap-3"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <Link href="/account" style={{ color: "var(--tx-muted)" }}>
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>
            Récompenses
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Échangez vos points contre des avantages
          </p>
        </div>
      </div>

      <div className="px-4 py-4 space-y-5">
        {isLoading && (
          <div className="space-y-3">
            {[0, 1].map((i) => <div key={i} className="skeleton h-32 w-full rounded-2xl" />)}
          </div>
        )}

        {!isLoading && nativeCards.length === 0 && (
          <div
            className="rounded-2xl p-8 text-center"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: "rgba(34,87,255,0.08)" }}>
              <Gift size={32} style={{ color: "var(--p-500)" }} />
            </div>
            <p className="font-bold text-base" style={{ color: "var(--tx-head)" }}>
              Aucune récompense disponible
            </p>
            <p className="text-sm mt-2 leading-relaxed" style={{ color: "var(--tx-muted)" }}>
              Accumez des points chez les marchands Fiissa pour débloquer des récompenses.
            </p>
            <Link
              href="/account/loyalty"
              className="inline-block mt-5 px-6 py-3 rounded-2xl font-bold text-sm text-white"
              style={{ background: "var(--p-500)" }}
            >
              Voir mes cartes
            </Link>
          </div>
        )}

        {nativeCards.map((card: any) => {
          const rewards: any[] = rewardsMap?.[card.program_id] ?? [];
          const activeRewards = rewards.filter((r) => r.is_active);

          return (
            <section key={card.id}>
              {/* Solde de la carte */}
              <div
                className="rounded-2xl p-4 mb-3 flex items-center justify-between"
                style={{
                  background: "linear-gradient(135deg, #0F172A 0%, #2257FF 100%)",
                  color: "#fff",
                }}
              >
                <div className="flex items-center gap-3">
                  <BadgePercent size={20} style={{ opacity: 0.8 }} />
                  <div>
                    <p className="text-xs" style={{ opacity: 0.7 }}>Carte Fiissa</p>
                    <p className="font-mono text-xs" style={{ opacity: 0.6 }}>
                      {card.card_number}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs" style={{ opacity: 0.7 }}>Points disponibles</p>
                  <p className="text-2xl font-semibold">{card.points_balance.toLocaleString("fr-FR")}</p>
                </div>
              </div>

              <p className="text-xs font-bold uppercase tracking-wide mb-3" style={{ color: "var(--tx-muted)" }}>
                Récompenses disponibles ({activeRewards.length})
              </p>

              {activeRewards.length === 0 && (
                <div
                  className="rounded-2xl p-5 text-center"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
                >
                  <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
                    Le marchand n'a pas encore configuré de récompenses pour ce programme.
                  </p>
                </div>
              )}

              <div className="space-y-3">
                {activeRewards.map((reward: any) => {
                  const canRedeem = card.points_balance >= reward.points_cost;
                  const discountText =
                    reward.reward_type === "discount_pct"
                      ? `−${reward.value}% sur votre prochaine commande`
                      : reward.reward_type === "discount_fixed"
                      ? `−${reward.value.toLocaleString("fr-FR")} F`
                      : reward.name;

                  return (
                    <div
                      key={reward.id}
                      className="rounded-2xl p-4"
                      style={{
                        background: "var(--bg-card)",
                        border: `1px solid ${canRedeem ? "rgba(0,214,143,0.25)" : "var(--bd)"}`,
                        opacity: canRedeem ? 1 : 0.6,
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                          style={{ background: canRedeem ? "rgba(0,214,143,0.1)" : "var(--bg-app)" }}
                        >
                          <Sparkles size={18} style={{ color: canRedeem ? "var(--s-500)" : "var(--tx-muted)" }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
                            {reward.name}
                          </p>
                          <p className="text-xs mt-0.5" style={{ color: canRedeem ? "var(--s-600)" : "var(--tx-muted)" }}>
                            {discountText}
                          </p>
                          {reward.description && (
                            <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
                              {reward.description}
                            </p>
                          )}
                        </div>
                        <div className="text-right flex-shrink-0">
                          <p className="font-semibold text-lg" style={{ color: canRedeem ? "var(--s-500)" : "var(--tx-muted)" }}>
                            {reward.points_cost.toLocaleString("fr-FR")}
                          </p>
                          <p className="text-[10px]" style={{ color: "var(--tx-muted)" }}>pts</p>
                        </div>
                      </div>

                      {canRedeem && (
                        <button
                          onClick={() => setRedeemTarget({ cardId: card.id, cardNumber: card.card_number, reward })}
                          className="w-full mt-3 py-2.5 rounded-xl font-bold text-sm"
                          style={{ background: "rgba(0,214,143,0.1)", color: "var(--s-600)", border: "1px solid rgba(0,214,143,0.3)" }}
                        >
                          Réclamer ({reward.points_cost.toLocaleString("fr-FR")} pts)
                        </button>
                      )}

                      {!canRedeem && (
                        <p className="text-xs mt-2 text-center" style={{ color: "var(--tx-muted)" }}>
                          Il vous manque {(reward.points_cost - card.points_balance).toLocaleString("fr-FR")} pts
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>

      <ConfirmModal
        open={!!redeemTarget}
        title="Réclamer cette récompense"
        message={`Échanger ${redeemTarget?.reward?.points_cost?.toLocaleString("fr-FR")} points de la carte ${redeemTarget?.cardNumber} contre "${redeemTarget?.reward?.name}" ?`}
        confirmLabel="Réclamer"
        variant="info"
        onConfirm={() =>
          redeemTarget &&
          redeemMutation.mutate({ cardId: redeemTarget.cardId, reward: redeemTarget.reward })
        }
        onCancel={() => setRedeemTarget(null)}
      />
    </div>
  );
}
