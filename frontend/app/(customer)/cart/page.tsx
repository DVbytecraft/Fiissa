"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Trash2, MapPin, Store, Truck } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useCartStore, useAuthStore } from "@/lib/store";
import { ordersApi } from "@/lib/api";
import { toast } from "sonner";

type DeliveryType = "click_collect" | "delivery";

export default function CartPage() {
  const router = useRouter();
  const { items, removeItem, updateQuantity, clearCart, storeId, companyId, total, itemCount } = useCartStore();
  const { isAuthenticated } = useAuthStore();
  const [step, setStep] = useState<"cart" | "delivery">("cart");
  const [deliveryType, setDeliveryType] = useState<DeliveryType>("click_collect");
  const [deliveryAddress, setDeliveryAddress] = useState({ street: "", city: "" });

  const createOrderMutation = useMutation({
    mutationFn: () =>
      ordersApi.createOrder({
        store_id: storeId,
        company_id: companyId,
        order_type: deliveryType,
        delivery_address: deliveryType === "delivery" ? deliveryAddress : undefined,
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
        toast.error("Veuillez saisir votre adresse de livraison");
        return;
      }
      createOrderMutation.mutate();
    }
  };

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-4">
        <span className="text-6xl mb-4">🛒</span>
        <h2 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>Votre panier est vide</h2>
        <p className="mt-2 text-center" style={{ color: "var(--tx-muted)" }}>Ajoutez des produits depuis un commerce</p>
        <button onClick={() => router.push("/")} className="mt-6 btn-primary max-w-xs">
          Découvrir les commerces
        </button>
      </div>
    );
  }

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div className="px-4 pt-4 pb-4 flex items-center" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <button onClick={() => step === "cart" ? router.back() : setStep("cart")} className="mr-3">
          <ArrowLeft size={22} style={{ color: "var(--tx-head)" }} />
        </button>
        <h1 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>
          {step === "cart" ? "Mon panier" : "Mode de récupération"}
        </h1>
      </div>

      {step === "cart" && (
        <>
          <div className="px-4 py-4 space-y-3">
            {items.map((item) => (
              <div key={item.productId} className="rounded-2xl p-4 flex items-center gap-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
                {item.imageUrl ? (
                  <img src={item.imageUrl} alt={item.name} className="w-16 h-16 rounded-xl object-cover" />
                ) : (
                  <div className="w-16 h-16 rounded-xl flex items-center justify-center text-2xl" style={{ background: "var(--bg-app)" }}>🛒</div>
                )}
                <div className="flex-1">
                  <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>{item.name}</p>
                  <p className="font-bold mt-1" style={{ color: "var(--p-500)" }}>
                    {item.price.toLocaleString("fr-FR")} FCFA
                  </p>
                  <div className="flex items-center gap-3 mt-2">
                    <button
                      onClick={() => updateQuantity(item.productId, item.quantity - 1)}
                      className="w-7 h-7 rounded-full flex items-center justify-center font-bold"
                      style={{ background: "var(--bg-app)", color: "var(--tx-body)" }}
                    >
                      −
                    </button>
                    <span className="font-bold w-6 text-center" style={{ color: "var(--tx-head)" }}>{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.productId, item.quantity + 1)}
                      className="w-7 h-7 rounded-full flex items-center justify-center text-white font-bold"
                      style={{ background: "var(--p-500)" }}
                    >
                      +
                    </button>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
                    {(item.price * item.quantity).toLocaleString("fr-FR")} FCFA
                  </p>
                  <button
                    onClick={() => removeItem(item.productId)}
                    className="mt-2 active:opacity-70"
                    style={{ color: "#EF4444" }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Résumé */}
          <div className="mx-4 rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <div className="flex justify-between text-sm" style={{ color: "var(--tx-muted)" }}>
              <span>Sous-total ({itemCount()} articles)</span>
              <span>{total().toLocaleString("fr-FR")} FCFA</span>
            </div>
            <div className="flex justify-between font-bold text-lg mt-2 pt-2" style={{ color: "var(--tx-head)", borderTop: "1px solid var(--bd)" }}>
              <span>Total</span>
              <span>{total().toLocaleString("fr-FR")} FCFA</span>
            </div>
          </div>
        </>
      )}

      {step === "delivery" && (
        <div className="px-4 py-6 space-y-4">
          {[
            {
              type: "click_collect" as DeliveryType,
              icon: Store,
              title: "Retrait en magasin",
              desc: "Commandez maintenant, récupérez quand c'est prêt",
              badge: "Gratuit",
            },
            {
              type: "delivery" as DeliveryType,
              icon: Truck,
              title: "Livraison à domicile",
              desc: "Recevez votre commande chez vous",
              badge: "Selon distance",
            },
          ].map(({ type, icon: Icon, title, desc, badge }) => (
            <button
              key={type}
              onClick={() => setDeliveryType(type)}
              className="w-full text-left p-4 rounded-2xl transition-all"
              style={{
                border: `2px solid ${deliveryType === type ? "var(--p-500)" : "var(--bd)"}`,
                background: deliveryType === type ? "rgba(34,87,255,0.04)" : "var(--bg-card)",
              }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center"
                  style={{ background: deliveryType === type ? "var(--p-500)" : "var(--bg-app)" }}
                >
                  <Icon size={22} style={{ color: deliveryType === type ? "#fff" : "var(--tx-muted)" }} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-bold" style={{ color: "var(--tx-head)" }}>{title}</p>
                    <span className="text-xs px-2 py-0.5 rounded-full font-semibold" style={{ background: "rgba(0,214,143,0.12)", color: "var(--s-500)" }}>{badge}</span>
                  </div>
                  <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>{desc}</p>
                </div>
                {deliveryType === type && (
                  <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ background: "var(--p-500)" }}>
                    <span className="text-white text-sm">✓</span>
                  </div>
                )}
              </div>
            </button>
          ))}

          {deliveryType === "delivery" && (
            <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
              <div className="flex items-center gap-2 mb-2">
                <MapPin size={18} style={{ color: "var(--p-500)" }} />
                <h3 className="font-semibold" style={{ color: "var(--tx-head)" }}>Adresse de livraison</h3>
              </div>
              <input
                placeholder="Rue, quartier..."
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
            </div>
          )}

          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <div className="flex justify-between font-bold text-lg">
              <span style={{ color: "var(--tx-head)" }}>Total à payer</span>
              <span style={{ color: "var(--p-500)" }}>{total().toLocaleString("fr-FR")} FCFA</span>
            </div>
          </div>
        </div>
      )}

      {/* Bouton action */}
      <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto px-4 pb-8 pt-4" style={{ background: "var(--bg-app)" }}>
        <button onClick={handleCheckout} disabled={createOrderMutation.isPending} className="btn-primary">
          {createOrderMutation.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <div className="spinner border-white border-t-transparent" />
              Création de la commande...
            </span>
          ) : step === "cart" ? (
            `Commander — ${total().toLocaleString("fr-FR")} FCFA`
          ) : (
            "Confirmer et payer"
          )}
        </button>
      </div>
    </div>
  );
}
