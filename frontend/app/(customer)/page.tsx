"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, MapPin, Search, ShoppingBag } from "lucide-react";
import { storesApi } from "@/lib/api";

/* ── Géolocalisation inverse Nominatim ── */
function useReverseGeocode() {
  const [label, setLabel] = useState<string | null>(null);
  useEffect(() => {
    if (typeof window === "undefined" || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      async ({ coords: { latitude, longitude } }) => {
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`,
            { headers: { "Accept-Language": "fr" } }
          );
          const data = await res.json();
          const district = data.address?.suburb || data.address?.quarter || data.address?.neighbourhood;
          const city = data.address?.city || data.address?.town || data.address?.village;
          if (district && city) setLabel(`${district}, ${city}`);
          else if (city) setLabel(city);
        } catch {}
      },
      () => {}
    );
  }, []);
  return label;
}

/* ── Carte commerce — Uber Eats style ── */
function StoreCard({ store }: { store: any }) {
  const distanceLabel =
    store.distance_km != null
      ? store.distance_km < 1
        ? `${Math.round(store.distance_km * 1000)} m`
        : `${store.distance_km.toFixed(1).replace(".", ",")} km`
      : null;

  const services: string[] = [];
  if (store.scan_go_enabled)       services.push("Scan & Go");
  if (store.click_collect_enabled) services.push("Retrait");
  if (store.delivery_enabled)      services.push("Livraison");

  return (
    <Link href={`/stores/${store.id}`}>
      <div
        className="overflow-hidden rounded-3xl active:scale-[0.985] transition-all duration-150"
        style={{
          background: "#FFFFFF",
          border: "1px solid var(--bd)",
          boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
        }}
      >
        {/* Hero image */}
        <div className="relative h-44 w-full overflow-hidden">
          {store.cover_image_url ? (
            <img src={store.cover_image_url} alt={store.name} className="h-full w-full object-cover" />
          ) : (
            <div
              className="h-full w-full flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, #F1F5F9 0%, #E2E8F0 100%)" }}
            >
              <ShoppingBag size={48} style={{ color: "#CBD5E1" }} />
            </div>
          )}
          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent" />

          {/* Logo */}
          {store.logo_url && (
            <img
              src={store.logo_url}
              alt="Logo"
              className="absolute top-3 right-3 w-12 h-12 rounded-2xl object-cover border-2 border-white shadow-lg"
            />
          )}

          {/* Distance badge */}
          {distanceLabel && (
            <div
              className="absolute top-3 left-3 rounded-full px-2.5 py-1 text-xs font-bold text-white"
              style={{ background: "rgba(0,0,0,0.48)", backdropFilter: "blur(8px)" }}
            >
              📍 {distanceLabel}
            </div>
          )}

          {/* Store name overlay */}
          <div className="absolute bottom-0 left-0 right-0 px-4 pb-3">
            <h3 className="text-white font-black text-xl leading-tight truncate">{store.name}</h3>
            {store.address?.city && (
              <p className="text-white/70 text-sm mt-0.5">{store.address.city}</p>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex gap-1.5 flex-wrap">
            {services.map((s) => (
              <span
                key={s}
                className="text-[11px] font-bold px-2.5 py-0.5 rounded-full"
                style={{
                  background: s === "Scan & Go" ? "rgba(255,159,0,0.12)" : "var(--n-100)",
                  color:      s === "Scan & Go" ? "var(--color-action)"  : "var(--tx-muted)",
                }}
              >
                {s}
              </span>
            ))}
          </div>
          <div className="flex items-center gap-1 text-sm font-bold" style={{ color: "var(--tx-muted)" }}>
            Voir <ArrowRight size={14} />
          </div>
        </div>
      </div>
    </Link>
  );
}

function StoreSkeleton() {
  return (
    <div className="overflow-hidden rounded-3xl" style={{ border: "1px solid var(--bd)" }}>
      <div className="skeleton h-44 w-full" />
      <div className="px-4 py-3 flex justify-between items-center">
        <div className="flex gap-2">
          <div className="skeleton h-5 w-16 rounded-full" />
          <div className="skeleton h-5 w-14 rounded-full" />
        </div>
        <div className="skeleton h-4 w-10" />
      </div>
    </div>
  );
}

/* ── Page principale ── */
export default function HomePage() {
  const [search, setSearch] = useState("");
  const locationLabel = useReverseGeocode();

  const { data: allStores, isLoading, error } = useQuery({
    queryKey: ["stores"],
    queryFn: () => storesApi.getNearby().then((r) => r.data),
  });

  const stores = useMemo(() => {
    if (!allStores) return [];
    if (!search.trim()) return allStores;
    const q = search.trim().toLowerCase();
    return allStores.filter(
      (s: any) =>
        s.name?.toLowerCase().includes(q) ||
        s.address?.city?.toLowerCase().includes(q)
    );
  }, [allStores, search]);

  return (
    <div style={{ background: "#FFFFFF", minHeight: "100vh" }}>

      {/* ── Salutation ── */}
      <section className="px-5 pt-7 pb-1">
        {locationLabel ? (
          <div className="flex items-center gap-1.5 mb-3">
            <MapPin size={12} style={{ color: "var(--tx-muted)" }} />
            <span className="text-sm font-medium" style={{ color: "var(--tx-muted)" }}>
              {locationLabel}
            </span>
          </div>
        ) : (
          <div className="mb-3 h-5" />
        )}

        <h1 className="text-[28px] font-black leading-tight tracking-tight" style={{ color: "#111111" }}>
          Bonjour 👋
        </h1>
        <p className="text-base mt-1 font-medium" style={{ color: "var(--tx-muted)" }}>
          Que voulez-vous faire aujourd'hui ?
        </p>
      </section>

      {/* ── Barre de recherche ── */}
      <section className="px-5 pt-5">
        <div
          className="flex items-center gap-3 px-4 py-3.5 rounded-2xl"
          style={{
            background: "var(--n-50)",
            border: "1.5px solid var(--bd)",
          }}
        >
          <Search size={18} style={{ color: "var(--n-400)" }} className="flex-shrink-0" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un commerce, une ville…"
            className="flex-1 bg-transparent text-base outline-none"
            style={{ color: "#111111" }}
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-black flex-shrink-0"
              style={{ background: "var(--n-300)", color: "white" }}
            >
              ×
            </button>
          )}
        </div>
      </section>

      {/* ── Séparateur ── */}
      <div className="mx-5 mt-6" style={{ height: 1, background: "var(--bd)" }} />

      {/* ── Liste des commerces ── */}
      <section className="px-5 pt-5 pb-8">
        <div className="flex items-end justify-between mb-4">
          <div>
            <p className="section-label">À proximité</p>
            <h2 className="text-xl font-black mt-0.5" style={{ color: "#111111" }}>
              Commerces disponibles
            </h2>
          </div>
          {!isLoading && allStores && (
            <span className="text-sm" style={{ color: "var(--tx-muted)" }}>
              {stores.length} résultat{stores.length > 1 ? "s" : ""}
            </span>
          )}
        </div>

        <div className="space-y-4">
          {isLoading && <><StoreSkeleton /><StoreSkeleton /><StoreSkeleton /></>}

          {error && (
            <div className="rounded-2xl p-5 text-center" style={{ background: "#FEF2F2", border: "1px solid #FCA5A5" }}>
              <p className="font-black" style={{ color: "#DC2626" }}>Connexion impossible</p>
              <p className="mt-1 text-sm" style={{ color: "#EF4444" }}>Vérifie ta connexion puis recharge.</p>
            </div>
          )}

          {!isLoading && stores.map((store: any) => <StoreCard key={store.id} store={store} />)}

          {!isLoading && allStores?.length === 0 && (
            <div className="py-16 text-center">
              <ShoppingBag size={48} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
              <p className="font-bold" style={{ color: "#111111" }}>Aucun commerce disponible</p>
              <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>Reviens bientôt !</p>
            </div>
          )}

          {!isLoading && allStores?.length > 0 && stores.length === 0 && search && (
            <div className="py-16 text-center">
              <Search size={48} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
              <p className="font-black" style={{ color: "#111111" }}>Aucun résultat</p>
              <p className="mt-1 text-sm" style={{ color: "var(--tx-muted)" }}>
                Essaie un autre nom ou une autre ville.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
