"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { ArrowLeft, Gift, MapPin, Minus, Plus, Store, Tag, Trash2, Truck, X } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useCartStore, useAuthStore } from "@/lib/store";
import { loyaltyApi, ordersApi } from "@/lib/api";
import { toast } from "sonner";

type DeliveryType = "click_collect" | "delivery";

export default function CartPage() {
  const router = useRouter();
  const { items, removeItem, updateQuantity, clearCart, storeId, companyId, total, itemCount } =
    useCartStore();
  const { isAuthenticated } = useAuthStore();
  const [step, setStep]                     = useState<"cart" | "delivery">("cart");
  const [deliveryType, setDeliveryType]     = useState<DeliveryType>("click_collect");
  const [deliveryAddress, setDeliveryAddress] = useState({ street: "", city: "", landmark: "" });
  const [couponCode, setCouponCode]         = useState("");

  const { data: loyaltyCard } = useQuery({
    queryKey: ["card-for-company", companyId],
    queryFn: () =>
      loyaltyApi.getCardForCompany(companyId!).then((r) => r.data),
    enabled: Boolean(isAuthenticated && companyId),
    retry: false,
  });

  const createOrderMutation = useMutation({
    mutationFn: () =>
      ordersApi.createOrder({
        store_id: storeId,
        company_id: companyId,
        order_type: deliveryType,
        delivery_address: deliveryType === "delivery" ? deliveryAddress : undefined,
        coupon_code: couponCode.trim() || undefined,
      }),
    onSuccess: (res) => {
      clearCart();
      router.push(`/payment/${res.data.id}`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || "Erreur lors de la commande");
    },
  });

  const handleCheckout = () => {
    if (!isAuthenticated) {
      router.push("/login?redirect=/cart");
      return;
    }
    if (step === "cart") {
      setStep("delivery");
    } else {
      if (deliveryType === "delivery" && !deliveryAddress.street) {
        toast.error("Saisis ton adresse de livraison");
        return;
      }
      if (deliveryType === "delivery" && !deliveryAddress.landmark.trim()) {
        toast.error("Les repères de livraison sont obligatoires");
        return;
      }
      createOrderMutation.mutate();
    }
  };

  /* ── Panier vide ── */
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-6">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center mb-5 text-4xl"
          style={{ background: "var(--n-100)" }}
        >
          🛒
        </div>
        <h2 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>
          Panier vide
        </h2>
        <p className="mt-2 text-center" style={{ color: "var(--tx-muted)" }}>
          Ajoute des produits depuis un commerce
        </p>
        <button onClick={() => router.push("/")} className="btn-primary mt-6 max-w-xs">
          Découvrir les commerces
        </button>
      </div>
    );
  }

  return (
    <div style={{ background: "var(--bg-layout)", minHeight: "100vh" }}>

      {/* ── Header ── */}
      <div
        className="px-5 py-4 flex items-center gap-3"
        style={{ background: "#FFFFFF", borderBottom: "1px solid var(--bd)" }}
      >
        <button
          onClick={() => (step === "cart" ? router.back() : setStep("cart"))}
          className="w-9 h-9 rounded-full flex items-center justify-center transition-colors"
          style={{ background: "var(--n-100)" }}
        >
          <ArrowLeft size={18} style={{ color: "var(--tx-head)" }} />
        </button>
        <div className="flex-1">
          <h1 className="text-lg font-semibold" style={{ color: "var(--tx-head)" }}>
            {step === "cart" ? "Mon panier" : "Mode de récupération"}
          </h1>
          {step === "cart" && (
            <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
              {itemCount()} article{itemCount() > 1 ? "s" : ""}
            </p>
          )}
        </div>
      </div>

      {/* ── Étape 1 : Articles ── */}
      {step === "cart" && (
        <div className="px-5 py-4 space-y-3">
          {items.map((item) => (
            <div
              key={item.productId}
              className="flex items-center gap-3 p-4 rounded-2xl"
              style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
            >
              {/* Miniature */}
              {item.imageUrl ? (
                <Image src={item.imageUrl} alt={item.name} width={64} height={64} unoptimized className="w-16 h-16 rounded-xl object-cover flex-shrink-0" />
              ) : (
                <div
                  className="w-16 h-16 rounded-xl flex items-center justify-center text-2xl flex-shrink-0"
                  style={{ background: "var(--n-100)" }}
                >
                  🛒
                </div>
              )}

              {/* Infos */}
              <div className="flex-1 min-w-0">
                <p className="font-bold text-sm truncate" style={{ color: "var(--tx-head)" }}>
                  {item.name}
                </p>
                <p className="font-bold mt-0.5 text-sm" style={{ color: "var(--tx-head)" }}>
                  {item.price.toLocaleString("fr-FR")} FCFA
                </p>
                {/* Quantité */}
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => updateQuantity(item.productId, item.quantity - 1)}
                    className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-lg transition-colors"
                    style={{ background: "var(--n-100)", color: "var(--tx-head)" }}
                  >
                    <Minus size={14} />
                  </button>
                  <span className="w-7 text-center font-bold text-sm" style={{ color: "var(--tx-head)" }}>
                    {item.quantity}
                  </span>
                  <button
                    onClick={() => updateQuantity(item.productId, item.quantity + 1)}
                    className="w-8 h-8 rounded-full flex items-center justify-center text-white font-bold transition-colors"
                    style={{ background: "var(--tx-head)" }}
                  >
                    <Plus size={14} />
                  </button>
                </div>
              </div>

              {/* Total ligne + supprimer */}
              <div className="flex flex-col items-end gap-3 flex-shrink-0">
                <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
                  {(item.price * item.quantity).toLocaleString("fr-FR")} F
                </p>
                <button
                  onClick={() => removeItem(item.productId)}
                  className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
                  style={{ background: "#FEF2F2" }}
                >
                  <Trash2 size={14} style={{ color: "#EF4444" }} />
                </button>
              </div>
            </div>
          ))}

          {/* Carte fidélité détectée */}
          {loyaltyCard && loyaltyCard.points_balance > 0 && (
            <div
              className="flex items-center gap-3 px-4 py-3 rounded-2xl"
              style={{ background: "rgba(34,87,255,0.06)", border: "1px solid rgba(34,87,255,0.18)" }}
            >
              <Gift size={18} style={{ color: "var(--p-500)", flexShrink: 0 }} />
              <div className="min-w-0">
                <p className="text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
                  {loyaltyCard.points_balance.toLocaleString("fr-FR")} pts disponibles
                </p>
                {loyaltyCard.tier_name && (
                  <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    Niveau {loyaltyCard.tier_name}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Coupon de réduction */}
          <div
            className="rounded-2xl p-4"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Tag size={14} style={{ color: "var(--tx-muted)" }} />
              <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--tx-muted)" }}>
                Code promo
              </span>
            </div>
            <div className="flex gap-2">
              <input
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                placeholder="MONCODE"
                className="input-mobile flex-1 font-mono text-sm"
              />
              {couponCode && (
                <button
                  onClick={() => setCouponCode("")}
                  className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
                  aria-label="Effacer le code"
                >
                  <X size={16} />
                </button>
              )}
            </div>
            <p className="text-xs mt-1.5" style={{ color: "var(--tx-muted)" }}>
              Le coupon sera appliqué à la confirmation
            </p>
          </div>

          {/* Récapitulatif */}
          <div
            className="rounded-2xl p-4 mt-2"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
          >
            <div className="flex justify-between text-sm mb-2" style={{ color: "var(--tx-muted)" }}>
              <span>Sous-total</span>
              <span>{total().toLocaleString("fr-FR")} FCFA</span>
            </div>
            {couponCode.trim() && (
              <div className="flex justify-between text-sm mb-2" style={{ color: "var(--p-500)" }}>
                <span className="font-semibold">Coupon · {couponCode.trim()}</span>
                <span>appliqué à la commande</span>
              </div>
            )}
            <div
              className="flex justify-between font-semibold text-sm pt-2"
              style={{ color: "var(--tx-head)", borderTop: "1px solid var(--bd)" }}
            >
              <span>Total</span>
              <span>{total().toLocaleString("fr-FR")} FCFA</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Étape 2 : Livraison ── */}
      {step === "delivery" && (
        <div className="px-5 py-5 space-y-4">
          {/* Options */}
          {[
            {
              type: "click_collect" as DeliveryType,
              icon: Store,
              title: "Retrait en magasin",
              desc: "Commande maintenant, récupère quand c'est prêt",
              badge: "Gratuit",
            },
            {
              type: "delivery" as DeliveryType,
              icon: Truck,
              title: "Livraison à domicile",
              desc: "Reçois ta commande chez toi",
              badge: "Selon distance",
            },
          ].map(({ type, icon: Icon, title, desc, badge }) => {
            const selected = deliveryType === type;
            return (
              <button
                key={type}
                onClick={() => setDeliveryType(type)}
                className="w-full text-left p-4 rounded-2xl transition-all active:scale-[0.99]"
                style={{
                  border: `2px solid ${selected ? "var(--tx-head)" : "var(--bd)"}`,
                  background: selected ? "var(--n-50)" : "#FFFFFF",
                }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: selected ? "var(--tx-head)" : "var(--n-100)" }}
                  >
                    <Icon size={22} style={{ color: selected ? "white" : "var(--tx-muted)" }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-bold" style={{ color: "var(--tx-head)" }}>{title}</p>
                      <span
                        className="text-xs px-2 py-0.5 rounded-full font-bold"
                        style={{ background: "var(--s-50)", color: "var(--s-700)" }}
                      >
                        {badge}
                      </span>
                    </div>
                    <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>{desc}</p>
                  </div>
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{
                      background: selected ? "var(--tx-head)" : "var(--n-200)",
                      border: `2px solid ${selected ? "var(--tx-head)" : "var(--n-300)"}`,
                    }}
                  >
                    {selected && <div className="w-2.5 h-2.5 rounded-full bg-white" />}
                  </div>
                </div>
              </button>
            );
          })}

          {/* Adresse livraison */}
          {deliveryType === "delivery" && (
            <div
              className="rounded-2xl p-4 space-y-3"
              style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
            >
              <div className="flex items-center gap-2 mb-1">
                <MapPin size={16} style={{ color: "var(--tx-head)" }} />
                <h3 className="font-bold" style={{ color: "var(--tx-head)" }}>Adresse de livraison</h3>
              </div>
              <input
                placeholder="Rue, quartier…"
                value={deliveryAddress.street}
                onChange={(e) => setDeliveryAddress((a) => ({ ...a, street: e.target.value }))}
                className="input-mobile"
              />
              <input
                placeholder="Ville"
                value={deliveryAddress.city}
                onChange={(e) => setDeliveryAddress((a) => ({ ...a, city: e.target.value }))}
                className="input-mobile"
              />
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide flex items-center gap-1 mb-1.5" style={{ color: "var(--tx-muted)" }}>
                  Indications et repères pour le livreur
                  <span style={{ color: "#EF4444" }}>*</span>
                </label>
                <textarea
                  placeholder="Ex : Maison barrière bleue, derrière la station Total, 2ème portail à gauche…"
                  value={deliveryAddress.landmark}
                  onChange={(e) => setDeliveryAddress((a) => ({ ...a, landmark: e.target.value }))}
                  rows={4}
                  className="input-mobile resize-none"
                  style={{ lineHeight: 1.6 }}
                  required
                />
                <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
                  Obligatoire — aide le livreur à vous trouver sans appel
                </p>
              </div>
            </div>
          )}

          {/* Récapitulatif total */}
          <div
            className="rounded-2xl p-4 space-y-2"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
          >
            {couponCode.trim() && (
              <div className="flex items-center gap-2">
                <Tag size={14} style={{ color: "var(--p-500)" }} />
                <span className="text-sm font-semibold flex-1" style={{ color: "var(--p-500)" }}>
                  Coupon · {couponCode.trim()}
                </span>
                <button onClick={() => setCouponCode("")} style={{ color: "var(--tx-muted)" }} aria-label="Retirer le coupon">
                  <X size={14} />
                </button>
              </div>
            )}
            <div className="flex justify-between font-semibold text-sm" style={{ color: "var(--tx-head)" }}>
              <span>Total à payer</span>
              <span>{total().toLocaleString("fr-FR")} FCFA</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Bouton CTA fixe — Orange Électrique ── */}
      <div
        className="fixed bottom-0 left-0 right-0 px-5 pb-8 pt-4"
        style={{ background: "rgba(255,255,255,0.96)", backdropFilter: "blur(20px)", borderTop: "1px solid var(--bd)" }}
      >
        <button
          onClick={handleCheckout}
          disabled={createOrderMutation.isPending}
          className="btn-primary"
        >
          {createOrderMutation.isPending ? (
            <span className="flex items-center gap-2">
              <div className="spinner border-white border-t-transparent" />
              Création de la commande…
            </span>
          ) : step === "cart" ? (
            `Commander · ${total().toLocaleString("fr-FR")} FCFA`
          ) : (
            "Confirmer et payer"
          )}
        </button>
      </div>
    </div>
  );
}
