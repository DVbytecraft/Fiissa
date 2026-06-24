"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { ArrowLeft, Copy, Clock } from "lucide-react";
import { ordersApi, paymentsApi } from "@/lib/api";
import { toast } from "sonner";

const OPERATORS = [
  { id: "wave",         label: "Wave",         abbr: "W",  bg: "#1A56DB", light: "#EBF5FF", desc: "Paiement via Wave" },
  { id: "orange_money", label: "Orange Money", abbr: "OM", bg: "#F97316", light: "#FFF7ED", desc: "Orange Money USSD" },
  { id: "mtn_momo",    label: "MTN MoMo",     abbr: "M",  bg: "#EAB308", light: "#FEFCE8", desc: "MTN Mobile Money" },
  { id: "free_money",  label: "Free Money",   abbr: "FM", bg: "#EF4444", light: "#FEF2F2", desc: "Free Money Sénégal" },
  { id: "moov_money",  label: "Moov Money",   abbr: "MV", bg: "#0284C7", light: "#F0F9FF", desc: "Moov Africa Money" },
];

export default function PaymentPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params.orderId as string;

  const [step, setStep] = useState<"select_operator" | "instructions" | "submit" | "waiting">("select_operator");
  const [selectedOperator, setSelectedOperator] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [instructions, setInstructions] = useState<any>(null);
  const [transactionRef, setTransactionRef] = useState("");
  const [senderPhone, setSenderPhone] = useState("");

  const { data: order } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => ordersApi.getOrderDetail(orderId).then((r) => r.data),
  });

  const createPaymentMutation = useMutation({
    mutationFn: (operator: string) =>
      paymentsApi.create({
        order_id: orderId,
        company_id: order?.company_id,
        method: "mobile_money",
        operator,
      }),
    onSuccess: (res) => {
      setPaymentId(res.data.payment_id);
      setInstructions(res.data.instructions);
      setStep("instructions");
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur"),
  });

  const submitProofMutation = useMutation({
    mutationFn: () =>
      paymentsApi.submitProof(paymentId!, {
        transaction_ref: transactionRef.trim(),
        sender_phone: senderPhone.trim(),
      }),
    onSuccess: () => setStep("waiting"),
    onError: (e: any) => {
      const code = e.response?.data?.code;
      if (code === "duplicate_payment_ref") {
        toast.error("Cette référence a déjà été utilisée. Vérifiez votre saisie.");
      } else {
        toast.error(e.response?.data?.message || "Erreur");
      }
    },
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copié !");
  };

  if (!order) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-10 h-10 rounded-full border-4 border-t-transparent animate-spin" style={{ borderColor: `var(--p-500) transparent transparent transparent` }} />
      </div>
    );
  }

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div className="px-4 pt-4 pb-4 flex items-center" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <button onClick={() => router.back()} className="mr-3">
          <ArrowLeft size={22} style={{ color: "var(--tx-head)" }} />
        </button>
        <div>
          <h1 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>Paiement</h1>
          <p className="text-sm" style={{ color: "var(--tx-muted)" }}>Commande {order.order_number}</p>
        </div>
      </div>

      {/* Bloc montant */}
      <div className="mx-4 mt-4 rounded-2xl p-5 text-center" style={{ background: "var(--fiissa-gradient)", boxShadow: "var(--sh-brand)" }}>
        <p className="text-white/80 text-sm">Montant à payer</p>
        <p className="text-4xl font-black text-white mt-1">{order.total_xof?.toLocaleString("fr-FR")}</p>
        <p className="text-white/80 text-lg">FCFA</p>
      </div>

      {/* ÉTAPE 1 — Choisir l'opérateur */}
      {step === "select_operator" && (
        <div className="px-4 mt-6">
          <p className="text-xs font-black uppercase tracking-[0.16em] mb-4" style={{ color: "var(--tx-muted)" }}>
            Choisissez votre opérateur Mobile Money
          </p>
          <div className="space-y-2">
            {OPERATORS.map((op) => {
              const isSelected = selectedOperator === op.id;
              const isPending  = createPaymentMutation.isPending && isSelected;
              return (
                <button
                  key={op.id}
                  onClick={() => {
                    setSelectedOperator(op.id);
                    createPaymentMutation.mutate(op.id);
                  }}
                  disabled={createPaymentMutation.isPending}
                  className="w-full rounded-2xl p-4 flex items-center gap-4 active:scale-95 transition-all text-left"
                  style={{
                    background: isSelected ? op.light : "var(--bg-card)",
                    border: `2px solid ${isSelected ? op.bg : "var(--bd)"}`,
                  }}
                >
                  {/* Initiales colorées */}
                  <div
                    className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
                    style={{ background: op.bg }}
                  >
                    <span className="text-white font-black text-sm tracking-tight">{op.abbr}</span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="font-black text-base" style={{ color: "var(--tx-head)" }}>{op.label}</p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>{op.desc}</p>
                  </div>

                  {isPending ? (
                    <div
                      className="w-5 h-5 rounded-full border-2 border-t-transparent animate-spin shrink-0"
                      style={{ borderColor: `${op.bg} transparent transparent transparent` }}
                    />
                  ) : isSelected ? (
                    <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{ background: op.bg }}>
                      <span className="text-white text-xs font-black">✓</span>
                    </div>
                  ) : (
                    <div className="w-5 h-5 rounded-full shrink-0" style={{ border: `2px solid var(--bd)` }} />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ÉTAPE 2 — Instructions */}
      {step === "instructions" && instructions && (
        <div className="px-4 mt-6 space-y-4">
          <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-lg mb-4" style={{ color: "var(--tx-head)" }}>📱 Instructions de paiement</h2>
            <div className="space-y-3">
              {[
                { label: "Opérateur", value: instructions.operator },
                { label: "Numéro à envoyer", value: instructions.number, copyable: true },
                { label: "Nom du compte", value: instructions.account_name },
                { label: "Montant", value: `${order.total_xof?.toLocaleString("fr-FR")} FCFA` },
                { label: "Référence à indiquer", value: instructions.reference_to_include, copyable: true },
              ].map(({ label, value, copyable }) => (
                <div key={label} className="flex items-center justify-between py-2" style={{ borderBottom: "1px solid var(--bg-app)" }}>
                  <div>
                    <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{label}</p>
                    <p className="font-bold" style={{ color: "var(--tx-head)" }}>{value}</p>
                  </div>
                  {copyable && (
                    <button onClick={() => copyToClipboard(value)} className="p-2" style={{ color: "var(--p-500)" }}>
                      <Copy size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-xl p-3" style={{ background: "#FFFBEB", border: "1px solid #FDE68A" }}>
              <p className="text-sm font-bold" style={{ color: "#92400E" }}>⚠️ Important</p>
              <p className="text-sm mt-1" style={{ color: "#B45309" }}>
                Mentionnez la référence <strong>{instructions.reference_to_include}</strong> dans le motif de paiement.
              </p>
            </div>
          </div>

          <button onClick={() => setStep("submit")} className="btn-primary">
            J'ai effectué le paiement ✓
          </button>
        </div>
      )}

      {/* ÉTAPE 3 — Saisir la preuve */}
      {step === "submit" && (
        <div className="px-4 mt-6 space-y-4">
          <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-lg mb-2" style={{ color: "var(--tx-head)" }}>Confirmer votre paiement</h2>
            <p className="text-sm mb-5" style={{ color: "var(--tx-muted)" }}>
              Saisissez la référence de la transaction que vous venez d'effectuer.
            </p>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-semibold mb-1 block" style={{ color: "var(--tx-body)" }}>
                  Référence de transaction *
                </label>
                <input
                  type="text"
                  placeholder="Ex: WV20241125001234"
                  value={transactionRef}
                  onChange={(e) => setTransactionRef(e.target.value)}
                  className="input-mobile"
                />
              </div>
              <div>
                <label className="text-sm font-semibold mb-1 block" style={{ color: "var(--tx-body)" }}>
                  Numéro depuis lequel vous avez payé
                </label>
                <input
                  type="tel"
                  placeholder="Ex: +221 77 123 45 67"
                  value={senderPhone}
                  onChange={(e) => setSenderPhone(e.target.value)}
                  className="input-mobile"
                />
              </div>
            </div>
          </div>

          <button
            onClick={() => submitProofMutation.mutate()}
            disabled={!transactionRef || submitProofMutation.isPending}
            className="btn-primary"
          >
            {submitProofMutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <div className="spinner border-white border-t-transparent" />
                Envoi en cours...
              </span>
            ) : (
              "Soumettre mon paiement"
            )}
          </button>
        </div>
      )}

      {/* ÉTAPE 4 — En attente */}
      {step === "waiting" && (
        <div className="px-4 mt-6">
          <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto" style={{ background: "rgba(34,87,255,0.08)" }}>
              <Clock style={{ color: "var(--p-500)" }} size={40} />
            </div>
            <h2 className="text-xl font-bold mt-4" style={{ color: "var(--tx-head)" }}>Vérification en cours</h2>
            <p className="mt-2" style={{ color: "var(--tx-muted)" }}>
              Le magasin vérifie votre paiement. Vous serez notifié dès que c'est confirmé.
            </p>
            <div className="mt-6 rounded-xl p-4 text-left" style={{ background: "rgba(34,87,255,0.06)" }}>
              <p className="font-semibold text-sm" style={{ color: "var(--p-500)" }}>Que se passe-t-il ensuite ?</p>
              <ul className="mt-2 space-y-1 text-sm" style={{ color: "var(--p-500)" }}>
                <li>1. Le magasin vérifie la transaction</li>
                <li>2. Vous recevez une notification</li>
                <li>3. Votre commande est préparée</li>
                <li>4. Vous êtes prévenu quand c'est prêt</li>
              </ul>
            </div>
            <button onClick={() => router.push("/orders")} className="btn-secondary mt-6">
              Suivre mes commandes
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
