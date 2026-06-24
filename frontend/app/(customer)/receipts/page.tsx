"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Receipt, ShieldCheck } from "lucide-react";
import { receiptsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function ReceiptsPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ["my-receipts"],
    queryFn: () => receiptsApi.getMyReceipts().then((response) => response.data),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-6">
        <Receipt size={64} className="mb-4" style={{ color: "var(--bd)" }} />
        <h2 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>
          Connectez-vous
        </h2>
        <p className="mt-2 text-center" style={{ color: "var(--tx-muted)" }}>
          Pour consulter vos recus, vous devez etre connecte.
        </p>
        <button className="btn-primary mt-6 max-w-xs" onClick={() => router.push("/login")}>
          Se connecter
        </button>
      </div>
    );
  }

  const receipts = data || [];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div className="px-4 pt-4 pb-4" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <h1 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>
          Mes recus
        </h1>
      </div>

      <div className="px-4 py-4 space-y-3">
        {isLoading &&
          [...Array(4)].map((_, index) => (
            <div key={index} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}>
              <div className="skeleton h-5 w-1/2 mb-2" />
              <div className="skeleton h-4 w-1/3" />
            </div>
          ))}

        {!isLoading && receipts.length === 0 && (
          <div className="text-center py-16">
            <Receipt size={64} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p className="font-semibold" style={{ color: "var(--tx-muted)" }}>
              Aucun recu disponible
            </p>
            <Link href="/orders" className="text-sm mt-2 block font-semibold" style={{ color: "var(--p-500)" }}>
              Voir mes commandes →
            </Link>
          </div>
        )}

        {receipts.map((receipt: any) => (
          <Link key={receipt.id} href={`/receipts/${receipt.id}`}>
            <div className="rounded-2xl p-4 active:scale-95 transition-transform" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-bold" style={{ color: "var(--tx-head)" }}>
                    {receipt.receipt_number}
                  </p>
                  <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {receipt.store_name || "Fiissa"} · {receipt.order_number || "Commande"}
                  </p>
                </div>
                <p className="font-bold" style={{ color: "var(--p-500)" }}>
                  {receipt.total_xof?.toLocaleString("fr-FR")} FCFA
                </p>
              </div>
              <div className="flex items-center justify-between mt-3 pt-3" style={{ borderTop: "1px solid var(--bg-app)" }}>
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                  {new Date(receipt.created_at).toLocaleDateString("fr-FR", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </p>
                <div className="flex items-center gap-1 text-xs font-semibold" style={{ color: receipt.is_verified ? "var(--s-500)" : "var(--p-500)" }}>
                  <ShieldCheck size={12} />
                  <span>{receipt.is_verified ? "Verifie" : "Verifiable"}</span>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
