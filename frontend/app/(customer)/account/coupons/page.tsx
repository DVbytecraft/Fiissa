"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Clock, QrCode, Tag, TicketX } from "lucide-react";
import { loyaltyApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import QRCode from "qrcode";

type CouponTab = "available" | "used" | "expired";

function CouponQrModal({ code, onClose }: { code: string; onClose: () => void }) {
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);

  useState(() => {
    QRCode.toDataURL(code, { width: 200, margin: 1, color: { dark: "#0F172A", light: "#FFFFFF" } })
      .then(setQrDataUrl)
      .catch(() => {});
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-6" onClick={onClose}>
      <div
        className="w-full max-w-xs rounded-3xl p-6 flex flex-col items-center"
        style={{ background: "var(--bg-card)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3" style={{ background: "rgba(34,87,255,0.08)" }}>
          <QrCode size={20} style={{ color: "var(--p-500)" }} />
        </div>
        <p className="font-bold text-base mb-1" style={{ color: "var(--tx-head)" }}>Code coupon</p>
        <p className="font-mono text-xl font-black mb-4 tracking-widest" style={{ color: "var(--p-500)" }}>{code}</p>
        {qrDataUrl ? (
          <img src={qrDataUrl} alt="QR coupon" className="w-44 h-44 rounded-2xl" style={{ border: "4px solid white", boxShadow: "0 2px 12px rgba(0,0,0,0.15)" }} />
        ) : (
          <div className="w-44 h-44 rounded-2xl skeleton" />
        )}
        <p className="text-xs mt-4 text-center" style={{ color: "var(--tx-muted)" }}>
          Présentez ce code ou QR à la caisse
        </p>
        <button onClick={onClose} className="mt-5 w-full py-3 rounded-2xl font-bold text-sm" style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}>
          Fermer
        </button>
      </div>
    </div>
  );
}

export default function CouponsPage() {
  const [tab, setTab] = useState<CouponTab>("available");
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const { user } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ["my-coupons", user?.id],
    queryFn: () => loyaltyApi.getMyCoupons(user!.id).then((r) => r.data),
    enabled: !!user?.id,
  });

  const now = new Date();
  const coupons: any[] = data ?? [];

  const available = coupons.filter(
    (c) => !c.is_used && (!c.expires_at || new Date(c.expires_at) > now)
  );
  const used = coupons.filter((c) => c.is_used);
  const expired = coupons.filter(
    (c) => !c.is_used && c.expires_at && new Date(c.expires_at) <= now
  );

  const shown = tab === "available" ? available : tab === "used" ? used : expired;

  const TABS: { key: CouponTab; label: string; count: number }[] = [
    { key: "available", label: "Disponibles", count: available.length },
    { key: "used", label: "Utilisés", count: used.length },
    { key: "expired", label: "Expirés", count: expired.length },
  ];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div className="px-5 pt-4 pb-4 flex items-center gap-3" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <Link href="/account" style={{ color: "var(--tx-muted)" }}>
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>Mes coupons</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
            {available.length} disponible{available.length > 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Onglets */}
      <div className="flex px-4 pt-4 gap-2">
        {TABS.map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className="flex-1 py-2 rounded-xl text-xs font-bold transition-colors"
            style={
              tab === key
                ? { background: "var(--p-500)", color: "#fff" }
                : { background: "var(--bg-card)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }
            }
          >
            {label} {count > 0 && `(${count})`}
          </button>
        ))}
      </div>

      <div className="px-4 py-4 space-y-3">
        {isLoading && [...Array(3)].map((_, i) => (
          <div key={i} className="skeleton h-28 w-full rounded-2xl" />
        ))}

        {!isLoading && shown.length === 0 && (
          <div className="text-center py-16">
            <TicketX size={56} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>
              Aucun coupon {tab === "available" ? "disponible" : tab === "used" ? "utilisé" : "expiré"}
            </p>
            {tab === "available" && (
              <p className="text-xs mt-2" style={{ color: "var(--tx-muted)" }}>
                Les coupons sont émis par les marchands lors de vos achats ou récompenses.
              </p>
            )}
          </div>
        )}

        {shown.map((coupon: any) => {
          const isExpiredItem = !coupon.is_used && coupon.expires_at && new Date(coupon.expires_at) <= now;
          const expiresAt = coupon.expires_at
            ? new Date(coupon.expires_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" })
            : null;

          const discountText =
            coupon.discount_type === "pct"
              ? `−${coupon.discount_value}%`
              : `−${coupon.discount_value.toLocaleString("fr-FR")} F`;

          return (
            <div
              key={coupon.id}
              className="rounded-2xl overflow-hidden"
              style={{
                background: "var(--bg-card)",
                border: `1px solid ${coupon.is_used ? "var(--bd)" : isExpiredItem ? "var(--bd)" : "rgba(34,87,255,0.2)"}`,
                opacity: coupon.is_used || isExpiredItem ? 0.65 : 1,
              }}
            >
              {/* Bande colorée gauche */}
              <div className="flex">
                <div
                  className="w-2 flex-shrink-0"
                  style={{
                    background: coupon.is_used
                      ? "var(--bd)"
                      : isExpiredItem
                      ? "#9CA3AF"
                      : "var(--p-500)",
                  }}
                />
                <div className="flex-1 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Tag size={14} style={{ color: "var(--p-500)" }} />
                        <p className="font-black text-xl" style={{ color: coupon.is_used ? "var(--tx-muted)" : "var(--p-500)" }}>
                          {discountText}
                        </p>
                      </div>
                      <p className="font-mono text-xs font-bold tracking-widest" style={{ color: "var(--tx-head)" }}>
                        {coupon.code}
                      </p>
                      {coupon.min_order_xof > 0 && (
                        <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                          Achat min. {coupon.min_order_xof.toLocaleString("fr-FR")} F
                        </p>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      {coupon.is_used ? (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(110,122,138,0.1)", color: "var(--tx-muted)" }}>
                          Utilisé
                        </span>
                      ) : isExpiredItem ? (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(220,38,38,0.08)", color: "#DC2626" }}>
                          Expiré
                        </span>
                      ) : (
                        <button
                          onClick={() => setSelectedCode(coupon.code)}
                          className="px-3 py-1.5 rounded-xl text-xs font-bold text-white"
                          style={{ background: "var(--p-500)" }}
                        >
                          Afficher
                        </button>
                      )}
                    </div>
                  </div>

                  {expiresAt && (
                    <div className="flex items-center gap-1 mt-2" style={{ color: "var(--tx-muted)" }}>
                      <Clock size={11} />
                      <p className="text-[10px]">
                        {coupon.is_used
                          ? `Utilisé le ${new Date(coupon.used_at).toLocaleDateString("fr-FR")}`
                          : isExpiredItem
                          ? `Expiré le ${expiresAt}`
                          : `Expire le ${expiresAt}`}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {selectedCode && (
        <CouponQrModal code={selectedCode} onClose={() => setSelectedCode(null)} />
      )}
    </div>
  );
}
