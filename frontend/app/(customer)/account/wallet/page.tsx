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
} from "lucide-react";
import { walletApi } from "@/lib/api";
import { toast } from "sonner";

const OPERATORS = [
  { value: "wave", label: "Wave", color: "#0050FF" },
  { value: "orange_money", label: "Orange Money", color: "#FF6600" },
  { value: "free_money", label: "Free Money", color: "#E30613" },
  { value: "mtn_momo", label: "MTN MoMo", color: "#FFC200" },
];

const OPERATOR_COLOR: Record<string, string> = {
  wave: "#0050FF",
  orange_money: "#FF6600",
  free_money: "#E30613",
  mtn_momo: "#FFC200",
};

export default function WalletPage() {
  const [displayName, setDisplayName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [operator, setOperator] = useState("wave");
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["wallet-methods"],
    queryFn: () => walletApi.getMyMethods().then((r) => r.data),
  });

  const methods: any[] = data || [];

  const createMutation = useMutation({
    mutationFn: () =>
      walletApi.createMethod({
        method_type: "mobile_money",
        operator,
        phone_number: phoneNumber,
        display_name: displayName,
        is_default: !data?.length,
      }),
    onSuccess: () => {
      setDisplayName("");
      setPhoneNumber("");
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["wallet-methods"] });
      toast.success("Moyen de paiement ajouté");
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || "Erreur lors de l'ajout"),
  });

  const deleteMutation = useMutation({
    mutationFn: (methodId: string) => walletApi.deleteMethod(methodId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallet-methods"] });
      toast.success("Moyen de paiement supprimé");
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || "Erreur suppression"),
  });

  const setDefaultMutation = useMutation({
    mutationFn: (methodId: string) =>
      walletApi.updateMethod(methodId, { is_default: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallet-methods"] });
      toast.success("Moyen par défaut mis à jour");
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || "Erreur"),
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
        <div className="flex-1">
          <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>
            Wallet
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Vos moyens de paiement
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: "var(--p-500)", color: "#fff" }}
          aria-label="Ajouter un moyen de paiement"
        >
          <Plus size={18} />
        </button>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Formulaire d'ajout */}
        {showForm && (
          <div
            className="rounded-2xl p-4 space-y-3"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
              Nouveau Mobile Money
            </h2>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Ex : Mon compte principal"
              className="input-mobile"
            />
            <select
              value={operator}
              onChange={(e) => setOperator(e.target.value)}
              className="input-mobile"
            >
              {OPERATORS.map((op) => (
                <option key={op.value} value={op.value}>
                  {op.label}
                </option>
              ))}
            </select>
            <input
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+221 77 123 45 67"
              className="input-mobile"
              type="tel"
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowForm(false)}
                className="flex-1 py-3 rounded-xl font-semibold text-sm"
                style={{
                  background: "var(--bg-app)",
                  color: "var(--tx-muted)",
                  border: "1px solid var(--bd)",
                }}
              >
                Annuler
              </button>
              <button
                onClick={() => createMutation.mutate()}
                disabled={
                  !displayName.trim() || !phoneNumber.trim() || createMutation.isPending
                }
                className="flex-1 btn-primary"
              >
                {createMutation.isPending ? "Ajout…" : "Ajouter"}
              </button>
            </div>
          </div>
        )}

        {/* Liste Mobile Money */}
        <div
          className="rounded-2xl p-4 space-y-3"
          style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
        >
          <div className="flex items-center gap-2">
            <CreditCard size={16} style={{ color: "var(--p-500)" }} />
            <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
              Mobile Money
            </h2>
          </div>

          {isLoading && <div className="skeleton h-20 w-full rounded-xl" />}

          {!isLoading && methods.length === 0 && (
            <p className="text-sm py-1" style={{ color: "var(--tx-muted)" }}>
              Aucun moyen enregistré. Appuyez sur + pour en ajouter un.
            </p>
          )}

          {methods
            .filter((m) => m.method_type === "mobile_money")
            .map((method) => {
              const opColor = OPERATOR_COLOR[method.operator] || "var(--p-500)";
              const opLabel =
                OPERATORS.find((o) => o.value === method.operator)?.label ||
                method.operator;
              return (
                <div
                  key={method.id}
                  className="rounded-xl p-3.5 flex items-center gap-3"
                  style={{
                    background: "var(--bg-app)",
                    border: `1px solid ${method.is_default ? "var(--p-500)" : "var(--bd)"}`,
                  }}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: opColor + "18" }}
                  >
                    <CreditCard size={18} style={{ color: opColor }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p
                        className="font-semibold text-sm truncate"
                        style={{ color: "var(--tx-head)" }}
                      >
                        {method.display_name}
                      </p>
                      {method.is_default && (
                        <span
                          className="flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                          style={{
                            background: "var(--p-50)",
                            color: "var(--p-600)",
                          }}
                        >
                          Défaut
                        </span>
                      )}
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                      {opLabel} · {method.phone_number}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {method.is_default ? (
                      <div className="w-8 h-8 flex items-center justify-center">
                        <CheckCircle size={16} style={{ color: "var(--p-500)" }} />
                      </div>
                    ) : (
                      <button
                        onClick={() => setDefaultMutation.mutate(method.id)}
                        disabled={setDefaultMutation.isPending}
                        title="Définir par défaut"
                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                        style={{ background: "rgba(34,87,255,0.08)" }}
                      >
                        <Star size={14} style={{ color: "var(--p-500)" }} />
                      </button>
                    )}
                    <button
                      onClick={() => deleteMutation.mutate(method.id)}
                      disabled={deleteMutation.isPending}
                      className="w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{ background: "#FEF2F2" }}
                    >
                      <Trash2 size={14} style={{ color: "#DC2626" }} />
                    </button>
                  </div>
                </div>
              );
            })}
        </div>

        {/* Carte bancaire & virement — V2 */}
        <div
          className="rounded-2xl p-4 space-y-3"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--bd)",
            opacity: 0.65,
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Landmark size={16} style={{ color: "var(--tx-muted)" }} />
              <h2 className="font-bold text-sm" style={{ color: "var(--tx-muted)" }}>
                Carte bancaire & Virement
              </h2>
            </div>
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded-full"
              style={{
                background: "rgba(107,114,128,0.12)",
                color: "var(--tx-muted)",
                border: "1px solid var(--bd)",
              }}
            >
              Bientôt
            </span>
          </div>
          <div
            className="rounded-xl p-3 flex items-start gap-3"
            style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
          >
            <Lock size={15} className="flex-shrink-0 mt-0.5" style={{ color: "var(--tx-muted)" }} />
            <p className="text-xs leading-relaxed" style={{ color: "var(--tx-muted)" }}>
              Les paiements par carte bancaire et virements seront disponibles dans une
              prochaine mise à jour.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
