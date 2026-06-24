"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, ChevronLeft } from "lucide-react";
import Link from "next/link";
import { notificationsApi } from "@/lib/api";
import { toast } from "sonner";

export default function AccountNotificationsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.getAll().then((r) => r.data),
  });

  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => notificationsApi.markRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notification-summary"] });
    },
    onError: () => toast.error("Impossible de marquer la notification comme lue"),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      toast.success("Toutes les notifications sont marquees comme lues");
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notification-summary"] });
    },
    onError: () => toast.error("Impossible de tout marquer comme lu"),
  });

  const items = Array.isArray(data) ? data : [];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div
        className="px-5 pt-4 pb-4 flex items-center gap-3"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <Link href="/account" style={{ color: "var(--tx-muted)" }}>
          <ChevronLeft size={18} />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-black" style={{ color: "var(--tx-head)" }}>
            Notifications
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
            Historique de tes evenements recents
          </p>
        </div>
        <button
          onClick={() => markAllReadMutation.mutate()}
          disabled={markAllReadMutation.isPending || !items.length}
          style={{ color: "var(--p-500)" }}
          className="text-sm font-bold"
        >
          Tout lire
        </button>
      </div>

      <div className="px-4 py-4 space-y-3">
        {isLoading &&
          [...Array(4)].map((_, i) => (
            <div key={i} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
              <div className="skeleton h-16 w-full" />
            </div>
          ))}

        {!isLoading && !items.length && (
          <div className="text-center py-20">
            <Bell size={64} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
            <p className="font-semibold" style={{ color: "var(--tx-head)" }}>
              Aucune notification
            </p>
            <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
              Les prochains evenements apparaitront ici.
            </p>
          </div>
        )}

        {items.map((notification: any) => (
          <button
            key={notification.id}
            onClick={() => !notification.is_read && markReadMutation.mutate(notification.id)}
            className="w-full text-left rounded-2xl p-4"
            style={{
              background: "var(--bg-card)",
              border: `1px solid ${notification.is_read ? "var(--bd)" : "rgba(34,87,255,0.25)"}`,
            }}
          >
            <div className="flex items-start gap-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: notification.is_read ? "rgba(110,122,138,0.08)" : "rgba(34,87,255,0.08)" }}
              >
                {notification.is_read ? (
                  <CheckCheck size={18} style={{ color: "var(--tx-muted)" }} />
                ) : (
                  <Bell size={18} style={{ color: "var(--p-500)" }} />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
                    {notification.title}
                  </p>
                  {!notification.is_read && (
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                      style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
                    >
                      Nouveau
                    </span>
                  )}
                </div>
                <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
                  {notification.body}
                </p>
                <p className="text-xs mt-2" style={{ color: "var(--tx-muted)" }}>
                  {new Date(notification.created_at).toLocaleString("fr-FR")}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
