"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

interface LoyaltyCardProps {
  customerName: string;
  companyName: string;
  points: number;
  cardNumber: string;
  tierName?: string | null;
  backgroundColor?: string;
  textColor?: string;
  logoUrl?: string | null;
  isActive?: boolean;
  className?: string;
}

export default function LoyaltyCard({
  customerName,
  companyName,
  points,
  cardNumber,
  tierName,
  backgroundColor = "#1A1A2E",
  textColor = "#FFFFFF",
  logoUrl,
  isActive = true,
  className = "",
}: LoyaltyCardProps) {
  const [formattedNumber, setFormattedNumber] = useState("");

  useEffect(() => {
    // Formater le numéro de carte par groupes de 4
    const cleaned = cardNumber.replace(/\s/g, "").replace(/-/g, "");
    const groups = cleaned.match(/.{1,4}/g) || [];
    setFormattedNumber(groups.join(" "));
  }, [cardNumber]);

  return (
    <div
      className={`relative w-full rounded-2xl p-6 shadow-xl overflow-hidden transition-transform hover:scale-[1.02] ${className}`}
      style={{
        background: backgroundColor.startsWith("#")
          ? `linear-gradient(135deg, ${backgroundColor} 0%, ${backgroundColor}DD 100%)`
          : backgroundColor,
        color: textColor,
        minHeight: "200px",
        opacity: isActive ? 1 : 0.6,
      }}
    >
      {/* Effet décoratif */}
      <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-10" style={{ background: textColor }} />
      <div className="absolute bottom-0 left-0 w-24 h-24 rounded-full opacity-5" style={{ background: textColor }} />

      {/* En-tête */}
      <div className="flex justify-between items-start mb-8 relative z-10">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider opacity-80">
            {companyName}
          </p>
          {tierName && (
            <p className="text-xs font-bold uppercase tracking-wider mt-1 opacity-90">
              {tierName}
            </p>
          )}
        </div>
        {logoUrl ? (
          <Image src={logoUrl} alt="Logo" width={96} height={32} unoptimized className="h-8 w-auto object-contain" />
        ) : (
          <div className="h-8 w-8 rounded-lg" style={{ background: textColor, opacity: 0.2 }} />
        )}
      </div>

      {/* Numéro de carte */}
      <div className="mb-6 relative z-10">
        <p className="text-lg font-mono tracking-wider">
          {formattedNumber || "•••• •••• •••• ••••"}
        </p>
      </div>

      {/* Points et nom */}
      <div className="flex justify-between items-end relative z-10">
        <div>
          <p className="text-xs uppercase tracking-wider opacity-70">Points</p>
          <p className="text-3xl font-black">
            {points.toLocaleString("fr-FR")}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wider opacity-70">Porteur</p>
          <p className="text-sm font-bold">{customerName}</p>
        </div>
      </div>

      {!isActive && (
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-20">
          <span className="text-sm font-bold uppercase tracking-widest px-3 py-1 rounded" style={{ background: textColor, color: backgroundColor }}>
            Inactive
          </span>
        </div>
      )}
    </div>
  );
}
