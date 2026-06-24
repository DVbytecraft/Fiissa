"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { receiptsApi } from "@/lib/api";

export default function PublicReceiptVerifyPage() {
  const { code } = useParams<{ code: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["verify-receipt", code],
    queryFn: () => receiptsApi.verify(code).then((r) => r.data),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center">
        <div className="w-12 h-12 border-4 border-white/30 border-t-white rounded-full animate-spin mb-4" />
        <p className="text-white/70 text-lg">Vérification en cours...</p>
      </div>
    );
  }

  const valid = !isError && data?.valid;
  const alreadyUsed = data?.already_verified;

  const bg = valid ? (alreadyUsed ? "bg-orange-500" : "bg-green-500") : "bg-red-500";
  const Icon = valid ? (alreadyUsed ? AlertCircle : CheckCircle) : XCircle;
  const title = valid
    ? alreadyUsed
      ? "Reçu déjà vérifié"
      : "Reçu valide"
    : "Reçu invalide";

  return (
    <div className={`min-h-screen ${bg} flex flex-col items-center justify-center px-6 text-white`}>
      <Icon size={96} className="mb-6" />
      <h1 className="text-4xl font-black text-center mb-2">{title}</h1>

      {data && (
        <div className="bg-white/20 rounded-2xl p-4 w-full max-w-sm mt-6 space-y-2">
          {data.receipt_number && (
            <div className="flex justify-between">
              <span className="text-white/70 text-sm">N° Reçu</span>
              <span className="font-bold text-sm">{data.receipt_number}</span>
            </div>
          )}
          {data.store_name && (
            <div className="flex justify-between">
              <span className="text-white/70 text-sm">Boutique</span>
              <span className="font-bold text-sm">{data.store_name}</span>
            </div>
          )}
          {data.total_xof != null && (
            <div className="flex justify-between">
              <span className="text-white/70 text-sm">Montant</span>
              <span className="font-bold text-sm">{data.total_xof?.toLocaleString("fr-FR")} FCFA</span>
            </div>
          )}
          {data.items_count != null && (
            <div className="flex justify-between">
              <span className="text-white/70 text-sm">Articles</span>
              <span className="font-bold text-sm">{data.items_count}</span>
            </div>
          )}
          {data.issued_at && (
            <div className="flex justify-between">
              <span className="text-white/70 text-sm">Émis le</span>
              <span className="font-bold text-sm">
                {new Date(data.issued_at).toLocaleDateString("fr-FR", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>
          )}
          {data.message && (
            <p className="text-white/80 text-sm mt-2 text-center pt-2 border-t border-white/20">
              {data.message}
            </p>
          )}
        </div>
      )}

      {isError && (
        <p className="text-white/80 text-center mt-4 max-w-xs">
          Ce reçu n'existe pas ou le code QR est invalide.
        </p>
      )}

      <p className="text-white/40 text-xs mt-8">SmartCheckout — Vérification de reçu</p>
    </div>
  );
}
