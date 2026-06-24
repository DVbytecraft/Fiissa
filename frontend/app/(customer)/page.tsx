"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, MapPin, Search, ShoppingBag, Sparkles, Store, Truck, Zap } from "lucide-react";
import { storesApi } from "@/lib/api";

function StoreCard({ store }: { store: any }) {
  const services = [];
  if (store.click_collect_enabled) services.push({ label: "Retrait express", color: "var(--p-500)" });
  if (store.delivery_enabled) services.push({ label: "Livraison", color: "var(--s-500)" });
  if (store.scan_go_enabled) services.push({ label: "Scan & Go", color: "#F59E0B" });

  return (
    <Link href={`/stores/${store.id}`}>
      <div
        className="overflow-hidden rounded-[28px] active:scale-[0.99] transition-transform"
        style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
      >
        <div className="relative">
          {store.cover_image_url ? (
            <img src={store.cover_image_url} alt={store.name} className="h-44 w-full object-cover" />
          ) : (
            <div className="flex h-44 w-full items-center justify-center" style={{ background: "var(--fiissa-gradient)" }}>
              <ShoppingBag className="text-white" size={48} />
            </div>
          )}

          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/55 to-transparent p-4">
            <div className="flex items-end justify-between gap-3">
              <div className="min-w-0">
                <h3 className="truncate text-xl font-black text-white">{store.name}</h3>
                {store.address?.city && (
                  <div className="mt-1 flex items-center text-white/80">
                    <MapPin size={13} className="mr-1 shrink-0" />
                    <span className="text-sm">{store.address.city}</span>
                  </div>
                )}
              </div>
              {store.logo_url && (
                <img src={store.logo_url} alt="Logo" className="h-12 w-12 rounded-2xl border border-white/30 object-cover shadow-lg" />
              )}
            </div>
          </div>
        </div>

        <div className="p-4">
          <div className="flex flex-wrap gap-2">
            {services.map(({ label, color }) => (
              <span
                key={label}
                className="rounded-full px-3 py-1 text-xs font-black uppercase tracking-[0.12em]"
                style={{ background: `${color}18`, color }}
              >
                {label}
              </span>
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
              Explorer le catalogue
            </p>
            <span className="inline-flex items-center gap-2 text-sm font-black" style={{ color: "var(--p-500)" }}>
              Ouvrir <ArrowRight size={15} />
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

function StoreSkeleton() {
  return (
    <div className="overflow-hidden rounded-[28px]" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
      <div className="skeleton h-44 w-full" />
      <div className="space-y-3 p-4">
        <div className="skeleton h-6 w-2/3" />
        <div className="skeleton h-4 w-1/3" />
        <div className="skeleton h-10 w-full" />
      </div>
    </div>
  );
}

export default function HomePage() {
  const [search, setSearch] = useState("");

  const { data: allStores, isLoading, error } = useQuery({
    queryKey: ["stores"],
    queryFn: () => storesApi.getNearby().then((r) => r.data),
  });

  const stores = useMemo(() => {
    if (!allStores) return [];
    if (!search.trim()) return allStores;
    const q = search.trim().toLowerCase();
    return allStores.filter((s: any) => s.name?.toLowerCase().includes(q) || s.address?.city?.toLowerCase().includes(q));
  }, [allStores, search]);

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <section className="px-4 pt-4">
        <div
          className="overflow-hidden rounded-[32px] p-5 text-white relative"
          style={{ background: "linear-gradient(145deg, #0D1227 0%, #1333B3 55%, #00AB72 100%)", boxShadow: "0 20px 46px rgba(13,18,39,0.16)" }}
        >
          <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-white/10" />
          <div className="absolute right-12 bottom-0 h-20 w-20 rounded-full bg-white/10" />
          <div className="relative">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/14 px-3 py-1 text-[11px] font-black uppercase tracking-[0.16em]">
              <Sparkles size={14} />
              Nouvelle generation retail
            </div>
            <h1 className="mt-4 text-3xl font-black leading-tight">
              Trouve ton commerce, paye vite, repars avec un vrai parcours clean.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-white/78">
              Retrait, livraison et Scan & Go dans une interface simple, rapide et rassurante.
            </p>
          </div>
        </div>
      </section>

      <section className="px-4 pt-4">
        <div className="flex items-center rounded-[24px] px-4 py-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}>
          <Search style={{ color: "var(--tx-muted)" }} className="mr-3 shrink-0" size={20} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un commerce ou une ville..."
            className="flex-1 bg-transparent text-base outline-none"
            style={{ color: "var(--tx-body)" }}
          />
          {search && (
            <button onClick={() => setSearch("")} style={{ color: "var(--tx-muted)" }} className="ml-2 text-lg leading-none">
              ×
            </button>
          )}
        </div>
      </section>

      <section className="px-4 pt-4">
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: Store, label: "Click & Collect", color: "var(--p-500)", bg: "rgba(34,87,255,0.1)" },
            { icon: Truck, label: "Livraison", color: "var(--s-500)", bg: "rgba(0,214,143,0.1)" },
            { icon: Zap, label: "Scan & Go", color: "#F59E0B", bg: "rgba(245,158,11,0.12)" },
          ].map(({ icon: Icon, label, color, bg }) => (
            <div key={label} className="rounded-[24px] p-4 text-center" style={{ background: bg }}>
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl bg-white/80">
                <Icon size={22} style={{ color }} />
              </div>
              <p className="mt-3 text-xs font-black uppercase leading-5 tracking-[0.12em]" style={{ color }}>
                {label}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="px-4 pb-6 pt-6">
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
              Selection
            </p>
            <h2 className="mt-1 text-xl font-black" style={{ color: "var(--tx-head)" }}>
              Commerces disponibles
            </h2>
          </div>
          <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
            {stores.length} resultat{stores.length > 1 ? "s" : ""}
          </p>
        </div>

        <div className="space-y-4">
          {isLoading && (
            <>
              <StoreSkeleton />
              <StoreSkeleton />
              <StoreSkeleton />
            </>
          )}

          {error && (
            <div className="rounded-[28px] p-5 text-center" style={{ background: "#FEF2F2", border: "1px solid #FCA5A5" }}>
              <p className="font-black" style={{ color: "#DC2626" }}>Connexion impossible</p>
              <p className="mt-2 text-sm" style={{ color: "#EF4444" }}>Verifie ta connexion internet puis recharge la page.</p>
            </div>
          )}

          {!isLoading && stores.map((store: any) => <StoreCard key={store.id} store={store} />)}

          {!isLoading && allStores?.length === 0 && (
            <div className="py-12 text-center">
              <ShoppingBag className="mx-auto mb-4" style={{ color: "var(--bd)" }} size={48} />
              <p style={{ color: "var(--tx-muted)" }}>Aucun commerce disponible pour le moment</p>
            </div>
          )}

          {!isLoading && allStores?.length > 0 && stores.length === 0 && search && (
            <div className="py-12 text-center">
              <Search className="mx-auto mb-4" style={{ color: "var(--bd)" }} size={48} />
              <p className="font-black" style={{ color: "var(--tx-head)" }}>Aucun resultat</p>
              <p className="mt-2 text-sm" style={{ color: "var(--tx-muted)" }}>Essaie un autre nom ou une autre ville.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
