"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle,
  CreditCard,
  Landmark,
  Lock,
  Plus,
  Star,
  Trash2,
  X,
} from "lucide-react";
import { walletApi } from "@/lib/api";
import { toast } from "sonner";

const OPERATORS = [
  { value: "tmoney",       label: "T-Money",     desc: "Togocel",     color: "#E11D48" },
  { value: "flooz",        label: "Flooz",        desc: "Moov Africa", color: "#F97316" },
  { value: "wave",         label: "Wave",         desc: "Wave",        color: "#1D4ED8" },
  { value: "orange_money", label: "Orange Money", desc: "Orange",      color: "#EA580C" },
  { value: "mtn_momo",     label: "MTN MoMo",     desc: "MTN",         color: "#CA8A04" },
];

function operatorInfo(value: string) {
  return OPERATORS.find((o) => o.value === value) ?? { label: value, color: "#64748B", desc: "" };
}

/* ── Sélecteur d'opérateur iOS-style ── */
function OperatorPicker({ selected, onSelect }: { selected: string; onSelect: (v: string) => void }) {
  return (
    <div>
      <p className="section-label mb-2">Opérateur</p>
      <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--bd)", background: "#fff" }}>
        {OPERATORS.map((op, i) => {
          const active = selected === op.value;
          return (
            <button
              key={op.value}
              onClick={() => onSelect(op.value)}
              className="w-full flex items-center gap-3 px-4 py-3.5 text-left active:bg-gray-50 transition-colors"
              style={{ borderBottom: i < OPERATORS.length - 1 ? "1px solid var(--bd)" : "none" }}
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 text-white text-xs font-black"
                style={{ background: op.color }}
              >
                {op.label[0]}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-bold text-sm" style={{ color: "#111111" }}>{op.label}</p>
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{op.desc}</p>
              </div>
              <div
                className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors"
                style={{
                  borderColor: active ? "#111111" : "var(--bd)",
                  background:  active ? "#111111" : "transparent",
                }}
              >
                {active && <div className="w-2 h-2 rounded-full bg-white" />}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ── Feuille modale d'ajout ── */
function AddSheet({ onClose, existingCount }: { onClose: () => void; existingCount: number }) {
  const queryClient = useQueryClient();
  const [operator, setOperator] = useState("tmoney");
  const [phone,    setPhone]    = useState("");
  const [alias,    setAlias]    = useState("");

  const addMutation = useMutation({
    mutationFn: () =>
      walletApi.createMethod({
        method_type:  "mobile_money",
        operator,
        phone_number: phone.trim(),
        display_name: alias.trim() || operatorInfo(operator).label,
        is_default:   existingCount === 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallet-methods"] });
      toast.success("Numéro ajouté");
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur lors de l'ajout"),
  });

  const canSubmit = phone.trim().length >= 8 && !addMutation.isPending;

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end"
      style={{ background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="rounded-t-3xl overflow-y-auto"
        style={{ background: "#FFFFFF", maxHeight: "90dvh", paddingBottom: "env(safe-area-inset-bottom, 24px)" }}
      >
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full" style={{ background: "var(--n-200)" }} />
        </div>

        <div className="px-5 py-3 flex items-center justify-between">
          <h2 className="text-xl font-black" style={{ color: "#111111" }}>Ajouter un numéro</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ background: "var(--n-100)" }}
          >
            <X size={16} style={{ color: "#111111" }} />
          </button>
        </div>

        <div className="px-5 pt-2 space-y-5 pb-4">
          <OperatorPicker selected={operator} onSelect={setOperator} />

          <div>
            <p className="section-label mb-2">Numéro de téléphone</p>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+228 90 XX XX XX"
              className="input-mobile"
              autoFocus
            />
          </div>

          <div>
            <p className="section-label mb-2">Alias (facultatif)</p>
            <input
              type="text"
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="Ex : Mon compte principal"
              className="input-mobile"
            />
          </div>

          <div
            className="flex items-center gap-2.5 px-4 py-3 rounded-2xl"
            style={{ background: "var(--n-50)", border: "1px solid var(--bd)" }}
          >
            <Lock size={14} style={{ color: "var(--tx-muted)" }} className="flex-shrink-0" />
            <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
              Aucun code PIN n'est jamais stocké.
            </p>
          </div>

          <button
            onClick={() => addMutation.mutate()}
            disabled={!canSubmit}
            className="btn-action"
          >
            {addMutation.isPending ? "Ajout en cours…" : "Enregistrer ce numéro"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Page principale ── */
export default function WalletPage() {
  const [showSheet, setShowSheet] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["wallet-methods"],
    queryFn: () => walletApi.getMyMethods().then((r) => r.data),
  });

  const methods: any[]   = data || [];
  const mobileMethods    = methods.filter((m) => m.method_type === "mobile_money");

  const deleteMutation = useMutation({
    mutationFn: (id: string) => walletApi.deleteMethod(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallet-methods"] });
      toast.success("Numéro supprimé");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur suppression"),
  });

  const setDefaultMutation = useMutation({
    mutationFn: (id: string) => walletApi.updateMethod(id, { is_default: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallet-methods"] });
      toast.success("Moyen par défaut mis à jour");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>

      {/* ─── Header ─── */}
      <header
        className="sticky top-0 z-40 flex items-center gap-3 px-5"
        style={{
          height: 56,
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--bd)",
        }}
      >
        <Link
          href="/account"
          className="w-9 h-9 rounded-full flex items-center justify-center"
          style={{ background: "var(--n-100)" }}
        >
          <ArrowLeft size={18} style={{ color: "#111111" }} />
        </Link>
        <div className="flex-1">
          <p className="font-black text-base" style={{ color: "#111111" }}>Wallet</p>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>Vos moyens de paiement</p>
        </div>
        <button
          onClick={() => setShowSheet(true)}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-bold text-white"
          style={{ background: "#111111" }}
        >
          <Plus size={14} />
          Ajouter
        </button>
      </header>

      <div className="px-4 py-5 space-y-4">

        {/* ─── Mobile Money ─── */}
        <div>
          <p className="section-label mb-2">Mobile Money</p>
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
          >
            {isLoading && (
              <>
                <div className="skeleton h-16 w-full" />
                <div className="skeleton h-16 w-full" style={{ borderTop: "1px solid var(--bd)" }} />
              </>
            )}

            {!isLoading && mobileMethods.length === 0 && (
              <div className="px-4 py-10 text-center">
                <CreditCard size={32} className="mx-auto mb-3" style={{ color: "var(--n-300)" }} />
                <p className="font-bold text-sm" style={{ color: "#111111" }}>Aucun numéro enregistré</p>
                <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
                  Appuyez sur "Ajouter" pour enregistrer un numéro Mobile Money.
                </p>
              </div>
            )}

            {mobileMethods.map((method, i) => {
              const op = operatorInfo(method.operator);
              return (
                <div
                  key={method.id}
                  className="flex items-center gap-3 px-4 py-3.5"
                  style={{ borderBottom: i < mobileMethods.length - 1 ? "1px solid var(--bd)" : "none" }}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 text-white font-black text-sm"
                    style={{ background: op.color }}
                  >
                    {op.label[0]}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-bold text-sm truncate" style={{ color: "#111111" }}>
                        {method.display_name || op.label}
                      </p>
                      {method.is_default && (
                        <span
                          className="flex-shrink-0 text-[10px] font-black px-2 py-0.5 rounded-full text-white"
                          style={{ background: "#111111" }}
                        >
                          Défaut
                        </span>
                      )}
                    </div>
                    <p className="text-xs mt-0.5 font-mono" style={{ color: "var(--tx-muted)" }}>
                      {op.label} · {method.phone_number}
                    </p>
                  </div>

                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {method.is_default ? (
                      <div className="w-8 h-8 flex items-center justify-center">
                        <CheckCircle size={16} style={{ color: "var(--s-500)" }} />
                      </div>
                    ) : (
                      <button
                        onClick={() => setDefaultMutation.mutate(method.id)}
                        disabled={setDefaultMutation.isPending}
                        title="Définir par défaut"
                        className="w-8 h-8 rounded-xl flex items-center justify-center"
                        style={{ background: "var(--n-100)" }}
                      >
                        <Star size={14} style={{ color: "var(--tx-muted)" }} />
                      </button>
                    )}
                    <button
                      onClick={() => deleteMutation.mutate(method.id)}
                      disabled={deleteMutation.isPending}
                      className="w-8 h-8 rounded-xl flex items-center justify-center"
                      style={{ background: "#FEF2F2" }}
                    >
                      <Trash2 size={14} style={{ color: "#DC2626" }} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ─── Sécurité ─── */}
        <div
          className="flex items-start gap-3 px-4 py-3.5 rounded-2xl"
          style={{ background: "var(--n-50)", border: "1px solid var(--bd)" }}
        >
          <Lock size={15} style={{ color: "var(--tx-muted)" }} className="flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-bold" style={{ color: "#111111" }}>Paiement sécurisé</p>
            <p className="text-xs mt-0.5 leading-relaxed" style={{ color: "var(--tx-muted)" }}>
              Vos numéros sont uniquement utilisés pour pré-remplir les formulaires.
              Aucun code PIN ou mot de passe n'est jamais stocké.
            </p>
          </div>
        </div>

        {/* ─── Carte bancaire — bientôt ─── */}
        <div>
          <p className="section-label mb-2">Carte bancaire & Virement</p>
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "#FFFFFF", border: "1px solid var(--bd)", opacity: 0.6 }}
          >
            <div className="flex items-center justify-between px-4 py-4">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: "var(--n-100)" }}
                >
                  <Landmark size={18} style={{ color: "var(--tx-muted)" }} />
                </div>
                <div>
                  <p className="font-bold text-sm" style={{ color: "#111111" }}>Carte & Virement bancaire</p>
                  <p className="text-xs" style={{ color: "var(--tx-muted)" }}>Disponible prochainement</p>
                </div>
              </div>
              <span
                className="text-[10px] font-bold px-2.5 py-1 rounded-full"
                style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
              >
                Bientôt
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Feuille d'ajout ─── */}
      {showSheet && (
        <AddSheet
          onClose={() => setShowSheet(false)}
          existingCount={mobileMethods.length}
        />
      )}
    </div>
  );
}
