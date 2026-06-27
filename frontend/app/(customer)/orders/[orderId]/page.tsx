"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, Package, Receipt, MapPin, QrCode, Clock, CheckCircle, Truck, UserCheck, Home, User } from "lucide-react";
import { ordersApi } from "@/lib/api";
import { toast } from "sonner";

const STATUS_STEPS = [
  { key: "confirmed",  label: "Confirmée" },
  { key: "preparing", label: "En préparation" },
  { key: "ready",     label: "Prête" },
  { key: "delivered", label: "Livrée" },
];

const STATUS_COLORS: Record<string, { color: string; bg: string; label: string }> = {
  draft:              { color: "var(--tx-muted)",  bg: "var(--bg-app)",            label: "Brouillon" },
  pending:            { color: "var(--tx-muted)",  bg: "var(--bg-app)",            label: "En attente" },
  awaiting_payment:   { color: "#F59E0B",          bg: "#FFFBEB",                  label: "Paiement attendu" },
  payment_submitted:  { color: "#F59E0B",          bg: "#FFFBEB",                  label: "Paiement soumis" },
  confirmed:          { color: "var(--p-500)",     bg: "rgba(34,87,255,0.08)",     label: "Confirmée" },
  preparing:          { color: "#F97316",          bg: "#FFF7ED",                  label: "En préparation" },
  ready:              { color: "var(--s-500)",     bg: "rgba(0,214,143,0.08)",     label: "Prête à retirer" },
  out_for_delivery:   { color: "var(--s-500)",     bg: "rgba(0,214,143,0.08)",     label: "En livraison" },
  delivered:          { color: "var(--s-500)",     bg: "rgba(0,214,143,0.08)",     label: "Livrée" },
  cancelled:          { color: "#EF4444",          bg: "#FEF2F2",                  label: "Annulée" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_COLORS[status] ?? { color: "var(--tx-muted)", bg: "var(--bg-app)", label: status };
  return (
    <span className="text-xs font-bold px-3 py-1.5 rounded-full" style={{ color: cfg.color, background: cfg.bg }}>
      {cfg.label}
    </span>
  );
}

function ProgressTracker({ status }: { status: string }) {
  const statusOrder = ["confirmed", "preparing", "ready", "delivered"];
  const currentIdx = statusOrder.indexOf(status);
  if (currentIdx === -1) return null;

  return (
    <div className="flex items-center gap-0">
      {STATUS_STEPS.map((step, idx) => {
        const done = idx <= currentIdx;
        const active = idx === currentIdx;
        return (
          <div key={step.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-black transition-all"
                style={done
                  ? { background: "var(--s-500)", color: "#fff" }
                  : { background: "var(--bg-app)", color: "var(--tx-muted)", border: "2px solid var(--bd)" }
                }
              >
                {done && !active ? "✓" : idx + 1}
              </div>
              <span className="text-xs font-medium text-center leading-tight" style={{ color: done ? "var(--tx-head)" : "var(--tx-muted)" }}>
                {step.label}
              </span>
            </div>
            {idx < STATUS_STEPS.length - 1 && (
              <div
                className="flex-1 h-0.5 mb-4 mx-1"
                style={{ background: idx < currentIdx ? "var(--s-500)" : "var(--bd)" }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function OrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params.orderId as string;

  const queryClient = useQueryClient();

  const { data: order, isLoading } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => ordersApi.getOne(orderId).then((r) => r.data),
    refetchInterval: 30000,
  });

  const [pickupEditing, setPickupEditing] = useState(false);
  const [pickupMode, setPickupMode] = useState("");
  const [delegateFirstName, setDelegateFirstName] = useState("");
  const [delegateLastName, setDelegateLastName] = useState("");
  const [delegateIdType, setDelegateIdType] = useState("carte_identite");
  const [deliveryAddress, setDeliveryAddress] = useState("");

  const setPickupMutation = useMutation({
    mutationFn: (payload: object) => ordersApi.setPickupMethod(orderId, payload),
    onSuccess: () => {
      toast.success("Mode de retrait enregistré");
      setPickupEditing(false);
      queryClient.invalidateQueries({ queryKey: ["order", orderId] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur lors de l'enregistrement"),
  });

  function submitPickup() {
    if (!pickupMode) return;
    if (pickupMode === "delegate") {
      if (!delegateFirstName.trim() || !delegateLastName.trim()) {
        toast.error("Prénom et nom du mandataire requis");
        return;
      }
    }
    if (pickupMode === "company_delivery" && !deliveryAddress.trim()) {
      toast.error("Adresse de livraison requise");
      return;
    }
    const payload: any = { fulfillment_method: pickupMode };
    if (pickupMode === "delegate") {
      payload.delegate_first_name = delegateFirstName.trim();
      payload.delegate_last_name = delegateLastName.trim();
      payload.delegate_id_type = delegateIdType;
    }
    if (pickupMode === "company_delivery") {
      payload.delivery_address = { address: deliveryAddress.trim() };
    }
    setPickupMutation.mutate(payload);
  }

  if (isLoading) {
    return (
      <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
        <div className="px-4 pt-4 pb-4 flex items-center" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
          <button onClick={() => router.back()} className="mr-3"><ArrowLeft size={22} style={{ color: "var(--tx-head)" }} /></button>
          <div className="skeleton h-6 w-40" />
        </div>
        <div className="px-4 py-4 space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}><div className="skeleton h-20 w-full" /></div>)}
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-6">
        <Package size={64} className="mb-4" style={{ color: "var(--bd)" }} />
        <p style={{ color: "var(--tx-muted)" }}>Commande introuvable</p>
        <button onClick={() => router.back()} className="btn-secondary mt-4">Retour</button>
      </div>
    );
  }

  const statusCfg = STATUS_COLORS[order.status] ?? STATUS_COLORS.pending;
  const isReady = order.status === "ready";
  const isDelivered = order.status === "delivered";

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div className="px-4 pt-4 pb-4 flex items-center justify-between" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()}>
            <ArrowLeft size={22} style={{ color: "var(--tx-head)" }} />
          </button>
          <div>
            <h1 className="font-black text-base" style={{ color: "var(--tx-head)" }}>{order.order_number}</h1>
            <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
              {new Date(order.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
            </p>
          </div>
        </div>
        <StatusBadge status={order.status} />
      </div>

      <div className="px-4 py-4 space-y-4 pb-8">

        {/* Barre de progression */}
        {["confirmed","preparing","ready","delivered"].includes(order.status) && (
          <div className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <ProgressTracker status={order.status} />
          </div>
        )}

        {/* Code retrait (si prêt) */}
        {isReady && order.pickup_code && (
          <div className="rounded-2xl p-5 text-center" style={{ background: "var(--s-500)", boxShadow: "var(--sh-green)" }}>
            <QrCode size={32} className="text-white mx-auto mb-2" />
            <p className="text-white/80 text-sm font-semibold">Votre commande est prête !</p>
            <p className="text-white font-black text-4xl mt-2 tracking-widest font-mono">{order.pickup_code}</p>
            <p className="text-white/70 text-xs mt-2">Présentez ce code en caisse</p>
          </div>
        )}

        {/* ── Procuration / Mode de retrait (click_collect & scan_go) ── */}
        {["click_collect", "scan_go"].includes(order.type) &&
         ["confirmed", "preparing", "ready"].includes(order.status) && (
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid var(--bg-app)" }}>
              <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Mode de retrait</p>
              {order.fulfillment_method && !pickupEditing && (
                <button onClick={() => { setPickupMode(order.fulfillment_method); setPickupEditing(true); }}
                  className="text-xs font-semibold" style={{ color: "var(--p-500)" }}>Modifier</button>
              )}
            </div>

            {/* Affichage du mode déjà choisi */}
            {order.fulfillment_method && !pickupEditing && (
              <div className="px-4 py-4 flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "rgba(34,87,255,0.08)" }}>
                  {order.fulfillment_method === "delegate"       && <UserCheck size={16} style={{ color: "var(--p-500)" }} />}
                  {order.fulfillment_method === "company_delivery" && <Home size={16} style={{ color: "var(--p-500)" }} />}
                  {order.fulfillment_method === "self_pickup"    && <User size={16} style={{ color: "var(--p-500)" }} />}
                </div>
                <div>
                  <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>
                    {order.fulfillment_method === "self_pickup"     && "Je viens moi-même"}
                    {order.fulfillment_method === "delegate"        && `Procuration — ${order.delegate_first_name ?? ""} ${order.delegate_last_name ?? ""}`.trim()}
                    {order.fulfillment_method === "company_delivery" && "Livraison à domicile demandée"}
                  </p>
                  {order.delegate_message && (
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>{order.delegate_message}</p>
                  )}
                </div>
              </div>
            )}

            {/* Formulaire choix / édition */}
            {(!order.fulfillment_method || pickupEditing) && (
              <div className="px-4 py-4 space-y-3">
                {/* Options */}
                {[
                  { value: "self_pickup",      icon: <User size={16} />,      label: "Je viens moi-même",         desc: "Je récupère la commande en personne" },
                  { value: "delegate",         icon: <UserCheck size={16} />, label: "J'envoie quelqu'un",         desc: "Procuration — je désigne un mandataire" },
                  { value: "company_delivery", icon: <Home size={16} />,      label: "Je veux être livré",         desc: "L'enseigne livre à mon adresse" },
                ].map((opt) => (
                  <button key={opt.value} onClick={() => setPickupMode(opt.value)}
                    className="w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all"
                    style={{
                      background: pickupMode === opt.value ? "rgba(34,87,255,0.08)" : "var(--bg-app)",
                      border: `1.5px solid ${pickupMode === opt.value ? "var(--p-500)" : "var(--bd)"}`,
                    }}>
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ background: pickupMode === opt.value ? "var(--p-500)" : "var(--bd)", color: "#fff" }}>
                      {opt.icon}
                    </div>
                    <div>
                      <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>{opt.label}</p>
                      <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{opt.desc}</p>
                    </div>
                  </button>
                ))}

                {/* Champs procuration */}
                {pickupMode === "delegate" && (
                  <div className="space-y-2 pt-1">
                    <div className="flex gap-2">
                      <input type="text" placeholder="Prénom *" value={delegateFirstName}
                        onChange={(e) => setDelegateFirstName(e.target.value)}
                        className="input-mobile flex-1" />
                      <input type="text" placeholder="Nom *" value={delegateLastName}
                        onChange={(e) => setDelegateLastName(e.target.value)}
                        className="input-mobile flex-1" />
                    </div>
                    <select value={delegateIdType} onChange={(e) => setDelegateIdType(e.target.value)}
                      className="input-mobile w-full">
                      <option value="carte_identite">Carte d'identité</option>
                      <option value="passeport">Passeport</option>
                      <option value="permis">Permis de conduire</option>
                      <option value="photo">Photo</option>
                    </select>
                    <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                      Le mandataire devra présenter sa pièce d'identité en magasin.
                    </p>
                  </div>
                )}

                {/* Champ adresse livraison */}
                {pickupMode === "company_delivery" && (
                  <input type="text" placeholder="Adresse de livraison *" value={deliveryAddress}
                    onChange={(e) => setDeliveryAddress(e.target.value)}
                    className="input-mobile w-full" />
                )}

                {/* Boutons */}
                <div className="flex gap-2 pt-1">
                  {pickupEditing && (
                    <button onClick={() => setPickupEditing(false)}
                      className="btn-secondary flex-1">Annuler</button>
                  )}
                  <button onClick={submitPickup}
                    disabled={!pickupMode || setPickupMutation.isPending}
                    className="btn-primary flex-1">
                    {setPickupMutation.isPending ? "Enregistrement…" : "Confirmer"}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Mode de livraison */}
        <div className="rounded-2xl p-4 flex items-center gap-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: order.type === "delivery" ? "rgba(0,214,143,0.1)" : "rgba(34,87,255,0.08)" }}>
            {order.type === "delivery" ? (
              <Truck size={18} style={{ color: "var(--s-500)" }} />
            ) : (
              <Package size={18} style={{ color: "var(--p-500)" }} />
            )}
          </div>
          <div>
            <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
              {order.type === "delivery" ? "Livraison à domicile" : order.type === "scan_go" ? "Scan & Go" : "Retrait en magasin"}
            </p>
            {order.delivery_address && (
              <p className="text-xs mt-0.5 flex items-center gap-1" style={{ color: "var(--tx-muted)" }}>
                <MapPin size={11} /> {order.delivery_address.street}, {order.delivery_address.city}
              </p>
            )}
            {!order.delivery_address && order.store_name && (
              <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>{order.store_name}</p>
            )}
          </div>
        </div>

        {/* Articles */}
        <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--bg-app)" }}>
            <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
              Articles ({order.items?.length ?? order.items_count ?? 0})
            </h2>
          </div>
          {(order.items ?? []).map((item: any) => (
            <div key={item.id} className="px-4 py-3 flex items-center gap-3" style={{ borderBottom: "1px solid var(--bg-app)" }}>
              {item.image_url ? (
                <Image src={item.image_url} alt={item.name} width={48} height={48} unoptimized className="w-12 h-12 rounded-xl object-cover shrink-0" />
              ) : (
                <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 text-xl" style={{ background: "var(--bg-app)" }}>🛍️</div>
              )}
              <div className="flex-1">
                <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>{item.product_name ?? item.name}</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>Qté : {item.quantity}</p>
              </div>
              <p className="font-bold text-sm shrink-0" style={{ color: "var(--p-500)" }}>
                {((item.unit_price_xof ?? item.price) * item.quantity).toLocaleString("fr-FR")} F
              </p>
            </div>
          ))}
          <div className="px-4 py-3 flex items-center justify-between">
            <span className="font-bold" style={{ color: "var(--tx-head)" }}>Total</span>
            <span className="font-black text-lg" style={{ color: "var(--p-500)" }}>
              {order.total_xof?.toLocaleString("fr-FR")} FCFA
            </span>
          </div>
        </div>

        {/* Statut paiement */}
        {order.payment_status && (
          <div className="rounded-2xl p-4 flex items-center gap-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "rgba(0,214,143,0.08)" }}>
              <CheckCircle size={18} style={{ color: "var(--s-500)" }} />
            </div>
            <div>
              <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Paiement Mobile Money</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                {order.payment_operator && `${order.payment_operator} · `}
                {order.payment_status === "confirmed" ? "Confirmé" : "En attente de confirmation"}
              </p>
            </div>
          </div>
        )}

        {/* Lien reçu */}
        {order.receipt_id && (
          <Link href={`/receipts/${order.receipt_id}`}>
            <div className="rounded-2xl p-4 flex items-center gap-3 active:scale-95 transition-transform" style={{ background: "rgba(34,87,255,0.06)", border: "1.5px solid var(--p-500)" }}>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "var(--p-500)" }}>
                <Receipt size={18} className="text-white" />
              </div>
              <div className="flex-1">
                <p className="font-bold text-sm" style={{ color: "var(--p-500)" }}>Voir le reçu</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>Télécharger le PDF ou scanner le QR</p>
              </div>
              <span className="text-sm" style={{ color: "var(--p-500)" }}>→</span>
            </div>
          </Link>
        )}

        {/* Payer si pas encore payé */}
        {order.status === "awaiting_payment" && (
          <Link href={`/payment/${order.id}`}>
            <button className="btn-primary">
              Payer maintenant — {order.total_xof?.toLocaleString("fr-FR")} FCFA
            </button>
          </Link>
        )}

        {/* En attente vérification */}
        {order.status === "payment_submitted" && (
          <div className="rounded-2xl p-4 text-center" style={{ background: "#FFFBEB", border: "1px solid #FDE68A" }}>
            <Clock size={24} className="mx-auto mb-2" style={{ color: "#D97706" }} />
            <p className="font-bold text-sm" style={{ color: "#92400E" }}>Paiement en cours de vérification</p>
            <p className="text-xs mt-1" style={{ color: "#B45309" }}>Le marchand vérifie votre transaction. Patience !</p>
          </div>
        )}

      </div>
    </div>
  );
}
