"use client";

import { useState, useMemo, useCallback } from "react";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft, MapPin, Minus, Plus, ScanLine, Search,
  ShoppingBag, Store, Truck,
} from "lucide-react";
import { storesApi, catalogApi } from "@/lib/api";
import { useCartStore } from "@/lib/store";
import { toast } from "sonner";

/* ────────────────────────────────────────────────────────────
   Types
───────────────────────────────────────────────────────────── */
interface Product {
  id: string;
  name: string;
  barcode?: string;
  price_xof: number;
  weight_grams?: number;
  category_id?: string;
  image_url?: string;
  stock_quantity?: number;
}
interface Category {
  id: string;
  name: string;
}

/* ────────────────────────────────────────────────────────────
   Composant produit — ligne Uber Eats
───────────────────────────────────────────────────────────── */
function ProductRow({
  product,
  qty,
  onAdd,
  onRemove,
}: {
  product: Product;
  qty: number;
  onAdd: () => void;
  onRemove: () => void;
}) {
  const outOfStock = product.stock_quantity !== undefined && product.stock_quantity <= 0;

  return (
    <div
      className="flex items-center gap-3 px-5 py-4 transition-colors"
      style={{ borderBottom: "1px solid var(--bg-layout)" }}
    >
      {/* Miniature */}
      <div className="flex-shrink-0">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            width={60}
            height={60}
            unoptimized
            className="w-[60px] h-[60px] rounded-xl object-cover"
          />
        ) : (
          <div
            className="w-[60px] h-[60px] rounded-xl flex items-center justify-center"
            style={{ background: "var(--n-100)" }}
          >
            <ShoppingBag size={22} style={{ color: "var(--n-300)" }} />
          </div>
        )}
      </div>

      {/* Infos */}
      <div className="flex-1 min-w-0">
        <p
          className="font-bold text-sm leading-tight line-clamp-2"
          style={{ color: outOfStock ? "var(--n-400)" : "#111111" }}
        >
          {product.name}
        </p>
        {product.weight_grams && (
          <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
            {product.weight_grams >= 1000
              ? `${(product.weight_grams / 1000).toFixed(1)} kg`
              : `${product.weight_grams} g`}
          </p>
        )}
        <p className="font-black text-sm mt-1" style={{ color: outOfStock ? "var(--n-400)" : "#111111" }}>
          {product.price_xof.toLocaleString("fr-FR")} FCFA
        </p>
        {outOfStock && (
          <p className="text-xs font-bold mt-0.5" style={{ color: "#EF4444" }}>
            Rupture de stock
          </p>
        )}
      </div>

      {/* Contrôle quantité / bouton + */}
      <div className="flex-shrink-0">
        {qty > 0 ? (
          <div className="flex items-center gap-2">
            <button
              onClick={onRemove}
              className="w-8 h-8 rounded-xl flex items-center justify-center transition-transform active:scale-90"
              style={{ background: "var(--n-100)", border: "1.5px solid var(--bd)" }}
            >
              <Minus size={14} style={{ color: "#111111" }} />
            </button>
            <span className="w-5 text-center font-black text-sm" style={{ color: "#111111" }}>
              {qty}
            </span>
            <button
              onClick={onAdd}
              className="w-8 h-8 rounded-xl flex items-center justify-center transition-transform active:scale-90"
              style={{
                background: "var(--p-500)",
                boxShadow: "0 3px 10px rgba(34,87,255,0.22)",
              }}
            >
              <Plus size={14} className="text-white" strokeWidth={2.5} />
            </button>
          </div>
        ) : (
          <button
            onClick={onAdd}
            disabled={outOfStock}
            className="w-9 h-9 rounded-xl flex items-center justify-center transition-transform active:scale-90 disabled:opacity-40"
            style={{
              background: outOfStock ? "var(--n-200)" : "var(--p-500)",
              boxShadow: outOfStock ? "none" : "0 4px 12px rgba(34,87,255,0.22)",
            }}
          >
            <Plus size={18} className="text-white" strokeWidth={2.5} />
          </button>
        )}
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Skeleton
───────────────────────────────────────────────────────────── */
function ProductSkeleton() {
  return (
    <div className="flex items-center gap-3 px-5 py-4" style={{ borderBottom: "1px solid var(--bg-layout)" }}>
      <div className="skeleton w-[60px] h-[60px] rounded-xl flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="skeleton h-4 w-3/4" />
        <div className="skeleton h-3 w-1/4" />
        <div className="skeleton h-4 w-1/3" />
      </div>
      <div className="skeleton w-9 h-9 rounded-xl flex-shrink-0" />
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Page principale
───────────────────────────────────────────────────────────── */
export default function StorePage() {
  const { id: storeId } = useParams<{ id: string }>();
  const router           = useRouter();
  const [selectedCat, setSelectedCat] = useState<string | null>(null);
  const [search, setSearch]           = useState("");
  const [showSearch, setShowSearch]   = useState(false);

  const { items, addItem, removeItem, updateQuantity, setStore, itemCount, total } = useCartStore();

  /* ── Données magasin ── */
  const { data: store, isLoading: storeLoading } = useQuery({
    queryKey: ["store", storeId],
    queryFn: () => storesApi.getById(storeId).then((r) => r.data),
    enabled: !!storeId,
  });

  /* ── Catégories ── */
  const { data: categoriesData } = useQuery({
    queryKey: ["categories", storeId],
    queryFn: () => catalogApi.getCategories(storeId, store?.company_id).then((r) => r.data),
    enabled: !!storeId && !!store,
  });
  const categories: Category[] = Array.isArray(categoriesData)
    ? categoriesData
    : categoriesData?.items ?? [];

  /* ── Produits ── */
  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ["products", storeId, selectedCat],
    queryFn: () =>
      catalogApi
        .getProducts(storeId, store?.company_id, {
          category_id: selectedCat || undefined,
          limit: 100,
        })
        .then((r) => r.data),
    enabled: !!storeId && !!store,
  });
  /* ── Filtrage recherche ── */
  const products = useMemo(() => {
    const allProducts: Product[] = Array.isArray(productsData)
      ? productsData
      : productsData?.items ?? [];
    if (!search.trim()) return allProducts;
    const q = search.toLowerCase();
    return allProducts.filter(
      (p) => p.name.toLowerCase().includes(q) || p.barcode?.includes(q)
    );
  }, [productsData, search]);

  /* ── Quantité dans le panier ── */
  const getQty = useCallback(
    (productId: string) => items.find((i) => i.productId === productId)?.quantity ?? 0,
    [items]
  );

  /* ── Ajouter au panier ── */
  const handleAdd = (product: Product) => {
    if (!store) return;
    setStore(storeId, store.company_id);
    addItem({
      productId: product.id,
      name:      product.name,
      price:     product.price_xof,
      quantity:  1,
      imageUrl:  product.image_url,
    });
    toast.success(`${product.name} ajouté`, { duration: 1200 });
  };

  const handleRemove = (product: Product) => {
    const qty = getQty(product.id);
    if (qty <= 1) removeItem(product.id);
    else updateQuantity(product.id, qty - 1);
  };

  const cartCount = itemCount();
  const cartTotal = total();

  const distanceLabel =
    store?.distance_km != null
      ? store.distance_km < 1
        ? `${Math.round(store.distance_km * 1000)} m`
        : `${store.distance_km.toFixed(1).replace(".", ",")} km`
      : null;

  /* ── Services badges ── */
  const services = [];
  if (store?.scan_go_enabled)       services.push({ label: "Scan & Go", icon: ScanLine, color: "var(--p-500)" });
  if (store?.click_collect_enabled) services.push({ label: "Retrait",   icon: Store, color: "#111111" });
  if (store?.delivery_enabled)      services.push({ label: "Livraison", icon: Truck, color: "#111111" });

  return (
    <div style={{ background: "var(--bg-layout)", minHeight: "100vh" }}>

      {/* ─── Header sticky ─── */}
      <header
        className="sticky top-0 z-40 flex items-center gap-3 px-5"
        style={{
          height: 56,
          background: "rgba(255,255,255,0.94)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--bd)",
        }}
      >
        <button
          onClick={() => router.back()}
          className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 transition-colors active:bg-gray-100"
          style={{ background: "var(--n-100)" }}
        >
          <ArrowLeft size={18} style={{ color: "#111111" }} />
        </button>

        <div className="flex-1 min-w-0">
          {storeLoading ? (
            <div className="skeleton h-5 w-32" />
          ) : (
            <p className="font-black text-base truncate" style={{ color: "#111111" }}>
              {store?.name}
            </p>
          )}
        </div>

        <button
          onClick={() => setShowSearch((v) => !v)}
          className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ background: showSearch ? "#111111" : "var(--n-100)" }}
        >
          <Search size={16} style={{ color: showSearch ? "white" : "var(--tx-muted)" }} />
        </button>
      </header>

      {/* ─── Barre de recherche (toggle) ─── */}
      {showSearch && (
        <div
          className="px-5 py-3"
          style={{ background: "#FFFFFF", borderBottom: "1px solid var(--bd)" }}
        >
          <div
            className="flex items-center gap-3 px-4 py-3 rounded-xl"
            style={{ background: "var(--n-50)", border: "1.5px solid var(--bd)" }}
          >
            <Search size={16} style={{ color: "var(--n-400)" }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher un produit…"
              className="flex-1 bg-transparent text-sm outline-none"
              style={{ color: "#111111" }}
              autoFocus
            />
            {search && (
              <button onClick={() => setSearch("")} className="text-sm font-bold" style={{ color: "var(--tx-muted)" }}>
                ✕
              </button>
            )}
          </div>
        </div>
      )}

      {/* ─── Hero magasin ─── */}
      {!storeLoading && store && (
        <div className="relative h-48 w-full overflow-hidden">
          {store.cover_image_url ? (
            <Image src={store.cover_image_url} alt={store.name} fill unoptimized className="object-cover" sizes="100vw" />
          ) : (
            <div
              className="h-full w-full flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, #F1F5F9 0%, #E2E8F0 100%)" }}
            >
              <ShoppingBag size={64} style={{ color: "#CBD5E1" }} />
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />

          {/* Logo */}
          {store.logo_url && (
            <Image
              src={store.logo_url}
              alt="Logo"
              width={56}
              height={56}
              unoptimized
              className="absolute top-4 right-4 w-14 h-14 rounded-2xl object-cover border-2 border-white shadow-xl"
            />
          )}

          <div className="absolute bottom-0 left-0 right-0 px-5 pb-4">
            <h1 className="text-2xl font-black text-white leading-tight">{store.name}</h1>
            <div className="flex items-center gap-3 mt-1.5 flex-wrap">
              {store.address?.city && (
                <div className="flex items-center gap-1 text-white/80 text-sm">
                  <MapPin size={12} />
                  <span>{store.address.city}</span>
                </div>
              )}
              {distanceLabel && (
                <span
                  className="text-xs font-bold text-white px-2.5 py-0.5 rounded-full"
                  style={{ background: "rgba(255,255,255,0.20)" }}
                >
                  {distanceLabel}
                </span>
              )}
            </div>
            {/* Services */}
            <div className="flex gap-2 mt-2 flex-wrap">
              {services.map(({ label, icon: Icon, color }) => (
                <div
                  key={label}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold"
                  style={{ background: "rgba(255,255,255,0.18)", color: "white" }}
                >
                  <Icon size={11} />
                  {label}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {storeLoading && <div className="skeleton h-48 w-full" />}

      {/* ─── Pills catégories — sticky sous le hero ─── */}
      {categories.length > 0 && (
        <div
          className="sticky z-30 py-3 overflow-x-auto scrollbar-hide"
          style={{
            top: 56,
            background: "rgba(255,255,255,0.96)",
            backdropFilter: "blur(12px)",
            borderBottom: "1px solid var(--bd)",
          }}
        >
          <div className="flex gap-2 px-5">
            <button
              onClick={() => setSelectedCat(null)}
              className="flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-bold transition-all active:scale-95"
              style={{
                background: selectedCat === null ? "#111111" : "var(--n-100)",
                color:      selectedCat === null ? "white"   : "var(--tx-muted)",
              }}
            >
              Tous
            </button>
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCat(cat.id)}
                className="flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-bold transition-all active:scale-95"
                style={{
                  background: selectedCat === cat.id ? "#111111" : "var(--n-100)",
                  color:      selectedCat === cat.id ? "white"   : "var(--tx-muted)",
                }}
              >
                {cat.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ─── Liste produits ─── */}
      <div style={{ background: "#FFFFFF", borderTop: "1px solid var(--bd)" }}>
        {productsLoading &&
          [...Array(6)].map((_, i) => <ProductSkeleton key={i} />)
        }

        {!productsLoading && products.length === 0 && (
          <div className="py-20 text-center">
            <ShoppingBag size={48} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
            <p className="font-bold" style={{ color: "#111111" }}>Aucun produit trouvé</p>
            {search && (
              <button
                onClick={() => setSearch("")}
                className="mt-3 text-sm font-bold"
                style={{ color: "var(--p-500)" }}
              >
                Effacer la recherche
              </button>
            )}
          </div>
        )}

        {!productsLoading && products.map((product) => (
          <ProductRow
            key={product.id}
            product={product}
            qty={getQty(product.id)}
            onAdd={() => handleAdd(product)}
            onRemove={() => handleRemove(product)}
          />
        ))}

        {/* Padding bas pour le bandeau panier */}
        {cartCount > 0 && <div className="h-24" />}
      </div>

      {/* ─── Bandeau panier flottant — Bleu officiel ─── */}
      {cartCount > 0 && (
        <div
          className="fixed bottom-0 left-0 right-0 px-5 pb-8 pt-4 z-50"
          style={{
            background: "rgba(255,255,255,0.96)",
            backdropFilter: "blur(20px)",
            borderTop: "1px solid var(--bd)",
          }}
        >
          <button
            onClick={() => router.push("/cart")}
            className="w-full py-4 rounded-2xl font-black text-white flex items-center justify-between px-5 active:scale-[0.98] transition-transform"
            style={{
              background: "var(--p-500)",
              boxShadow: "0 8px 24px rgba(34,87,255,0.30)",
            }}
          >
            <span
              className="min-w-[28px] h-7 px-2 rounded-xl flex items-center justify-center font-black text-sm"
              style={{ background: "rgba(255,255,255,0.22)" }}
            >
              {cartCount}
            </span>
            <span className="text-base">Voir mon panier</span>
            <span className="font-black">{cartTotal.toLocaleString("fr-FR")} FCFA</span>
          </button>
        </div>
      )}
    </div>
  );
}
