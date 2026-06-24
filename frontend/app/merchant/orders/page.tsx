"use client";

import { Suspense, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Package, ChevronRight, Play, CheckCircle } from "lucide-react";
import { ordersApi } from "@/lib/api";
import { toast } from "sonner";

const STATUS_TABS = [
  { status: "payment_submitted", label: "À confirmer", active: "#F59E0B", bg: "#FFFBEB" },
  { status: "confirmed", label: "À préparer", active: "var(--p-500)", bg: "rgba(34,87,255,0.06)" },
  { status: "preparing", label: "En cours", active: "#F97316", bg: "#FFF7ED" },
  { status: "ready", label: "Prêtes", active: "var(--s-500)", bg: "rgba(0,214,143,0.06)" },
  { status: "delivered", label: "Livrées", active: "var(--tx-muted)", bg: "var(--bg-app)" },
];

const STATUS_LABELS: Record<string, string> = {
  payment_submitted: "Paiement soumis",
  confirmed: "Confirmée",
  preparing: "En préparation",
  ready: "Prête",
  delivered: "Livrée",
  cancelled: "Annulée",
};

function OrderRow({ order, onStatusUpdate }: { order: any; onStatusUpdate: () => void }) {
  const updateMutation = useMutation({
    mutationFn: (newStatus: string) => ordersApi.updateStatus(order.id, newStatus),
    onSuccess: () => {
      toast.success("Statut mis à jour");
      onStatusUpdate();
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur"),
  });

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
      <Link href={`/merchant/orders/${order.id}`}>
        <div className="px-4 py-3 flex items-center gap-3 active:opacity-80">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: "rgba(34,87,255,0.08)" }}>
            <Package size={18} style={{ color: "var(--p-500)" }} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{order.order_number}</p>
            <p className="text-xs truncate" style={{ color: "var(--tx-muted)" }}>
              {order.customer_name} · {order.items_count} article{order.items_count > 1 ? "s" : ""}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="font-bold text-sm" style={{ color: "var(--p-500)" }}>{order.total_xof?.toLocaleString("fr-FR")} F</p>
            <p className="text-xs" style={{ color: "var(--tx-muted)" }}>{order.type === "click_collect" ? "Retrait" : "Livraison"}</p>
          </div>
          <ChevronRight size={16} className="shrink-0" style={{ color: "var(--bd)" }} />
        </div>
      </Link>

      {order.status === "confirmed" && (
        <div className="px-4 py-2.5" style={{ borderTop: "1px solid var(--bg-app)", background: "rgba(34,87,255,0.03)" }}>
          <button
            onClick={() => updateMutation.mutate("preparing")}
            disabled={updateMutation.isPending}
            className="flex items-center gap-2 text-sm font-bold active:opacity-70"
            style={{ color: "var(--p-500)" }}
          >
            <Play size={15} />
            Commencer la préparation
          </button>
        </div>
      )}

      {order.status === "preparing" && (
        <div className="px-4 py-2.5" style={{ borderTop: "1px solid var(--bg-app)", background: "rgba(0,214,143,0.06)" }}>
          <button
            onClick={() => updateMutation.mutate("ready")}
            disabled={updateMutation.isPending}
            className="flex items-center gap-2 text-sm font-bold active:opacity-70"
            style={{ color: "var(--s-500)" }}
          >
            <CheckCircle size={15} />
            Marquer comme prête
          </button>
        </div>
      )}
    </div>
  );
}

export default function MerchantOrdersPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" style={{ background: "var(--bg-app)" }} />}>
      <MerchantOrdersPageContent />
    </Suspense>
  );
}

function MerchantOrdersPageContent() {
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get("status") || "confirmed";
  const [activeStatus, setActiveStatus] = useState(initialStatus);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["merchant-orders", activeStatus],
    queryFn: () => ordersApi.getMerchantOrders(activeStatus).then((r) => r.data),
    refetchInterval: 15000,
  });

  const activeTab = STATUS_TABS.find((t) => t.status === activeStatus);

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div className="pb-0" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <div className="px-5 pt-4 pb-3">
          <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>Commandes</h1>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 overflow-x-auto pb-3 px-4 scrollbar-hide">
          {STATUS_TABS.map(({ status, label, active, bg }) => (
            <button
              key={status}
              onClick={() => setActiveStatus(status)}
              className="shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-colors"
              style={
                activeStatus === status
                  ? { background: bg, color: active, border: `1.5px solid ${active}` }
                  : { background: "var(--bg-app)", color: "var(--tx-muted)", border: "1.5px solid transparent" }
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        {isLoading &&
          [...Array(3)].map((_, i) => (
            <div key={i} className="rounded-2xl p-4" style={{ background: "var(--bg-card)" }}>
              <div className="skeleton h-16 w-full" />
            </div>
          ))}

        {!isLoading && data?.items?.length === 0 && (
          <div className="text-center py-16">
            <Package size={64} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p style={{ color: "var(--tx-muted)" }}>Aucune commande dans ce statut</p>
          </div>
        )}

        {data?.items?.map((order: any) => (
          <OrderRow
            key={order.id}
            order={order}
            onStatusUpdate={() =>
              queryClient.invalidateQueries({ queryKey: ["merchant-orders", activeStatus] })
            }
          />
        ))}
      </div>
    </div>
  );
}
