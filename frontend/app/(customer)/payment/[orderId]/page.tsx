"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  ArrowLeft, Copy, Check, Clock, Shield,
  Smartphone, ChevronRight,
} from "lucide-react";
import { ordersApi, paymentsApi } from "@/lib/api";
import { toast } from "sonner";

/* ── Opérateurs Mobile Money Afrique de l'Ouest ── */
const OPERATORS = [
  { id: "tmoney",      label: "T-Money",      abbr: "TM", bg: "#E11D48", desc: "Togocel · *145#" },
  { id: "flooz",       label: "Flooz",         abbr: "FL", bg: "#F97316", desc: "Moov Africa · *155#" },
  { id: "wave",        label: "Wave",          abbr: "W",  bg: "#1D4ED8", desc: "Wave · App mobile" },
  { id: "orange_money",label: "Orange Money",  abbr: "OM", bg: "#EA580C", desc: "Orange · #144#" },
  { id: "mtn_momo",   label: "MTN MoMo",      abbr: "M",  bg: "#CA8A04", desc: "MTN · *170#" },
];

/* ── Utilitaire copier ── */
function useCopy() {
  const [copied, setCopied] = useState("");
  const copy = (text: string, key: string) => {
    navigator.clipboard?.writeText(text).catch(() => {});
    setCopied(key);
    setTimeout(() => setCopied(""), 2000);
  };
  return { copy, copied };
}

/* ─────────────────────────────────────────────────────────────
   Page principale
───────────────────────────────────────────────────────────── */
export default function PaymentPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const router      = useRouter();
  const { copy, copied } = useCopy();

  type Step = "select" | "instructions" | "submit" | "waiting" | "manual";
  const [step, setStep]             = useState<Step>("select");
  const [operator, setOperator]     = useState<string | null>(null);
  const [paymentId, setPaymentId]   = useState<string | null>(null);
  const [instructions, setInstructions] = useState<any>(null);
  const [txRef, setTxRef]           = useState("");
  const [senderPhone, setSenderPhone] = useState("");

  /* Chargement commande */
  const { data: order, isLoading } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => ordersApi.getOrderDetail(orderId).then((r) => r.data),
    enabled: !!orderId,
  });

  /* Détection mode paiement manuel du magasin */
  const isManualMode = (() => {
    const mode = order?.store?.payment_mode ?? order?.payment_mode ?? "";
    return mode === "manual" || mode === "GRATUIT_MANUEL" || mode === "free_manual";
  })();

  /* Mutation dédiée au mode manuel (create + submit en une seule passe) */
  const manualSubmitMutation = useMutation({
    mutationFn: async () => {
      const payRes = await paymentsApi.create({
        order_id: orderId,
        company_id: order?.company_id,
        method: "manual",
        operator: "manual",
      });
      const pid = payRes.data.payment_id ?? payRes.data.id;
      await paymentsApi.submitProof(pid, { transaction_ref: txRef.trim(), sender_phone: senderPhone.trim() });
    },
    onSuccess: () => {
      setStep("waiting");
      setTimeout(() => router.push(`/payment/${orderId}/success`), 2500);
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur lors de la finalisation"),
  });

  /* Créer le paiement */
  const createMutation = useMutation({
    mutationFn: (op: string) =>
      paymentsApi.create({ order_id: orderId, company_id: order?.company_id, method: "mobile_money", operator: op }),
    onSuccess: (res) => {
      setPaymentId(res.data.payment_id);
      setInstructions(res.data.instructions);
      setStep("instructions");
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur paiement"),
  });

  /* Soumettre la preuve */
  const submitMutation = useMutation({
    mutationFn: () =>
      paymentsApi.submitProof(paymentId!, { transaction_ref: txRef.trim(), sender_phone: senderPhone.trim() }),
    onSuccess: () => {
      setStep("waiting");
      /* Après 3s, rediriger vers la page succès */
      setTimeout(() => router.push(`/payment/${orderId}/success`), 3000);
    },
    onError: (e: any) => {
      const code = e.response?.data?.code;
      toast.error(
        code === "duplicate_payment_ref"
          ? "Cette référence a déjà été utilisée."
          : e.response?.data?.message || "Erreur"
      );
    },
  });

  const selectedOp = OPERATORS.find((o) => o.id === operator);

  /* Bascule auto en mode manuel dès que l'order est disponible */
  useEffect(() => {
    if (order && isManualMode && step === "select") {
      setStep("manual");
    }
  }, [order, isManualMode]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Loader ── */
  if (isLoading) {
    return (
      <div style={{ background: "var(--bg-layout)", minHeight: "100vh" }}>
        <div className="px-5 py-20 flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-full border-4 border-t-transparent animate-spin"
            style={{ borderColor: "var(--color-action) transparent transparent transparent" }} />
          <p style={{ color: "var(--tx-muted)" }}>Chargement…</p>
        </div>
      </div>
    );
  }

  if (!order) return null;

  return (
    <div style={{ background: "var(--bg-layout)", minHeight: "100vh" }}>

      {/* ─── Header ─── */}
      <header
        className="sticky top-0 z-40 flex items-center gap-3 px-5"
        style={{
          height: 56,
          background: "rgba(255,255,255,0.94)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--bd)",
        }}
      >
        <button
          onClick={() => step === "select" ? router.back() : setStep("select")}
          className="w-9 h-9 rounded-full flex items-center justify-center"
          style={{ background: "var(--n-100)" }}
        >
          <ArrowLeft size={18} style={{ color: "#111111" }} />
        </button>
        <div className="flex-1">
          <p className="font-black text-base" style={{ color: "#111111" }}>Paiement</p>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
            {order.order_number} · {order.store?.name ?? "Fiissa"}
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold"
          style={{ background: "var(--s-50)", color: "var(--s-700)" }}>
          <Shield size={12} />Sécurisé
        </div>
      </header>

      {/* ─── Bloc montant (toujours visible) ─── */}
      <div className="px-5 pt-5">
        <div
          className="rounded-3xl p-6 text-center"
          style={{ background: "#FFFFFF", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
        >
          <p className="section-label mb-2">Total à régler</p>
          <p className="text-5xl font-black tracking-tight" style={{ color: "#111111" }}>
            {order.total_xof?.toLocaleString("fr-FR")}
          </p>
          <p className="text-lg font-bold mt-1" style={{ color: "var(--tx-muted)" }}>FCFA</p>
          {selectedOp && (
            <div className="inline-flex items-center gap-2 mt-3 px-3 py-1.5 rounded-full text-xs font-bold"
              style={{ background: "var(--n-100)", color: "var(--tx-body)" }}>
              <div className="w-4 h-4 rounded-sm flex items-center justify-center text-white text-[8px] font-black"
                style={{ background: selectedOp.bg }}>{selectedOp.abbr}</div>
              {selectedOp.label}
            </div>
          )}
        </div>
      </div>

      {/* ══════════ MODE GRATUIT_MANUEL ══════════ */}
      {step === "manual" && (
        <div className="px-5 pt-5 space-y-4 pb-8">

          {/* Instruction principale */}
          <div
            className="rounded-3xl p-6 text-center"
            style={{ background: "#FFFFFF", border: "2.5px solid #111111" }}
          >
            <p className="text-4xl mb-4">💸</p>
            <p className="text-base font-bold" style={{ color: "#111111" }}>
              Veuillez envoyer
            </p>
            <p className="font-black mt-1 mb-1" style={{ fontSize: 42, color: "#111111", lineHeight: 1.1 }}>
              {order.total_xof?.toLocaleString("fr-FR")}
            </p>
            <p className="text-xl font-bold mb-4" style={{ color: "var(--tx-muted)" }}>FCFA</p>
            <p className="text-base font-bold" style={{ color: "#111111" }}>
              au code T-Money / Flooz Marchand de la boutique :
            </p>
            {/* Numéro marchand */}
            <div
              className="mt-4 py-4 px-5 rounded-2xl"
              style={{ background: "var(--n-50)", border: "1px solid var(--bd)" }}
            >
              <p
                className="font-black font-mono tracking-widest"
                style={{ fontSize: 28, color: "#111111" }}
              >
                {order.store?.merchant_phone
                  ?? order.store?.phone
                  ?? order.store?.contact_phone
                  ?? "Voir en caisse"}
              </p>
              {order.store?.name && (
                <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>{order.store.name}</p>
              )}
            </div>
          </div>

          {/* Champ ID transaction SMS */}
          <div
            className="rounded-2xl p-5 space-y-3"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
          >
            <div>
              <label className="field-label flex items-center gap-1 mb-2">
                ID de transaction SMS
                <span style={{ color: "#EF4444" }}>*</span>
              </label>
              <input
                type="text"
                placeholder="Ex : TGO20241225XXXXXX"
                value={txRef}
                onChange={(e) => setTxRef(e.target.value.toUpperCase())}
                className="input-mobile font-mono tracking-widest"
                autoComplete="off"
              />
              <p className="text-xs mt-1.5" style={{ color: "var(--tx-muted)" }}>
                L'identifiant reçu par SMS après votre transfert Mobile Money
              </p>
            </div>
            <div>
              <label className="field-label mb-2">Numéro expéditeur (optionnel)</label>
              <input
                type="tel"
                placeholder="+228 90 XX XX XX"
                value={senderPhone}
                onChange={(e) => setSenderPhone(e.target.value)}
                className="input-mobile"
              />
            </div>
          </div>

          <button
            onClick={() => {
              if (!txRef.trim()) {
                toast.error("Entrez l'ID de transaction reçu par SMS");
                return;
              }
              manualSubmitMutation.mutate();
            }}
            disabled={!txRef.trim() || manualSubmitMutation.isPending}
            className="btn-action"
          >
            {manualSubmitMutation.isPending ? (
              <span className="flex items-center gap-2">
                <div className="spinner border-white border-t-transparent" />
                Finalisation…
              </span>
            ) : (
              <>Finaliser l'achat ✓</>
            )}
          </button>

          <p className="text-center text-xs" style={{ color: "var(--n-400)" }}>
            🔒 Aucun code PIN n'est stocké
          </p>
        </div>
      )}

      {/* ══════════ ÉTAPE 1 — Choisir l'opérateur ══════════ */}
      {step === "select" && (
        <div className="px-5 pt-5 pb-8">
          <p className="section-label mb-3">Choisir votre opérateur</p>
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
          >
            {OPERATORS.map((op, i) => {
              const isSelected = operator === op.id;
              const isPending  = createMutation.isPending && isSelected;
              return (
                <button
                  key={op.id}
                  onClick={() => { setOperator(op.id); createMutation.mutate(op.id); }}
                  disabled={createMutation.isPending}
                  className="w-full flex items-center gap-4 px-5 py-4 text-left active:bg-gray-50 transition-colors disabled:opacity-60"
                  style={{ borderBottom: i < OPERATORS.length - 1 ? "1px solid var(--bg-layout)" : "none" }}
                >
                  <div
                    className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 text-white font-black text-sm"
                    style={{ background: op.bg }}
                  >
                    {op.abbr}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm" style={{ color: "#111111" }}>{op.label}</p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>{op.desc}</p>
                  </div>
                  {isPending
                    ? <div className="w-5 h-5 rounded-full border-2 border-t-transparent animate-spin"
                        style={{ borderColor: `${op.bg} transparent transparent transparent` }} />
                    : <ChevronRight size={16} style={{ color: "var(--n-300)" }} />
                  }
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ══════════ ÉTAPE 2 — Instructions ══════════ */}
      {step === "instructions" && instructions && (
        <div className="px-5 pt-5 space-y-4 pb-8">
          <p className="section-label">Instructions de transfert</p>

          <div className="rounded-2xl overflow-hidden" style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}>
            {[
              { label: "Numéro à envoyer", value: instructions.number, key: "num" },
              { label: "Nom du compte",    value: instructions.account_name, key: "name" },
              { label: "Montant exact",    value: `${order.total_xof?.toLocaleString("fr-FR")} FCFA`, key: "amt" },
              { label: "Référence",        value: instructions.reference_to_include, key: "ref" },
            ].map(({ label, value, key }, i, arr) => (
              <div
                key={key}
                className="flex items-center justify-between px-5 py-4"
                style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--bg-layout)" : "none" }}
              >
                <div className="min-w-0">
                  <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{label}</p>
                  <p className="font-black text-base mt-0.5 truncate" style={{ color: "#111111" }}>{value}</p>
                </div>
                <button
                  onClick={() => copy(value, key)}
                  className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ml-3 transition-colors"
                  style={{ background: copied === key ? "var(--s-500)" : "var(--n-100)" }}
                >
                  {copied === key
                    ? <Check size={14} className="text-white" />
                    : <Copy size={14} style={{ color: "var(--tx-muted)" }} />
                  }
                </button>
              </div>
            ))}
          </div>

          <div className="rounded-2xl p-4 flex items-start gap-3"
            style={{ background: "rgba(255,159,0,0.08)", border: "1px solid rgba(255,159,0,0.25)" }}>
            <span className="text-lg flex-shrink-0">⚠️</span>
            <p className="text-sm" style={{ color: "#92400E" }}>
              Mentionnez la référence <strong>{instructions.reference_to_include}</strong> dans le motif de votre transfert.
            </p>
          </div>

          <button onClick={() => setStep("submit")} className="btn-action">
            J'ai effectué le transfert →
          </button>
        </div>
      )}

      {/* ══════════ ÉTAPE 3 — Preuves ══════════ */}
      {step === "submit" && (
        <div className="px-5 pt-5 space-y-4 pb-8">
          <p className="section-label">Confirmer votre paiement</p>

          <div className="rounded-2xl overflow-hidden" style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}>
            <div className="px-5 py-5 space-y-4">
              <div>
                <label className="field-label">Référence de transaction *</label>
                <input
                  type="text"
                  placeholder="Ex : TGO20241225XXXXXX"
                  value={txRef}
                  onChange={(e) => setTxRef(e.target.value.toUpperCase())}
                  className="input-mobile font-mono tracking-widest"
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="field-label">Numéro expéditeur (optionnel)</label>
                <input
                  type="tel"
                  placeholder="+228 90 XX XX XX"
                  value={senderPhone}
                  onChange={(e) => setSenderPhone(e.target.value)}
                  className="input-mobile"
                />
              </div>
            </div>
          </div>

          <button
            onClick={() => submitMutation.mutate()}
            disabled={!txRef.trim() || submitMutation.isPending}
            className="btn-action"
          >
            {submitMutation.isPending
              ? <span className="flex items-center gap-2"><div className="spinner border-white border-t-transparent" />Vérification…</span>
              : <><Shield size={18} />Soumettre mon paiement</>
            }
          </button>

          <p className="text-center text-xs" style={{ color: "var(--n-400)" }}>
            🔒 Aucun code PIN n'est stocké
          </p>
        </div>
      )}

      {/* ══════════ ÉTAPE 4 — En attente ══════════ */}
      {step === "waiting" && (
        <div className="px-5 pt-8 pb-8 flex flex-col items-center text-center gap-6">
          <div className="relative">
            <div className="w-24 h-24 rounded-full flex items-center justify-center"
              style={{ background: "var(--s-50)" }}>
              <div className="w-16 h-16 rounded-full flex items-center justify-center animate-pulse"
                style={{ background: "var(--s-500)" }}>
                <Clock size={28} className="text-white" />
              </div>
            </div>
            <div className="absolute inset-0 rounded-full animate-ping opacity-20"
              style={{ background: "var(--s-500)" }} />
          </div>

          <div>
            <p className="text-2xl font-black" style={{ color: "#111111" }}>Vérification en cours</p>
            <p className="text-sm mt-2" style={{ color: "var(--tx-muted)" }}>
              Le magasin vérifie votre paiement. Redirection automatique…
            </p>
          </div>

          <div className="w-full rounded-2xl overflow-hidden" style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}>
            {[
              { done: true,  label: "Transfert soumis" },
              { done: false, label: "Vérification du magasin" },
              { done: false, label: "Génération du QR de sortie" },
            ].map(({ done, label }, i) => (
              <div key={i} className="flex items-center gap-3 px-5 py-3.5"
                style={{ borderBottom: i < 2 ? "1px solid var(--bg-layout)" : "none" }}>
                <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ background: done ? "var(--s-500)" : "var(--n-200)" }}>
                  {done
                    ? <Check size={13} className="text-white" />
                    : <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--n-400)" }} />
                  }
                </div>
                <p className="text-sm font-semibold" style={{ color: done ? "var(--s-700)" : "var(--tx-muted)" }}>
                  {label}
                </p>
              </div>
            ))}
          </div>

          <button onClick={() => router.push("/orders")} className="btn-secondary w-full">
            Voir mes commandes
          </button>
        </div>
      )}
    </div>
  );
}
