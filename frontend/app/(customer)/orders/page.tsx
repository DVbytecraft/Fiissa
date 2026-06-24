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
        <Package size={64} className="mb-4" style={{ color: "var(--bd)" }} />
        <h2 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>
          Connectez-vous
        </h2>
        <p className="mt-2 text-center" style={{ color: "var(--tx-muted)" }}>
          Pour voir vos commandes, vous devez être connecté
        </p>
        <button className="btn-primary mt-6 max-w-xs" onClick={() => router.push("/login")}>
          Se connecter
        </button>
      </div>
    );
  }

  const orders = data?.items ?? [];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div
        className="px-4 pt-4 pb-4"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <h1 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>
          Mes commandes
        </h1>
      </div>

      <div className="px-4 py-4 pb-6 space-y-3">
        {isLoading &&
          [...Array(4)].map((_, i) => (
            <div key={i} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}>
              <div className="skeleton h-5 w-1/2 mb-2" />
              <div className="skeleton h-4 w-1/3" />
            </div>
          ))}

        {!isLoading && orders.length === 0 && (
          <div className="text-center py-16">
            <Package size={64} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p className="font-semibold" style={{ color: "var(--tx-muted)" }}>
              Aucune commande pour l'instant
            </p>
            <Link href="/" className="text-sm mt-2 block font-semibold" style={{ color: "var(--p-500)" }}>
              Commencer à commander →
            </Link>
          </div>
        )}

        {orders.map((order: any) => (
          <Link key={order.id} href={`/orders/${order.id}`}>
            <div
              className="rounded-2xl p-4 active:scale-95 transition-transform"
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-bold" style={{ color: "var(--tx-head)" }}>
                    {order.order_number}
                  </p>
                  <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {order.items_count} article{order.items_count > 1 ? "s" : ""}
                    {" · "}
                    {order.type === "click_collect" ? "Retrait" : "Livraison"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold" style={{ color: "var(--p-500)" }}>
                    {order.total_xof?.toLocaleString("fr-FR")} FCFA
                  </p>
                  <div className="mt-1">
                    <StatusBadge status={order.status} />
                  </div>
                </div>
              </div>
              <div
                className="flex items-center justify-between mt-3 pt-3"
                style={{ borderTop: "1px solid var(--bg-app)" }}
              >
                <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
                  {new Date(order.created_at).toLocaleDateString("fr-FR", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </p>
                {order.has_receipt && (
                  <div
                    className="flex items-center gap-1 text-xs font-semibold"
                    style={{ color: "var(--p-500)" }}
                  >
                    <Receipt size={12} />
                    <span>Reçu disponible</span>
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
