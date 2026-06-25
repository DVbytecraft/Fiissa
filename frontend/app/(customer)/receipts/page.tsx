"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Receipt, ShieldCheck, WifiOff } from "lucide-react";
import { receiptsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function ReceiptsPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [isOffline, setIsOffline] = useState(false);

  /* ── Service Worker offline cache ── */
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/offline-receipts-sw.js", { scope: "/" })
        .catch(() => {});
    }

    const handleOffline = () => setIsOffline(true);
    const handleOnline  = () => setIsOffline(false);
    setIsOffline(!navigator.onLine);
    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ["my-receipts"],
    queryFn:  () => receiptsApi.getMyReceipts().then((r) => r.data),
    enabled:  isAuthenticated,
    /* Données servies depuis le SW cache si hors ligne */
    staleTime: 0,
  });

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-6">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center mb-5"
          style={{ background: "var(--n-100)" }}
        >
          <Receipt size={36} style={{ color: "var(--n-400)" }} />
        </div>
        <h2 className="text-2xl font-black" style={{ color: "var(--tx-head)" }}>
          Mes reçus
        </h2>
        <p className="mt-2 text-center" style={{ color: "var(--tx-muted)" }}>
          Connecte-toi pour consulter tes reçus
        </p>
        <button className="btn-action mt-6 max-w-xs" onClick={() => router.push("/login")}>
          Se connecter
        </button>
      </div>
    );
  }

  const receipts = Array.isArray(data) ? data : (data?.items ?? data?.results ?? []);

  const handleExportMonth = () => {
    window.open(`/api/v1/receipts/export/monthly`, "_blank");
  };

  return (
    <div style={{ background: "var(--bg-layout)", minHeight: "100vh" }}>

      {/* Header */}
      <div
        className="px-5 py-4 flex items-center justify-between"
        style={{ background: "#FFFFFF", borderBottom: "1px solid var(--bd)" }}
      >
        <h1 className="text-2xl font-black" style={{ color: "var(--tx-head)" }}>Mes reçus</h1>
        {receipts.length > 0 && (
          <button
            onClick={handleExportMonth}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-bold transition-colors"
            style={{ background: "var(--n-100)", color: "var(--tx-body)" }}
          >
            <Download size={14} />
            Exporter
          </button>
        )}
      </div>

      {/* Bannière hors ligne */}
      {isOffline && (
        <div
          className="mx-4 mt-4 rounded-2xl px-4 py-3 flex items-center gap-3"
          style={{ background: "rgba(107,114,128,0.12)", border: "1px solid rgba(107,114,128,0.25)" }}
        >
          <WifiOff size={16} style={{ color: "#6B7280" }} className="flex-shrink-0" />
          <p className="text-sm font-bold" style={{ color: "#6B7280" }}>
            Hors ligne — affichage depuis le cache local (5 derniers reçus)
          </p>
        </div>
      )}

      <div className="px-5 py-4 space-y-3">
        {isLoading &&
          [...Array(4)].map((_, i) => (
            <div key={i} className="rounded-2xl p-4" style={{ background: "#FFFFFF" }}>
              <div className="skeleton h-5 w-1/2 mb-2" />
              <div className="skeleton h-4 w-1/3" />
            </div>
          ))}

        {!isLoading && receipts.length === 0 && (
          <div className="text-center py-16">
            <Receipt size={56} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
            <p className="font-bold" style={{ color: "var(--tx-head)" }}>Aucun reçu</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
              Tes reçus apparaîtront ici après chaque achat
            </p>
            <Link href="/orders" className="inline-block mt-4 text-sm font-bold" style={{ color: "var(--color-action)" }}>
              Voir mes commandes →
            </Link>
          </div>
        )}

        {receipts.map((receipt: any) => (
          <Link key={receipt.id} href={`/receipts/${receipt.id}`}>
            <div
              className="rounded-2xl p-4 active:scale-[0.99] transition-transform"
              style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-black" style={{ color: "var(--tx-head)" }}>
                    {receipt.receipt_number}
                  </p>
                  <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {receipt.store_name || "Fiissa"} · {receipt.order_number || "Commande"}
                  </p>
                </div>
                <p className="font-black flex-shrink-0" style={{ color: "var(--tx-head)" }}>
                  {receipt.total_xof?.toLocaleString("fr-FR")} FCFA
                </p>
              </div>

              <div
                className="flex items-center justify-between mt-3 pt-3"
                style={{ borderTop: "1px solid var(--bg-layout)" }}
              >
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                  {new Date(receipt.created_at).toLocaleDateString("fr-FR", {
                    day:   "numeric",
                    month: "long",
                    year:  "numeric",
                  })}
                </p>
                <div
                  className="flex items-center gap-1 text-xs font-bold"
                  style={{ color: receipt.is_verified ? "var(--s-600)" : "var(--tx-muted)" }}
                >
                  <ShieldCheck size={12} />
                  <span>{receipt.is_verified ? "Vérifié" : "Vérifiable"}</span>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
