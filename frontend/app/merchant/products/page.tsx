"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Package, AlertTriangle, Upload, Pencil, Trash2, BarChart2, X } from "lucide-react";
import { catalogApi } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmModal } from "@/components/ui/confirm-modal";

function ProductFormModal({
  product,
  categories,
  onClose,
}: {
  product: any | null;
  categories: any[];
  onClose: () => void;
}) {
  const isEdit = Boolean(product);
  const queryClient = useQueryClient();

  const [name, setName] = useState(product?.name ?? "");
  const [barcode, setBarcode] = useState(product?.barcode ?? "");
  const [priceXof, setPriceXof] = useState(product?.price_xof?.toString() ?? "");
  const [categoryId, setCategoryId] = useState(product?.category_id ?? "");
  const [unit, setUnit] = useState(product?.unit ?? "piece");
  const [trackStock, setTrackStock] = useState<boolean>(product?.track_stock ?? true);
  const [stockQty, setStockQty] = useState(product?.stock_quantity?.toString() ?? "0");
  const [stockAlertQty, setStockAlertQty] = useState(product?.stock_alert_qty?.toString() ?? "10");
  const [isAvailable, setIsAvailable] = useState<boolean>(product?.is_available ?? true);
  const [description, setDescription] = useState(product?.description ?? "");

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = {
        name,
        barcode: barcode || undefined,
        price_xof: parseInt(priceXof),
        category_id: categoryId || undefined,
        unit,
        track_stock: trackStock,
        stock_quantity: trackStock ? parseInt(stockQty) : undefined,
        stock_alert_qty: trackStock ? parseInt(stockAlertQty) : undefined,
        is_available: isAvailable,
        description: description || undefined,
      };
      return isEdit
        ? catalogApi.updateProduct(product.id, payload)
        : catalogApi.createProduct(payload);
    },
    onSuccess: () => {
      toast.success(isEdit ? "Produit mis à jour" : "Produit créé");
      queryClient.invalidateQueries({ queryKey: ["merchant-products"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur"),
  });

  const isValid = name.trim() && priceXof && parseInt(priceXof) > 0;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end">
      <div
        style={{ background: "var(--bg-card)" }}
        className="rounded-t-3xl w-full p-6 space-y-4 max-h-[92vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between">
          <h3 style={{ color: "var(--tx-head)" }} className="text-lg font-bold">
            {isEdit ? "Modifier le produit" : "Ajouter un produit"}
          </h3>
          <button onClick={onClose} style={{ color: "var(--tx-muted)" }}>
            <X size={20} />
          </button>
        </div>

        {/* Nom */}
        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Nom du produit *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ex: Riz parfumé 5kg"
            className="input-mobile"
          />
        </div>

        {/* Prix + Code-barres */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
              Prix (XOF) *
            </label>
            <input
              type="number"
              value={priceXof}
              onChange={(e) => setPriceXof(e.target.value)}
              placeholder="3500"
              min="0"
              className="input-mobile"
            />
          </div>
          <div>
            <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
              Code-barres
            </label>
            <input
              type="text"
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              placeholder="6111..."
              className="input-mobile font-mono"
            />
          </div>
        </div>

        {/* Catégorie + Unité */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
              Catégorie
            </label>
            <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="input-mobile">
              <option value="">Sans catégorie</option>
              {categories.map((cat: any) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
              Unité
            </label>
            <select value={unit} onChange={(e) => setUnit(e.target.value)} className="input-mobile">
              {["piece", "kg", "g", "L", "mL", "sac", "bouteille", "boite", "paquet", "tube"].map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Stock */}
        <div>
          <label className="flex items-center gap-3 cursor-pointer mb-3">
            <div
              onClick={() => setTrackStock(!trackStock)}
              style={{
                background: trackStock ? "var(--p-500)" : "var(--bg-app)",
                border: `2px solid ${trackStock ? "var(--p-500)" : "var(--bd)"}`,
              }}
              className="w-5 h-5 rounded flex items-center justify-center shrink-0"
            >
              {trackStock && <span className="text-white text-xs font-bold">✓</span>}
            </div>
            <span style={{ color: "var(--tx-head)" }} className="text-sm font-semibold">
              Suivre le stock
            </span>
          </label>

          {trackStock && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
                  Quantité en stock
                </label>
                <input
                  type="number"
                  value={stockQty}
                  onChange={(e) => setStockQty(e.target.value)}
                  min="0"
                  className="input-mobile"
                />
              </div>
              <div>
                <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
                  Seuil d'alerte
                </label>
                <input
                  type="number"
                  value={stockAlertQty}
                  onChange={(e) => setStockAlertQty(e.target.value)}
                  min="0"
                  className="input-mobile"
                />
              </div>
            </div>
          )}
        </div>

        {/* Description */}
        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Description (optionnel)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Détails supplémentaires..."
            rows={2}
            style={{ borderColor: "var(--bd)", color: "var(--tx-head)" }}
            className="w-full p-3 border rounded-xl text-sm resize-none outline-none"
          />
        </div>

        {/* Disponibilité */}
        <label className="flex items-center gap-3 cursor-pointer">
          <div
            onClick={() => setIsAvailable(!isAvailable)}
            style={{
              background: isAvailable ? "var(--s-500)" : "var(--bg-app)",
              border: `2px solid ${isAvailable ? "var(--s-500)" : "var(--bd)"}`,
            }}
            className="w-5 h-5 rounded flex items-center justify-center shrink-0"
          >
            {isAvailable && <span className="text-white text-xs font-bold">✓</span>}
          </div>
          <span style={{ color: "var(--tx-head)" }} className="text-sm font-semibold">
            Produit disponible à la vente
          </span>
        </label>

        <div className="flex gap-3 pt-1">
          <button
            onClick={onClose}
            style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}
            className="flex-1 py-3 rounded-xl font-semibold"
          >
            Annuler
          </button>
          <button
            onClick={() => saveMutation.mutate()}
            disabled={!isValid || saveMutation.isPending}
            style={{ background: "var(--p-500)", boxShadow: "var(--sh-brand)" }}
            className="flex-1 py-3 text-white rounded-xl font-bold disabled:opacity-50"
          >
            {saveMutation.isPending ? "..." : isEdit ? "Mettre à jour" : "Créer le produit"}
          </button>
        </div>
      </div>
    </div>
  );
}

function StockBadge({ qty, alertQty }: { qty: number; alertQty: number | null }) {
  if (qty === 0) return <span className="badge badge-cancelled">Rupture</span>;
  if (alertQty && qty <= alertQty)
    return (
      <span className="badge badge-pending">
        {qty} restant{qty > 1 ? "s" : ""}
      </span>
    );
  return <span className="badge badge-delivered">{qty} en stock</span>;
}

function ProductRow({
  product,
  onEdit,
  onDelete,
  onAdjustStock,
}: {
  product: any;
  onEdit: (p: any) => void;
  onDelete: (id: string) => void;
  onAdjustStock: (p: any) => void;
}) {
  return (
    <div
      style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
      className="rounded-2xl p-4"
    >
      <div className="flex items-start gap-3">
        <div
          style={{ background: "var(--bg-app)" }}
          className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
        >
          {product.image_url ? (
            <Image
              src={product.image_url}
              alt={product.name}
              width={48}
              height={48}
              unoptimized
              className="w-full h-full object-cover rounded-xl"
            />
          ) : (
            <Package size={20} style={{ color: "var(--tx-muted)" }} />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p style={{ color: "var(--tx-head)" }} className="font-bold text-sm">
                {product.name}
              </p>
              <p style={{ color: "var(--tx-muted)" }} className="text-xs mt-0.5">
                {product.category_name || "Sans catégorie"}
              </p>
            </div>
            <p style={{ color: "var(--p-500)" }} className="font-bold shrink-0">
              {product.price_xof?.toLocaleString("fr-FR")} F
            </p>
          </div>

          <div className="flex items-center gap-2 mt-2">
            {product.track_stock ? (
              <StockBadge
                qty={product.stock_available ?? product.stock_quantity}
                alertQty={product.stock_alert_qty}
              />
            ) : (
              <span style={{ color: "var(--tx-muted)" }} className="text-xs">
                Stock non suivi
              </span>
            )}
            {product.barcode && (
              <span style={{ color: "var(--tx-muted)" }} className="text-xs font-mono">
                {product.barcode}
              </span>
            )}
          </div>
        </div>

        <div className="flex gap-1">
          <button
            onClick={() => onAdjustStock(product)}
            style={{ color: "var(--tx-muted)" }}
            className="p-2 rounded-lg"
            title="Ajuster stock"
          >
            <BarChart2 size={16} />
          </button>
          <button
            onClick={() => onEdit(product)}
            style={{ color: "var(--tx-muted)" }}
            className="p-2 rounded-lg"
            title="Modifier"
          >
            <Pencil size={16} />
          </button>
          <button
            onClick={() => onDelete(product.id)}
            style={{ color: "var(--tx-muted)" }}
            className="p-2 rounded-lg"
            title="Supprimer"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function StockAdjustModal({ product, onClose }: { product: any; onClose: () => void }) {
  const [qty, setQty] = useState("");
  const [reason, setReason] = useState("adjustment");
  const queryClient = useQueryClient();

  const adjustMutation = useMutation({
    mutationFn: () =>
      catalogApi.adjustStock(product.id, {
        quantity_change: parseInt(qty),
        reason,
        notes: "Ajustement manuel depuis dashboard",
      }),
    onSuccess: () => {
      toast.success("Stock mis à jour");
      queryClient.invalidateQueries({ queryKey: ["merchant-products"] });
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur"),
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end">
      <div
        style={{ background: "var(--bg-card)" }}
        className="rounded-t-3xl w-full p-6 space-y-4"
      >
        <h3 style={{ color: "var(--tx-head)" }} className="text-lg font-bold">
          Ajuster le stock
        </h3>
        <p style={{ color: "var(--tx-muted)" }} className="text-sm">
          <strong style={{ color: "var(--tx-head)" }}>{product.name}</strong> — Stock actuel :{" "}
          {product.stock_quantity}
        </p>

        <div>
          <label style={{ color: "var(--tx-head)" }} className="text-sm font-semibold mb-2 block">
            Variation (+ pour ajouter, - pour retirer)
          </label>
          <input
            type="number"
            placeholder="ex: +50 ou -10"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="input-mobile"
            autoFocus
          />
        </div>

        <div>
          <label style={{ color: "var(--tx-head)" }} className="text-sm font-semibold mb-2 block">
            Motif
          </label>
          <select value={reason} onChange={(e) => setReason(e.target.value)} className="input-mobile">
            <option value="adjustment">Ajustement manuel</option>
            <option value="purchase">Réception marchandise</option>
            <option value="loss">Perte / casse</option>
            <option value="return">Retour client</option>
          </select>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}
            className="flex-1 py-3 rounded-xl font-semibold"
          >
            Annuler
          </button>
          <button
            onClick={() => adjustMutation.mutate()}
            disabled={!qty || adjustMutation.isPending}
            style={{ background: "var(--p-500)" }}
            className="flex-1 py-3 text-white rounded-xl font-bold disabled:opacity-50"
          >
            {adjustMutation.isPending ? "..." : "Valider"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MerchantProductsPage() {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [stockFilter, setStockFilter] = useState<"all" | "low" | "out">("all");
  const [adjustingProduct, setAdjustingProduct] = useState<any>(null);
  const [editingProduct, setEditingProduct] = useState<any | null | undefined>(undefined);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["merchant-products", search, categoryFilter, stockFilter],
    queryFn: () =>
      catalogApi
        .getProducts({
          search,
          category_id: categoryFilter || undefined,
          stock_filter: stockFilter === "all" ? undefined : stockFilter,
        })
        .then((r) => r.data),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => catalogApi.getCategories().then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => catalogApi.deleteProduct(id),
    onSuccess: () => {
      toast.success("Produit supprimé");
      queryClient.invalidateQueries({ queryKey: ["merchant-products"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur suppression"),
  });

  const handleImportCSV = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await catalogApi.importCSV(formData);
        toast.success(`${res.data.created} produits importés`);
        queryClient.invalidateQueries({ queryKey: ["merchant-products"] });
      } catch (err: any) {
        toast.error(err.response?.data?.message || "Erreur import CSV");
      }
    };
    input.click();
  };

  const stockAlertCount =
    data?.items?.filter(
      (p: any) => p.track_stock && p.stock_alert_qty && p.stock_quantity <= p.stock_alert_qty
    ).length || 0;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      {/* Header */}
      <div
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
        className="px-6 pt-12 pb-4"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 style={{ color: "var(--tx-head)" }} className="text-xl font-bold">
              Produits
            </h1>
            <p style={{ color: "var(--tx-muted)" }} className="text-sm">
              {data?.total || 0} référence{(data?.total || 0) > 1 ? "s" : ""}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleImportCSV}
              style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}
              className="p-2 rounded-xl"
              title="Importer CSV"
            >
              <Upload size={20} />
            </button>
            <button
              onClick={() => setEditingProduct(null)}
              style={{ background: "var(--p-500)" }}
              className="p-2 text-white rounded-xl"
              title="Ajouter un produit"
            >
              <Plus size={20} />
            </button>
          </div>
        </div>

        {/* Import CSV — Bandeau format */}
        <div
          className="rounded-2xl px-4 py-3 mb-3 flex items-start gap-3"
          style={{ background: "var(--n-50)", border: "1px solid var(--bd)" }}
        >
          <Upload size={15} style={{ color: "var(--tx-muted)" }} className="flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-xs font-bold" style={{ color: "#111111" }}>Format CSV attendu</p>
            <p className="text-[11px] font-mono mt-0.5 leading-relaxed break-all" style={{ color: "var(--tx-muted)" }}>
              code_barres, designation, prix_fcfa, poids_grammes, quantite_stock
            </p>
          </div>
          <button
            onClick={handleImportCSV}
            className="shrink-0 px-3 py-1.5 rounded-xl text-xs font-bold text-white"
            style={{ background: "#111111" }}
          >
            Importer
          </button>
        </div>

        {/* Alertes stock */}
        {stockAlertCount > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-xl px-3 py-2 flex items-center gap-2 mb-3">
            <AlertTriangle size={16} className="text-orange-500" />
            <p className="text-orange-700 text-sm font-medium">
              {stockAlertCount} produit{stockAlertCount > 1 ? "s" : ""} en alerte de stock
            </p>
          </div>
        )}

        {/* Recherche */}
        <div className="relative mb-3">
          <Search size={16} style={{ color: "var(--tx-muted)" }} className="absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Rechercher un produit ou code-barres..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ background: "var(--bg-app)", color: "var(--tx-head)" }}
            className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm outline-none"
          />
        </div>

        {/* Filtres catégories */}
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-6 px-6 scrollbar-hide">
          <button
            onClick={() => setCategoryFilter("")}
            style={
              !categoryFilter
                ? { background: "var(--p-500)", color: "#fff" }
                : { background: "var(--bg-app)", color: "var(--tx-muted)" }
            }
            className="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium"
          >
            Tous
          </button>
          {(categories?.items || []).map((cat: any) => (
            <button
              key={cat.id}
              onClick={() => setCategoryFilter(cat.id)}
              style={
                categoryFilter === cat.id
                  ? { background: "var(--p-500)", color: "#fff" }
                  : { background: "var(--bg-app)", color: "var(--tx-muted)" }
              }
              className="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium"
            >
              {cat.name}
            </button>
          ))}
          <button
            onClick={() => setStockFilter(stockFilter === "low" ? "all" : "low")}
            className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium ${
              stockFilter === "low" ? "bg-orange-500 text-white" : "bg-orange-50 text-orange-600"
            }`}
          >
            Alerte stock
          </button>
          <button
            onClick={() => setStockFilter(stockFilter === "out" ? "all" : "out")}
            className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium ${
              stockFilter === "out" ? "bg-red-500 text-white" : "bg-red-50 text-red-600"
            }`}
          >
            Rupture
          </button>
        </div>
      </div>

      {/* Liste */}
      <div className="px-4 py-4 space-y-3">
        {isLoading &&
          [...Array(4)].map((_, i) => (
            <div key={i} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
              <div className="skeleton h-16 w-full" />
            </div>
          ))}

        {!isLoading && data?.items?.length === 0 && (
          <div className="text-center py-16">
            <Package size={64} style={{ color: "var(--bd)" }} className="mx-auto mb-4" />
            <p style={{ color: "var(--tx-muted)" }} className="font-medium">
              Aucun produit trouvé
            </p>
            <button onClick={handleImportCSV} className="mt-4 btn-primary max-w-xs mx-auto">
              Importer un catalogue CSV
            </button>
          </div>
        )}

        {data?.items?.map((product: any) => (
          <ProductRow
            key={product.id}
            product={product}
            onEdit={(p) => setEditingProduct(p)}
            onAdjustStock={(p) => setAdjustingProduct(p)}
            onDelete={(id) => setConfirmDeleteId(id)}
          />
        ))}
      </div>

      {adjustingProduct && (
        <StockAdjustModal product={adjustingProduct} onClose={() => setAdjustingProduct(null)} />
      )}

      {editingProduct !== undefined && (
        <ProductFormModal
          product={editingProduct}
          categories={categories?.items || []}
          onClose={() => setEditingProduct(undefined)}
        />
      )}

      <ConfirmModal
        open={!!confirmDeleteId}
        title="Supprimer le produit"
        message="Cette action est irréversible. Le produit sera supprimé du catalogue."
        confirmLabel="Supprimer"
        variant="danger"
        onConfirm={() => {
          if (confirmDeleteId) deleteMutation.mutate(confirmDeleteId);
          setConfirmDeleteId(null);
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
