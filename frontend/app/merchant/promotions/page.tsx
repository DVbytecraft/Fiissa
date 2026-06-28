"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Tag, Plus, Trash2, Pencil, X, Check } from "lucide-react";
import { promotionsApi } from "@/lib/api";
import { toast } from "sonner";

const TYPE_LABELS: Record<string, string> = {
  percentage:   "% Réduction",
  fixed_amount: "Montant fixe",
  free_shipping: "Livraison offerte",
  buy_x_get_y:  "X acheté → Y offert",
};

const APPLIES_LABELS: Record<string, string> = {
  all:           "Tout le catalogue",
  category:      "Catégorie",
  product:       "Produit spécifique",
  minimum_order: "Montant minimum",
};

function PromoForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: any;
  onSave: (data: any) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    name:                initial?.name ?? "",
    code:                initial?.code ?? "",
    promotion_type:      initial?.promotion_type ?? "percentage",
    value:               initial?.value ?? "",
    applies_to:          initial?.applies_to ?? "all",
    minimum_order_amount: initial?.minimum_order_amount ?? "",
    usage_limit:         initial?.usage_limit ?? "",
    per_customer_limit:  initial?.per_customer_limit ?? "",
    starts_at:           initial?.starts_at ? initial.starts_at.slice(0, 16) : "",
    ends_at:             initial?.ends_at ? initial.ends_at.slice(0, 16) : "",
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = () => {
    if (!form.name.trim() || !form.value) {
      toast.error("Nom et valeur sont obligatoires");
      return;
    }
    const payload: any = {
      name:           form.name.trim(),
      promotion_type: form.promotion_type,
      value:          Number(form.value),
      applies_to:     form.applies_to,
    };
    if (form.code.trim())               payload.code               = form.code.trim().toUpperCase();
    if (form.minimum_order_amount)      payload.minimum_order_amount = Number(form.minimum_order_amount);
    if (form.usage_limit)               payload.usage_limit         = Number(form.usage_limit);
    if (form.per_customer_limit)        payload.per_customer_limit  = Number(form.per_customer_limit);
    if (form.starts_at)                 payload.starts_at           = new Date(form.starts_at).toISOString();
    if (form.ends_at)                   payload.ends_at             = new Date(form.ends_at).toISOString();
    onSave(payload);
  };

  const inputStyle = {
    width: "100%",
    padding: "10px 12px",
    borderRadius: "12px",
    border: "1.5px solid var(--bd)",
    background: "var(--bg-app)",
    color: "var(--tx-body)",
    fontSize: "14px",
    outline: "none",
  };

  return (
    <div
      className="rounded-2xl p-5 space-y-3"
      style={{ background: "var(--bg-card)", border: "1.5px solid var(--bd)" }}
    >
      <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
        {initial ? "Modifier la promotion" : "Nouvelle promotion"}
      </p>

      <input style={inputStyle} placeholder="Nom de la promotion *" value={form.name} onChange={set("name")} />
      <input style={inputStyle} placeholder="Code promo (optionnel)" value={form.code} onChange={set("code")} />

      <div className="grid grid-cols-2 gap-2">
        <select style={inputStyle} value={form.promotion_type} onChange={set("promotion_type")}>
          {Object.entries(TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <input
          style={inputStyle}
          type="number"
          min="0"
          placeholder={form.promotion_type === "percentage" ? "Valeur % *" : "Valeur FCFA *"}
          value={form.value}
          onChange={set("value")}
        />
      </div>

      <select style={inputStyle} value={form.applies_to} onChange={set("applies_to")}>
        {Object.entries(APPLIES_LABELS).map(([k, v]) => (
          <option key={k} value={k}>{v}</option>
        ))}
      </select>

      {form.applies_to === "minimum_order" && (
        <input
          style={inputStyle}
          type="number"
          placeholder="Montant minimum FCFA"
          value={form.minimum_order_amount}
          onChange={set("minimum_order_amount")}
        />
      )}

      <div className="grid grid-cols-2 gap-2">
        <input
          style={inputStyle}
          type="number"
          placeholder="Limite d'utilisations"
          value={form.usage_limit}
          onChange={set("usage_limit")}
        />
        <input
          style={inputStyle}
          type="number"
          placeholder="Limite par client"
          value={form.per_customer_limit}
          onChange={set("per_customer_limit")}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[11px] mb-1" style={{ color: "var(--tx-muted)" }}>Début</p>
          <input style={inputStyle} type="datetime-local" value={form.starts_at} onChange={set("starts_at")} />
        </div>
        <div>
          <p className="text-[11px] mb-1" style={{ color: "var(--tx-muted)" }}>Fin</p>
          <input style={inputStyle} type="datetime-local" value={form.ends_at} onChange={set("ends_at")} />
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <button
          onClick={onCancel}
          className="flex-1 py-3 rounded-xl font-semibold text-sm"
          style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
        >
          Annuler
        </button>
        <button
          onClick={handleSubmit}
          className="flex-1 py-3 rounded-xl font-bold text-sm text-white"
          style={{ background: "var(--p-500)" }}
        >
          <Check size={15} className="inline mr-1" />
          {initial ? "Enregistrer" : "Créer"}
        </button>
      </div>
    </div>
  );
}

function PromoCard({ promo, onEdit, onDelete }: { promo: any; onEdit: () => void; onDelete: () => void }) {
  const isExpired = promo.ends_at && new Date(promo.ends_at) < new Date();
  const isScheduled = promo.starts_at && new Date(promo.starts_at) > new Date();

  const statusColor = !promo.is_active
    ? { bg: "var(--n-100)", text: "var(--tx-muted)", label: "Désactivée" }
    : isExpired
    ? { bg: "#FEF2F2", text: "#DC2626", label: "Expirée" }
    : isScheduled
    ? { bg: "#FFFBEB", text: "#D97706", label: "Planifiée" }
    : { bg: "#ECFDF5", text: "#059669", label: "Active" };

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
    >
      <div className="px-4 py-3 flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{promo.name}</p>
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={{ background: statusColor.bg, color: statusColor.text }}
            >
              {statusColor.label}
            </span>
          </div>
          {promo.code && (
            <p
              className="text-xs font-mono font-bold mt-1 px-2 py-0.5 rounded-lg inline-block"
              style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-600)" }}
            >
              {promo.code}
            </p>
          )}
        </div>
        <div className="flex gap-1 ml-2 shrink-0">
          <button
            onClick={onEdit}
            className="w-8 h-8 flex items-center justify-center rounded-xl"
            style={{ background: "var(--p-50)", color: "var(--p-600)" }}
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={onDelete}
            className="w-8 h-8 flex items-center justify-center rounded-xl"
            style={{ background: "#FEF2F2", color: "#DC2626" }}
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      <div
        className="px-4 py-2 flex flex-wrap gap-x-4 gap-y-1 text-xs"
        style={{ background: "var(--bg-app)", borderTop: "1px solid var(--bd)" }}
      >
        <span style={{ color: "var(--tx-muted)" }}>
          {TYPE_LABELS[promo.promotion_type]} :{" "}
          <strong style={{ color: "var(--tx-head)" }}>
            {promo.promotion_type === "percentage"
              ? `${promo.value}%`
              : `${Number(promo.value).toLocaleString("fr-FR")} FCFA`}
          </strong>
        </span>
        <span style={{ color: "var(--tx-muted)" }}>
          Utilisations : <strong style={{ color: "var(--tx-head)" }}>{promo.usage_count}{promo.usage_limit ? `/${promo.usage_limit}` : ""}</strong>
        </span>
        {promo.ends_at && (
          <span style={{ color: "var(--tx-muted)" }}>
            Expire : <strong style={{ color: "var(--tx-head)" }}>{new Date(promo.ends_at).toLocaleDateString("fr-FR")}</strong>
          </span>
        )}
      </div>
    </div>
  );
}

export default function MerchantPromotionsPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editPromo, setEditPromo] = useState<any>(null);

  const { data: promos, isLoading } = useQuery({
    queryKey: ["promotions"],
    queryFn: () => promotionsApi.getAll().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => promotionsApi.create(data),
    onSuccess: () => {
      toast.success("Promotion créée");
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["promotions"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => promotionsApi.update(id, data),
    onSuccess: () => {
      toast.success("Promotion mise à jour");
      setEditPromo(null);
      queryClient.invalidateQueries({ queryKey: ["promotions"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => promotionsApi.deactivate(id),
    onSuccess: () => {
      toast.success("Promotion désactivée");
      queryClient.invalidateQueries({ queryKey: ["promotions"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div className="px-5 pt-4 pb-4" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>Promotions</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
              {promos?.length ?? 0} promotion{promos?.length !== 1 ? "s" : ""}
            </p>
          </div>
          {!showForm && !editPromo && (
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 py-2 px-4 rounded-full text-sm font-bold text-white"
              style={{ background: "var(--p-500)" }}
            >
              <Plus size={15} />
              Nouvelle
            </button>
          )}
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        {/* Formulaire création */}
        {showForm && (
          <PromoForm
            onSave={(data) => createMutation.mutate(data)}
            onCancel={() => setShowForm(false)}
          />
        )}

        {/* Formulaire édition */}
        {editPromo && (
          <PromoForm
            initial={editPromo}
            onSave={(data) => updateMutation.mutate({ id: editPromo.id, data })}
            onCancel={() => setEditPromo(null)}
          />
        )}

        {/* Skeleton */}
        {isLoading &&
          [...Array(3)].map((_, i) => (
            <div key={i} className="rounded-2xl p-4 h-20" style={{ background: "var(--bg-card)" }}>
              <div className="skeleton h-full w-full rounded-xl" />
            </div>
          ))}

        {/* Vide */}
        {!isLoading && !promos?.length && !showForm && (
          <div className="text-center py-16">
            <Tag size={52} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p className="font-semibold" style={{ color: "var(--tx-muted)" }}>Aucune promotion</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
              Créez des codes promo ou des réductions automatiques
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="mt-4 py-2.5 px-6 rounded-full text-sm font-bold text-white"
              style={{ background: "var(--p-500)" }}
            >
              Créer une promotion
            </button>
          </div>
        )}

        {/* Liste */}
        {promos?.map((promo: any) => (
          <PromoCard
            key={promo.id}
            promo={promo}
            onEdit={() => { setEditPromo(promo); setShowForm(false); }}
            onDelete={() => {
              if (confirm(`Désactiver "${promo.name}" ?`)) deleteMutation.mutate(promo.id);
            }}
          />
        ))}
      </div>
    </div>
  );
}
