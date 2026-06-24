"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ShoppingCart, Plus, Minus, Search } from "lucide-react";
import { storesApi, catalogApi } from "@/lib/api";
import { useCartStore } from "@/lib/store";
import { useDebounce } from "@/lib/hooks";
import { toast } from "sonner";

function FormatXOF({ amount }: { amount: number }) {
  return <span>{amount.toLocaleString("fr-FR")} FCFA</span>;
}

function ProductCard({ product }: { product: any }) {
  const { addItem, items, updateQuantity } = useCartStore();
  const cartItem = items.find((i) => i.productId === product.id);
  const qty = cartItem?.quantity || 0;

  const handleAdd = () => {
    if (!product.is_available) return;
    if (product.stock_available !== null && product.stock_available !== undefined && product.stock_available <= qty) {
      toast.error("Stock insuffisant");
      return;
    }
    addItem({
      productId: product.id,
      name: product.name,
      price: product.price_xof,
      quantity: 1,
      imageUrl: product.image_url,
    });
    toast.success(`${product.name} ajouté`);
  };

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
      {product.image_url ? (
        <img src={product.image_url} alt={product.name} className="w-full h-36 object-cover" />
      ) : (
        <div className="w-full h-36 flex items-center justify-center" style={{ background: "var(--bg-app)" }}>
          <span className="text-4xl">🛒</span>
        </div>
      )}
      <div className="p-3">
        <h3 className="font-semibold text-sm leading-tight" style={{ color: "var(--tx-head)" }}>{product.name}</h3>
        {product.compare_price_xof && (
          <p className="line-through text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
            <FormatXOF amount={product.compare_price_xof} />
          </p>
        )}
        <p className="font-bold mt-1" style={{ color: "var(--p-500)" }}>
          <FormatXOF amount={product.price_xof} />
        </p>

        {qty === 0 ? (
          <button
            onClick={handleAdd}
            disabled={!product.is_available}
            className="mt-2 w-full py-2 text-white rounded-xl font-semibold text-sm active:scale-95 transition-transform"
            style={product.is_available ? { background: "var(--p-500)" } : { background: "var(--bd)", color: "var(--tx-muted)" }}
          >
            {product.is_available ? "Ajouter" : "Indisponible"}
          </button>
        ) : (
          <div className="mt-2 flex items-center justify-between rounded-xl p-1" style={{ background: "rgba(34,87,255,0.07)" }}>
            <button
              onClick={() => updateQuantity(product.id, qty - 1)}
              className="w-8 h-8 rounded-lg flex items-center justify-center active:scale-90"
              style={{ background: "var(--bg-card)" }}
            >
              <Minus size={14} style={{ color: "var(--p-500)" }} />
            </button>
            <span className="font-bold text-base" style={{ color: "var(--p-500)" }}>{qty}</span>
            <button
              onClick={handleAdd}
              className="w-8 h-8 rounded-lg flex items-center justify-center active:scale-90"
              style={{ background: "var(--p-500)" }}
            >
              <Plus size={14} className="text-white" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function StorePage() {
  const params = useParams();
  const router = useRouter();
  const storeId = params.storeId as string;
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 350);
  const { itemCount, total, setStore } = useCartStore();

  const { data: store } = useQuery({
    queryKey: ["store", storeId],
    queryFn: () => storesApi.getById(storeId).then((r) => r.data),
  });

  const companyId = store?.company_id;

  const { data: categories } = useQuery({
    queryKey: ["categories", storeId, companyId],
    queryFn: () => catalogApi.getCategories(storeId, companyId).then((r) => r.data),
    enabled: !!companyId,
  });

  const { data: productsData, isLoading } = useQuery({
    queryKey: ["products", storeId, companyId, selectedCategory, debouncedSearch],
    queryFn: () =>
      catalogApi.getProducts(storeId, companyId, {
        category_id: selectedCategory || undefined,
        search: debouncedSearch || undefined,
      }).then((r) => r.data),
    enabled: !!companyId,
  });

  const handleEnterStore = () => {
    if (companyId) setStore(storeId, companyId);
  };

  if (!store) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="spinner" style={{ borderColor: `var(--p-500) transparent transparent transparent` }} />
      </div>
    );
  }

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header image cover */}
      <div className="relative">
        <div className="w-full h-52" style={{ background: "var(--fiissa-gradient)" }}>
          {store.cover_image_url && (
            <img src={store.cover_image_url} alt={store.name} className="w-full h-full object-cover" />
          )}
          <div className="absolute inset-0" style={{ background: "rgba(0,0,0,0.25)" }} />
        </div>
        <button
          onClick={() => router.back()}
          className="absolute top-4 left-4 w-10 h-10 rounded-full flex items-center justify-center shadow"
          style={{ background: "rgba(255,255,255,0.92)" }}
        >
          <ArrowLeft size={20} style={{ color: "var(--tx-head)" }} />
        </button>
        <div className="absolute bottom-4 left-4 right-4">
          <h1 className="text-white text-2xl font-bold">{store.name}</h1>
          {store.address?.city && <p className="text-white/80 text-sm">📍 {store.address.city}</p>}
        </div>
      </div>

      {/* Services badges */}
      <div className="px-4 py-3" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="flex gap-2 flex-wrap">
          {store.services?.click_collect && (
            <span className="text-xs px-3 py-1 rounded-full font-semibold" style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}>
              Retrait gratuit
            </span>
          )}
          {store.services?.delivery && (
            <span className="text-xs px-3 py-1 rounded-full font-semibold" style={{ background: "rgba(0,214,143,0.08)", color: "var(--s-500)" }}>
              Livraison {store.delivery_fee_xof > 0 ? `${store.delivery_fee_xof.toLocaleString()} FCFA` : "gratuite"}
            </span>
          )}
          {store.services?.scan_go && (
            <span className="text-xs px-3 py-1 rounded-full font-semibold" style={{ background: "rgba(245,158,11,0.08)", color: "#F59E0B" }}>
              Scan & Go
            </span>
          )}
        </div>
      </div>

      {/* Barre de recherche */}
      <div className="px-4 py-3" style={{ background: "var(--bg-card)" }}>
        <div className="flex items-center rounded-xl px-3 py-2" style={{ background: "var(--bg-app)" }}>
          <Search size={16} className="mr-2 shrink-0" style={{ color: "var(--tx-muted)" }} />
          <input
            type="text"
            placeholder="Rechercher un produit..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 bg-transparent outline-none text-sm"
            style={{ color: "var(--tx-body)" }}
          />
        </div>
      </div>

      {/* Catégories */}
      {categories && categories.length > 0 && (
        <div className="px-4 py-2 flex gap-2 overflow-x-auto scrollbar-hide" style={{ background: "var(--bg-card)" }}>
          <button
            onClick={() => setSelectedCategory(null)}
            className="shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-colors"
            style={!selectedCategory
              ? { background: "var(--p-500)", color: "#fff" }
              : { background: "var(--bg-app)", color: "var(--tx-muted)" }
            }
          >
            Tout
          </button>
          {categories.map((cat: any) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className="shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-colors"
              style={selectedCategory === cat.id
                ? { background: "var(--p-500)", color: "#fff" }
                : { background: "var(--bg-app)", color: "var(--tx-muted)" }
              }
            >
              {cat.name}
            </button>
          ))}
        </div>
      )}

      {/* Grille produits */}
      <div className="px-4 pb-32 mt-3" onClick={handleEnterStore}>
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)" }}>
                <div className="skeleton h-36 w-full" />
                <div className="p-3 space-y-2">
                  <div className="skeleton h-4 w-3/4" />
                  <div className="skeleton h-5 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {productsData?.items?.map((product: any) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
        {productsData?.items?.length === 0 && !isLoading && (
          <div className="text-center py-12">
            <p style={{ color: "var(--tx-muted)" }}>Aucun produit trouvé</p>
          </div>
        )}
      </div>

      {/* Bouton panier flottant */}
      {itemCount() > 0 && (
        <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto px-4 pb-20">
          <Link href="/cart">
            <button
              className="w-full py-4 text-white rounded-2xl font-bold text-base shadow-lg flex items-center justify-between px-5 active:scale-95 transition-transform"
              style={{ background: "var(--p-500)", boxShadow: "var(--sh-brand)" }}
            >
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ background: "rgba(255,255,255,0.2)" }}>
                  <span className="text-sm font-bold">{itemCount()}</span>
                </div>
                <span>Voir le panier</span>
              </div>
              <span>{total().toLocaleString("fr-FR")} FCFA</span>
            </button>
          </Link>
        </div>
      )}
    </div>
  );
}
