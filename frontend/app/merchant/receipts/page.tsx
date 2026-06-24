"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Receipt, Search, Download, ExternalLink, QrCode } from "lucide-react";
import { receiptsApi } from "@/lib/api";
import Link from "next/link";
import { toast } from "sonner";

export default function MerchantReceiptsPage() {
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["merchant-receipts", search, dateFrom, dateTo],
    queryFn: () =>
      receiptsApi
        .getMerchantReceipts({ search: search || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined })
        .then((r) => r.data),
  });

  const qrMutation = useMutation({
    mutationFn: (receiptId: string) => receiptsApi.getQr(receiptId).then((r) => r.data),
    onSuccess: async (payload) => {
      const absoluteUrl = `${window.location.origin}${payload.verification_url.replace("/api/v1", "")}`;
      await navigator.clipboard.writeText(absoluteUrl);
      toast.success("Lien de verification copie");
    },
    onError: () => toast.error("Impossible de recuperer le QR"),
  });

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      {/* Header */}
      <div
        className="px-5 pt-5 pb-4 sticky top-0 z-10"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>Reçus</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
              {data?.total || 0} reçu{(data?.total || 0) > 1 ? "s" : ""}
            </p>
          </div>
        </div>

        {/* Recherche */}
        <div className="relative mb-3">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: "var(--tx-muted)" }}
          />
          <input
            type="text"
            placeholder="Numéro de reçu ou commande..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 text-sm rounded-xl outline-none"
            style={{
              background: "var(--n-100)",
              color: "var(--tx-head)",
              border: "1.5px solid transparent",
            }}
          />
        </div>

        {/* Filtre date */}
        <div className="flex gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="flex-1 py-2 px-3 text-sm rounded-xl outline-none"
            style={{ background: "var(--n-100)", color: "var(--tx-head)", border: "1.5px solid transparent" }}
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="flex-1 py-2 px-3 text-sm rounded-xl outline-none"
            style={{ background: "var(--n-100)", color: "var(--tx-head)", border: "1.5px solid transparent" }}
          />
        </div>
      </div>

      {/* Liste */}
      <div className="px-4 py-4 space-y-3">
        {isLoading &&
          [...Array(4)].map((_, i) => (
            <div key={i} className="card p-4">
              <div className="skeleton h-16 w-full" />
            </div>
          ))}

        {!isLoading && !data?.items?.length && (
          <div className="text-center py-20">
            <Receipt size={64} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
            <p className="font-semibold" style={{ color: "var(--tx-muted)" }}>Aucun reçu trouvé</p>
          </div>
        )}

        {data?.items?.map((receipt: any) => (
          <div key={receipt.id} className="card overflow-hidden">
            <div className="px-4 py-3 flex items-center gap-3">
              {/* Icône */}
              <div
                className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0"
                style={{ background: "var(--s-50)" }}
              >
                <Receipt size={20} style={{ color: "var(--s-600)" }} />
              </div>

              {/* Infos */}
              <div className="flex-1 min-w-0">
                <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
                  {receipt.receipt_number}
                </p>
                <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                  {receipt.order_number} ·{" "}
                  {new Date(receipt.created_at).toLocaleDateString("fr-FR", {
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>

              {/* Montant */}
              <div className="text-right shrink-0">
                <p className="font-black text-base" style={{ color: "var(--p-500)" }}>
                  {receipt.total_xof?.toLocaleString("fr-FR")} F
                </p>
                {receipt.is_verified && (
                  <span
                    className="text-xs font-semibold"
                    style={{ color: "var(--s-600)" }}
                  >
                    ✓ Vérifié
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div
              className="px-4 py-2 flex gap-3 border-t"
              style={{ borderColor: "var(--bd)", background: "var(--n-50)" }}
            >
              {receipt.pdf_url && (
                <a
                  href={receipt.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs font-semibold"
                  style={{ color: "var(--p-500)" }}
                >
                  <Download size={13} />
                  Télécharger PDF
                </a>
              )}
              <button
                onClick={() => qrMutation.mutate(receipt.id)}
                className="flex items-center gap-1.5 text-xs font-semibold"
                style={{ color: "var(--p-500)" }}
              >
                <QrCode size={13} />
                Copier lien QR
              </button>
              <Link
                href={`/receipts/verify/${receipt.verification_code}`}
                className="flex items-center gap-1.5 text-xs font-semibold ml-auto"
                style={{ color: "var(--tx-muted)" }}
              >
                <ExternalLink size={13} />
                Vérifier
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
