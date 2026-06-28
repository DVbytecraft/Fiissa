"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MapPin, Plus, Trash2, Pencil, Check, AlertCircle } from "lucide-react";
import { deliveryZonesApi, storesApi } from "@/lib/api";
import { toast } from "sonner";

function ZoneForm({
  storeId,
  initial,
  onSave,
  onCancel,
}: {
  storeId: string;
  initial?: any;
  onSave: (data: any) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    name:               initial?.name ?? "",
    description:        initial?.description ?? "",
    base_fee_xof:       initial?.base_fee_xof ?? "",
    per_km_fee_xof:     initial?.per_km_fee_xof ?? "",
    estimated_minutes:  initial?.estimated_minutes ?? "",
    radius_km:          initial?.radius_km ?? "",
    is_active:          initial?.is_active ?? true,
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = () => {
    if (!form.name.trim()) { toast.error("Le nom est obligatoire"); return; }
    if (form.base_fee_xof === "") { toast.error("Le tarif de base est obligatoire"); return; }
    const payload: any = {
      name:         form.name.trim(),
      base_fee_xof: Number(form.base_fee_xof),
    };
    if (form.description.trim())    payload.description       = form.description.trim();
    if (form.per_km_fee_xof !== "") payload.per_km_fee_xof   = Number(form.per_km_fee_xof);
    if (form.estimated_minutes !== "") payload.estimated_minutes = Number(form.estimated_minutes);
    if (form.radius_km !== "")      payload.radius_km         = Number(form.radius_km);
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
        {initial ? "Modifier la zone" : "Nouvelle zone de livraison"}
      </p>

      <input style={inputStyle} placeholder="Nom de la zone *" value={form.name} onChange={set("name")} />
      <textarea
        style={{ ...inputStyle, resize: "none", height: "72px" }}
        placeholder="Description (optionnel)"
        value={form.description}
        onChange={set("description")}
      />

      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[11px] mb-1" style={{ color: "var(--tx-muted)" }}>Tarif de base (FCFA) *</p>
          <input style={inputStyle} type="number" min="0" value={form.base_fee_xof} onChange={set("base_fee_xof")} />
        </div>
        <div>
          <p className="text-[11px] mb-1" style={{ color: "var(--tx-muted)" }}>Tarif/km (FCFA)</p>
          <input style={inputStyle} type="number" min="0" value={form.per_km_fee_xof} onChange={set("per_km_fee_xof")} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[11px] mb-1" style={{ color: "var(--tx-muted)" }}>Délai estimé (min)</p>
          <input style={inputStyle} type="number" min="0" value={form.estimated_minutes} onChange={set("estimated_minutes")} />
        </div>
        <div>
          <p className="text-[11px] mb-1" style={{ color: "var(--tx-muted)" }}>Rayon (km)</p>
          <input style={inputStyle} type="number" min="0" step="0.1" value={form.radius_km} onChange={set("radius_km")} />
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

function ZoneCard({
  zone,
  storeId,
  onEdit,
  onDelete,
}: {
  zone: any;
  storeId: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
    >
      <div className="px-4 py-3 flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{zone.name}</p>
            {!zone.is_active && (
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
              >
                Désactivée
              </span>
            )}
          </div>
          {zone.description && (
            <p className="text-xs mt-0.5 truncate" style={{ color: "var(--tx-muted)" }}>{zone.description}</p>
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
          Tarif de base : <strong style={{ color: "var(--tx-head)" }}>{zone.base_fee_xof?.toLocaleString("fr-FR")} FCFA</strong>
        </span>
        {zone.per_km_fee_xof > 0 && (
          <span style={{ color: "var(--tx-muted)" }}>
            + {zone.per_km_fee_xof?.toLocaleString("fr-FR")} FCFA/km
          </span>
        )}
        {zone.estimated_minutes && (
          <span style={{ color: "var(--tx-muted)" }}>
            Délai : <strong style={{ color: "var(--tx-head)" }}>{zone.estimated_minutes} min</strong>
          </span>
        )}
        {zone.radius_km && (
          <span style={{ color: "var(--tx-muted)" }}>
            Rayon : <strong style={{ color: "var(--tx-head)" }}>{zone.radius_km} km</strong>
          </span>
        )}
      </div>
    </div>
  );
}

export default function MerchantDeliveryZonesPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editZone, setEditZone] = useState<any>(null);

  const { data: store, isLoading: storeLoading } = useQuery({
    queryKey: ["my-store"],
    queryFn: () => storesApi.getMyStore().then((r) => r.data),
  });

  const storeId = store?.id;

  const { data: zones, isLoading } = useQuery({
    queryKey: ["delivery-zones", storeId],
    queryFn: () => deliveryZonesApi.list(storeId!).then((r) => r.data),
    enabled: !!storeId,
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => deliveryZonesApi.create(storeId!, data),
    onSuccess: () => {
      toast.success("Zone créée");
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["delivery-zones"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      deliveryZonesApi.update(storeId!, id, data),
    onSuccess: () => {
      toast.success("Zone mise à jour");
      setEditZone(null);
      queryClient.invalidateQueries({ queryKey: ["delivery-zones"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deliveryZonesApi.delete(storeId!, id),
    onSuccess: () => {
      toast.success("Zone supprimée");
      queryClient.invalidateQueries({ queryKey: ["delivery-zones"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  if (storeLoading) {
    return (
      <div className="px-4 py-4 space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="rounded-2xl p-4 h-20 skeleton" />
        ))}
      </div>
    );
  }

  if (!storeId) {
    return (
      <div className="px-5 py-12 text-center">
        <AlertCircle size={48} className="mx-auto mb-4" style={{ color: "var(--warning)" }} />
        <p className="font-semibold" style={{ color: "var(--tx-head)" }}>Aucun magasin trouvé</p>
        <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
          Configurez d'abord votre magasin dans les paramètres.
        </p>
      </div>
    );
  }

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div className="px-5 pt-4 pb-4" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>Zones de livraison</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
              {zones?.length ?? 0} zone{zones?.length !== 1 ? "s" : ""}
            </p>
          </div>
          {!showForm && !editZone && (
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 py-2 px-4 rounded-full text-sm font-bold text-white"
              style={{ background: "var(--p-500)" }}
            >
              <Plus size={15} />
              Nouvelle zone
            </button>
          )}
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        {showForm && (
          <ZoneForm
            storeId={storeId}
            onSave={(data) => createMutation.mutate(data)}
            onCancel={() => setShowForm(false)}
          />
        )}

        {editZone && (
          <ZoneForm
            storeId={storeId}
            initial={editZone}
            onSave={(data) => updateMutation.mutate({ id: editZone.id, data })}
            onCancel={() => setEditZone(null)}
          />
        )}

        {isLoading &&
          [...Array(2)].map((_, i) => (
            <div key={i} className="rounded-2xl p-4 h-20 skeleton" />
          ))}

        {!isLoading && !zones?.length && !showForm && (
          <div className="text-center py-16">
            <MapPin size={52} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p className="font-semibold" style={{ color: "var(--tx-muted)" }}>Aucune zone configurée</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
              Définissez les zones où vous livrez et leurs tarifs
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="mt-4 py-2.5 px-6 rounded-full text-sm font-bold text-white"
              style={{ background: "var(--p-500)" }}
            >
              Créer une zone
            </button>
          </div>
        )}

        {zones?.map((zone: any) => (
          <ZoneCard
            key={zone.id}
            zone={zone}
            storeId={storeId}
            onEdit={() => { setEditZone(zone); setShowForm(false); }}
            onDelete={() => {
              if (confirm(`Supprimer "${zone.name}" ?`)) deleteMutation.mutate(zone.id);
            }}
          />
        ))}
      </div>
    </div>
  );
}
