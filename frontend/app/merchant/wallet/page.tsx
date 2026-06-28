"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CreditCard,
  Pencil,
  Phone,
  Plus,
  Save,
  Trash2,
  Wallet,
  X,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { walletApi } from "@/lib/api";

const OPERATORS = [
  { value: "wave",         label: "Wave" },
  { value: "orange_money", label: "Orange Money" },
  { value: "mtn_momo",     label: "MTN MoMo" },
  { value: "moov_money",   label: "Moov Money" },
  { value: "free_money",   label: "Free Money" },
  { value: "flooz",        label: "Flooz" },
  { value: "tmoney",       label: "T-Money" },
];

const OPERATOR_COLORS: Record<string, { bg: string; color: string }> = {
  wave:         { bg: "rgba(0,100,255,0.08)",  color: "#0064FF" },
  orange_money: { bg: "rgba(255,100,0,0.09)",  color: "#FF6400" },
  mtn_momo:     { bg: "rgba(255,204,0,0.12)",  color: "#B8920A" },
  moov_money:   { bg: "rgba(0,180,80,0.09)",   color: "#00A850" },
  free_money:   { bg: "rgba(130,0,200,0.08)",  color: "#8200C8" },
  flooz:        { bg: "rgba(255,60,60,0.08)",  color: "#E02020" },
  tmoney:       { bg: "rgba(0,180,180,0.09)",  color: "#009696" },
};

function operatorLabel(value: string) {
  return OPERATORS.find((o) => o.value === value)?.label ?? value;
}

type Method = {
  id: string;
  name: string;
  phone: string;
  operator: string;
  is_active?: boolean;
};

type FormState = {
  name: string;
  phone: string;
  operator: string;
};

const EMPTY_FORM: FormState = { name: "", phone: "", operator: "wave" };

export default function MerchantWalletPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const { data, isLoading } = useQuery({
    queryKey: ["merchant-wallet-methods"],
    queryFn: () => walletApi.getMyMethods().then((r) => r.data),
  });

  const methods: Method[] = Array.isArray(data) ? data : data?.items ?? [];

  const createMutation = useMutation({
    mutationFn: () => walletApi.createMethod(form),
    onSuccess: () => {
      toast.success("Méthode ajoutée");
      setForm(EMPTY_FORM);
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["merchant-wallet-methods"] });
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || e.response?.data?.message || "Erreur lors de l'ajout"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: FormState }) =>
      walletApi.updateMethod(id, data),
    onSuccess: () => {
      toast.success("Méthode mise à jour");
      setEditingId(null);
      setForm(EMPTY_FORM);
      queryClient.invalidateQueries({ queryKey: ["merchant-wallet-methods"] });
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || e.response?.data?.message || "Erreur lors de la mise à jour"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => walletApi.deleteMethod(id),
    onSuccess: () => {
      toast.success("Méthode supprimée");
      queryClient.invalidateQueries({ queryKey: ["merchant-wallet-methods"] });
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || e.response?.data?.message || "Erreur lors de la suppression"),
  });

  function startEdit(method: Method) {
    setEditingId(method.id);
    setForm({ name: method.name, phone: method.phone, operator: method.operator });
    setShowForm(false);
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  function handleSubmit() {
    if (!form.name.trim() || !form.phone.trim()) {
      toast.error("Le nom et le numéro de téléphone sont requis");
      return;
    }
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: form });
    } else {
      createMutation.mutate();
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div
        className="px-5 pt-4 pb-4 flex items-center gap-3"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <Link href="/merchant/settings" style={{ color: "var(--tx-muted)" }}>
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>
            Méthodes wallet
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Gérez vos numéros de réception de paiement mobile
          </p>
        </div>
        {!showForm && !editingId && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-bold text-white"
            style={{ background: "var(--p-500)" }}
          >
            <Plus size={16} />
            Ajouter
          </button>
        )}
      </div>

      <div className="px-4 py-5 space-y-4">
        {/* Hero banner */}
        <div
          className="rounded-2xl p-5"
          style={{
            background: "linear-gradient(135deg, var(--p-500) 0%, var(--s-500) 100%)",
            boxShadow: "var(--sh-md)",
          }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
              <Wallet size={20} className="text-white" />
            </div>
            <div>
              <p className="text-white font-semibold text-sm">Portefeuille mobile</p>
              <p className="text-white/70 text-xs mt-0.5">
                {methods.length} méthode{methods.length !== 1 ? "s" : ""} enregistrée{methods.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <p className="text-white/80 text-xs leading-5">
            Ces méthodes sont proposées à vos clients comme options de paiement au moment du checkout.
          </p>
        </div>

        {/* Formulaire création / édition */}
        {(showForm || editingId) && (
          <div
            className="rounded-2xl border p-5 space-y-3"
            style={{ background: "var(--bg-card)", borderColor: "var(--bd)", boxShadow: "var(--sh-sm)" }}
          >
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-base font-semibold" style={{ color: "var(--tx-head)" }}>
                {editingId ? "Modifier la méthode" : "Nouvelle méthode"}
              </h2>
              <button
                onClick={() => {
                  setShowForm(false);
                  cancelEdit();
                }}
                className="w-8 h-8 rounded-xl flex items-center justify-center"
                style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
              >
                <X size={15} style={{ color: "var(--tx-muted)" }} />
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1.5" style={{ color: "var(--tx-muted)" }}>
                NOM DU COMPTE
              </label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Ex: Wave principal"
                className="input-mobile"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1.5" style={{ color: "var(--tx-muted)" }}>
                NUMÉRO DE TÉLÉPHONE
              </label>
              <input
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                placeholder="+228 90 00 00 00"
                type="tel"
                className="input-mobile"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1.5" style={{ color: "var(--tx-muted)" }}>
                OPÉRATEUR
              </label>
              <select
                value={form.operator}
                onChange={(e) => setForm((f) => ({ ...f, operator: e.target.value }))}
                className="input-mobile"
              >
                {OPERATORS.map((op) => (
                  <option key={op.value} value={op.value}>
                    {op.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleSubmit}
              disabled={isSaving}
              className="btn-primary"
            >
              <Save size={17} />
              {isSaving
                ? "Enregistrement..."
                : editingId
                ? "Mettre à jour"
                : "Ajouter la méthode"}
            </button>
          </div>
        )}

        {/* Liste des méthodes */}
        {isLoading && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="skeleton h-20 w-full rounded-2xl"
              />
            ))}
          </div>
        )}

        {!isLoading && methods.length === 0 && !showForm && (
          <div
            className="rounded-2xl p-10 text-center"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <CreditCard
              size={48}
              className="mx-auto mb-4"
              style={{ color: "var(--bd)" }}
            />
            <p className="font-semibold text-base" style={{ color: "var(--tx-head)" }}>
              Aucune méthode wallet
            </p>
            <p className="text-sm mt-1 mb-5" style={{ color: "var(--tx-muted)" }}>
              Ajoutez un numéro Wave, Orange Money ou autre pour recevoir les paiements de vos clients.
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold text-white"
              style={{ background: "var(--p-500)" }}
            >
              <Plus size={16} />
              Ajouter une méthode
            </button>
          </div>
        )}

        {!isLoading && methods.length > 0 && (
          <div className="space-y-3">
            {methods.map((method) => {
              const opStyle = OPERATOR_COLORS[method.operator] ?? {
                bg: "rgba(110,122,138,0.08)",
                color: "var(--tx-muted)",
              };
              const isEditing = editingId === method.id;

              return (
                <div
                  key={method.id}
                  className="rounded-2xl p-4"
                  style={{
                    background: "var(--bg-card)",
                    border: `1px solid ${isEditing ? "var(--p-500)" : "var(--bd)"}`,
                    boxShadow: "var(--sh-sm)",
                  }}
                >
                  <div className="flex items-center gap-3">
                    {/* Icône opérateur */}
                    <div
                      className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold"
                      style={{ background: opStyle.bg, color: opStyle.color }}
                    >
                      {operatorLabel(method.operator)
                        .split(" ")
                        .map((w) => w[0])
                        .join("")
                        .slice(0, 2)
                        .toUpperCase()}
                    </div>

                    {/* Infos */}
                    <div className="flex-1 min-w-0">
                      <p
                        className="font-semibold text-sm truncate"
                        style={{ color: "var(--tx-head)" }}
                      >
                        {method.name}
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <Phone size={11} style={{ color: "var(--tx-muted)" }} />
                        <p className="text-xs font-mono" style={{ color: "var(--tx-muted)" }}>
                          {method.phone}
                        </p>
                      </div>
                    </div>

                    {/* Badge opérateur */}
                    <span
                      className="flex-shrink-0 text-[10px] font-bold px-2 py-1 rounded-full"
                      style={{ background: opStyle.bg, color: opStyle.color }}
                    >
                      {operatorLabel(method.operator)}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 mt-3 pt-3" style={{ borderTop: "1px solid var(--bd)" }}>
                    <button
                      onClick={() => startEdit(method)}
                      className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-bold"
                      style={{ background: "rgba(34,87,255,0.07)", color: "var(--p-500)" }}
                    >
                      <Pencil size={13} />
                      Modifier
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Supprimer "${method.name}" ?`)) {
                          deleteMutation.mutate(method.id);
                        }
                      }}
                      disabled={deleteMutation.isPending}
                      className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-bold"
                      style={{ background: "rgba(239,68,68,0.07)", color: "var(--error)" }}
                    >
                      <Trash2 size={13} />
                      Supprimer
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
