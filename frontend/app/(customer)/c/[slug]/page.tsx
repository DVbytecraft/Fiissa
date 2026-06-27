"use client";

import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft, Phone, Globe, MapPin, Clock, Star,
  ChevronRight, Store, Pill, ShoppingCart, UtensilsCrossed,
} from "lucide-react";
import { companiesApi } from "@/lib/api";
import Link from "next/link";

const TYPE_LABELS: Record<string, string> = {
  boutique: "Boutique",
  supermarket: "Supermarché",
  restaurant: "Restaurant",
  proximity: "Commerce de proximité",
  pharmacy: "Pharmacie",
  other: "Commerce",
};

const TYPE_ICONS: Record<string, React.ElementType> = {
  pharmacy: Pill,
  supermarket: ShoppingCart,
  restaurant: UtensilsCrossed,
};

const DAY_LABELS: Record<string, string> = {
  mon: "Lundi", tue: "Mardi", wed: "Mercredi", thu: "Jeudi",
  fri: "Vendredi", sat: "Samedi", sun: "Dimanche",
};
const DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

function isOpenNow(openingHours: Record<string, any> | null): boolean {
  if (!openingHours) return false;
  const now = new Date();
  const dayKey = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"][now.getDay()];
  const today = openingHours[dayKey];
  if (!today || today.closed) return false;
  const [oh, om] = (today.open || "").split(":").map(Number);
  const [ch, cm] = (today.close || "").split(":").map(Number);
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  return nowMinutes >= oh * 60 + om && nowMinutes < ch * 60 + cm;
}

export default function CompanyProfilePage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["company-profile", slug],
    queryFn: () => companiesApi.getPublicProfile(slug),
    enabled: !!slug,
  });

  const company = data?.data;

  if (isLoading) {
    return (
      <div className="flex flex-col min-h-screen" style={{ background: "var(--bg-app)" }}>
        <div className="px-5 pt-12 pb-5 flex items-center gap-3" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
          <button onClick={() => router.back()} style={{ color: "var(--tx-muted)" }}>
            <ArrowLeft size={22} />
          </button>
          <div className="h-6 w-40 rounded-xl animate-pulse" style={{ background: "var(--bd)" }} />
        </div>
        <div className="px-5 py-6 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-2xl h-20 animate-pulse" style={{ background: "var(--bg-card)" }} />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !company) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4" style={{ background: "var(--bg-app)" }}>
        <Store size={48} style={{ color: "var(--tx-muted)", opacity: 0.4 }} />
        <p className="text-lg font-semibold" style={{ color: "var(--tx-head)" }}>Enseigne introuvable</p>
        <button onClick={() => router.back()} className="text-sm font-semibold" style={{ color: "var(--p-500)" }}>
          Retour
        </button>
      </div>
    );
  }

  const Icon = TYPE_ICONS[company.type] || Store;
  const openNow = isOpenNow(company.opening_hours);
  const openingHours: Record<string, any> = company.opening_hours || {};

  return (
    <div className="flex flex-col min-h-screen" style={{ background: "var(--bg-app)" }}>

      {/* Header */}
      <div
        className="px-5 pt-12 pb-0"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <div className="flex items-center gap-3 mb-5">
          <button onClick={() => router.back()} style={{ color: "var(--tx-muted)" }}>
            <ArrowLeft size={22} />
          </button>
        </div>

        {/* Logo + nom */}
        <div className="flex items-center gap-4 pb-6">
          <div
            className="w-20 h-20 rounded-2xl flex items-center justify-center shrink-0 overflow-hidden"
            style={{ background: "var(--bg-app)", border: "2px solid var(--bd)" }}
          >
            {company.logo_url ? (
              <Image src={company.logo_url} alt={company.name} fill unoptimized className="object-cover" sizes="80px" />
            ) : (
              <Icon size={32} style={{ color: "var(--tx-muted)" }} />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold leading-tight" style={{ color: "var(--tx-head)" }}>
              {company.name}
            </h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
              {TYPE_LABELS[company.type] || "Commerce"}
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span
                className="text-[11px] font-semibold px-2.5 py-1 rounded-full"
                style={{
                  background: openNow ? "rgba(0,200,100,0.1)" : "rgba(150,150,150,0.1)",
                  color: openNow ? "#00C864" : "var(--tx-muted)",
                }}
              >
                {openNow ? "Ouvert maintenant" : "Fermé"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 px-5 py-6 space-y-4">

        {/* Description */}
        {company.description && (
          <div
            className="rounded-2xl p-4"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <p className="text-sm leading-6" style={{ color: "var(--tx-body)" }}>
              {company.description}
            </p>
          </div>
        )}

        {/* Programme fidélité */}
        {company.loyalty?.enabled && (
          <div
            className="rounded-2xl p-4 flex items-center gap-4"
            style={{ background: "rgba(255,159,0,0.06)", border: "1px solid rgba(255,159,0,0.2)" }}
          >
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "rgba(255,159,0,0.12)" }}
            >
              <Star size={18} style={{ color: "#FF9F00" }} />
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: "#92400E" }}>
                {company.loyalty.program_name || "Programme fidélité"}
              </p>
              <p className="text-xs mt-0.5" style={{ color: "#B45309" }}>
                {company.loyalty.points_per_xof
                  ? `${company.loyalty.points_per_xof} pt / XOF dépensé`
                  : company.loyalty.description || "Gagnez des points à chaque achat"}
              </p>
            </div>
          </div>
        )}

        {/* Contact */}
        <div
          className="rounded-2xl divide-y"
          style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", "--divider": "var(--bd)" } as any}
        >
          {company.contact_phone && (
            <a
              href={`tel:${company.contact_phone}`}
              className="flex items-center gap-4 p-4"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "rgba(34,87,255,0.07)" }}
              >
                <Phone size={18} style={{ color: "var(--p-500)" }} />
              </div>
              <div className="flex-1">
                <p className="text-xs font-medium" style={{ color: "var(--tx-muted)" }}>Téléphone</p>
                <p className="text-sm font-semibold mt-0.5" style={{ color: "var(--tx-head)" }}>
                  {company.contact_phone}
                </p>
              </div>
              <ChevronRight size={18} style={{ color: "var(--tx-muted)" }} />
            </a>
          )}

          {company.website_url && (
            <a
              href={company.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-4 p-4"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "rgba(34,87,255,0.07)" }}
              >
                <Globe size={18} style={{ color: "var(--p-500)" }} />
              </div>
              <div className="flex-1">
                <p className="text-xs font-medium" style={{ color: "var(--tx-muted)" }}>Site web</p>
                <p className="text-sm font-semibold mt-0.5 truncate" style={{ color: "var(--p-500)" }}>
                  {company.website_url.replace(/^https?:\/\//, "")}
                </p>
              </div>
              <ChevronRight size={18} style={{ color: "var(--tx-muted)" }} />
            </a>
          )}

          {company.address?.city && (
            <div className="flex items-center gap-4 p-4">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "rgba(34,87,255,0.07)" }}
              >
                <MapPin size={18} style={{ color: "var(--p-500)" }} />
              </div>
              <div className="flex-1">
                <p className="text-xs font-medium" style={{ color: "var(--tx-muted)" }}>Adresse</p>
                <p className="text-sm font-semibold mt-0.5" style={{ color: "var(--tx-head)" }}>
                  {[company.address.street, company.address.city].filter(Boolean).join(", ")}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Horaires */}
        {Object.keys(openingHours).length > 0 && (
          <div
            className="rounded-2xl p-4"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Clock size={16} style={{ color: "var(--tx-muted)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--tx-head)" }}>Horaires d'ouverture</p>
            </div>
            <div className="space-y-2">
              {DAY_ORDER.filter((d) => openingHours[d] !== undefined).map((dayKey) => {
                const slot = openingHours[dayKey];
                const now = new Date();
                const todayKey = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"][now.getDay()];
                const isToday = dayKey === todayKey;
                return (
                  <div key={dayKey} className="flex items-center justify-between">
                    <span
                      className="text-sm"
                      style={{
                        color: isToday ? "var(--p-500)" : "var(--tx-body)",
                        fontWeight: isToday ? 700 : 400,
                      }}
                    >
                      {DAY_LABELS[dayKey]}
                    </span>
                    <span
                      className="text-sm"
                      style={{
                        color: slot?.closed ? "var(--tx-muted)" : (isToday ? "var(--p-500)" : "var(--tx-body)"),
                        fontWeight: isToday ? 700 : 400,
                      }}
                    >
                      {slot?.closed ? "Fermé" : `${slot?.open || "?"} – ${slot?.close || "?"}`}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
