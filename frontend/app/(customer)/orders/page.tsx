"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ordersApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Package, Receipt } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";

export default function OrdersPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ["my-orders"],
    queryFn: () => ordersApi.getMyOrders().then((r) => r.data),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-6">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center mb-5"
          style={{ background: "var(--n-100)" }}
        >
          <Package size={36} style={{ color: "var(--n-400)" }} />
        </div>
        <h2 className="text-2xl font-black" style={{ color: "var(--tx-head)" }}>
          Mes commandes
        </h2>
        <p className="mt-2 text-center" style={{ color: "var(--tx-muted)" }}>
          Connecte-toi pour voir tes commandes
        </p>
        <button className="btn-action mt-6 max-w-xs" onClick={() => router.push("/login")}>
          Se connecter
        </button>
      </div>
    );
  }

  const orders = data?.items ?? [];

  return (
    <div style={{ background: "var(--bg-layout)", minHeight: "100vh" }}>

      {/* Header */}
      <div
        className="px-5 py-4"
        style={{ background: "#FFFFFF", borderBottom: "1px solid var(--bd)" }}
      >
        <h1 className="text-2xl font-black" style={{ color: "var(--tx-head)" }}>Mes commandes</h1>
      </div>

      <div className="px-5 py-4 pb-6 space-y-3">
        {isLoading &&
          [...Array(4)].map((_, i) => (
            <div key={i} className="rounded-2xl p-4" style={{ background: "#FFFFFF" }}>
              <div className="skeleton h-5 w-1/2 mb-2" />
              <div className="skeleton h-4 w-1/3" />
            </div>
          ))}

        {!isLoading && orders.length === 0 && (
          <div className="text-center py-16">
            <Package size={56} className="mx-auto mb-4" style={{ color: "var(--n-300)" }} />
            <p className="font-bold" style={{ color: "var(--tx-head)" }}>Aucune commande</p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
              Tes futures commandes apparaîtront ici
            </p>
            <Link href="/" className="inline-block mt-4 text-sm font-bold" style={{ color: "var(--color-action)" }}>
              Commencer à commander →
            </Link>
          </div>
        )}

        {orders.map((order: any) => (
          <Link key={order.id} href={`/orders/${order.id}`}>
            <div
              className="rounded-2xl p-4 active:scale-[0.99] transition-transform"
              style={{ background: "#FFFFFF", border: "1px solid var(--bd)" }}
            >
              {/* Ligne principale */}
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-black" style={{ color: "var(--tx-head)" }}>
                    {order.order_number}
                  </p>
                  <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {order.items_count} article{order.items_count > 1 ? "s" : ""}
                    {" · "}
                    {order.type === "click_collect" ? "Retrait" : order.type === "scan_go" ? "Scan & Go" : "Livraison"}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="font-black" style={{ color: "var(--tx-head)" }}>
                    {order.total_xof?.toLocaleString("fr-FR")} FCFA
                  </p>
                  <div className="mt-1">
                    <StatusBadge status={order.status} />
                  </div>
                </div>
              </div>

              {/* Pied de carte */}
              <div
                className="flex items-center justify-between mt-3 pt-3"
                style={{ borderTop: "1px solid var(--bg-layout)" }}
              >
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                  {new Date(order.created_at).toLocaleDateString("fr-FR", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </p>
                {order.has_receipt && (
                  <div className="flex items-center gap-1 text-xs font-bold" style={{ color: "var(--s-600)" }}>
                    <Receipt size={12} />
                    <span>Reçu dispo</span>
                  </div>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
