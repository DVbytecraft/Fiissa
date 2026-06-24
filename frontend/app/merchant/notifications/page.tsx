"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  CheckCheck,
  FileText,
  LayoutTemplate,
  MessageSquareText,
  RefreshCw,
  Save,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { notificationsApi } from "@/lib/api";
import { toast } from "sonner";

type TabKey = "inbox" | "templates" | "events";

const DEFAULT_TEMPLATE_BODY: Record<string, string> = {
  "order.ready": "Bonjour {{ customer_name }}, votre commande {{ order_number }} est prete.",
  "order.cancelled": "Votre commande {{ order_number }} a ete annulee. Motif: {{ reason }}.",
  "payment.confirmed": "Paiement confirme pour {{ order_number }}. Merci pour votre achat.",
  "receipt.generated": "Votre recu {{ receipt_number }} est disponible.",
};

const EVENT_OPTIONS = [
  "order.ready",
  "order.cancelled",
  "payment.confirmed",
  "receipt.generated",
];

const STATUS_OPTIONS = ["pending", "sent", "failed"];

function formatEventLabel(eventKey: string) {
  return eventKey
    .split(".")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

export default function MerchantNotificationsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>("inbox");
  const [eventKey, setEventKey] = useState("order.ready");
  const [channel, setChannel] = useState("in_app");
  const [subjectTemplate, setSubjectTemplate] = useState("");
  const [bodyTemplate, setBodyTemplate] = useState(DEFAULT_TEMPLATE_BODY["order.ready"]);
  const [isActive, setIsActive] = useState(true);
  const [eventFilter, setEventFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data: notificationsData, isLoading: loadingInbox } = useQuery({
    queryKey: ["merchant-notifications-inbox"],
    queryFn: () => notificationsApi.getAll().then((r) => r.data),
  });

  const { data: summary } = useQuery({
    queryKey: ["merchant-notifications-summary"],
    queryFn: () => notificationsApi.getSummary().then((r) => r.data),
  });

  const { data: templatesData, isLoading: loadingTemplates } = useQuery({
    queryKey: ["merchant-notification-templates"],
    queryFn: () => notificationsApi.getTemplates().then((r) => r.data),
  });

  const { data: eventsData, isLoading: loadingEvents } = useQuery({
    queryKey: ["merchant-notification-events", eventFilter, statusFilter],
    queryFn: () =>
      notificationsApi
        .getEvents({
          event_key: eventFilter || undefined,
          status: statusFilter || undefined,
        })
        .then((r) => r.data),
  });

  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => notificationsApi.markRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["merchant-notifications-inbox"] });
      queryClient.invalidateQueries({ queryKey: ["merchant-notifications-summary"] });
    },
    onError: () => toast.error("Impossible de marquer la notification comme lue"),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      toast.success("Toutes les notifications ont ete marquees comme lues");
      queryClient.invalidateQueries({ queryKey: ["merchant-notifications-inbox"] });
      queryClient.invalidateQueries({ queryKey: ["merchant-notifications-summary"] });
    },
    onError: () => toast.error("Impossible de tout marquer comme lu"),
  });

  const saveTemplateMutation = useMutation({
    mutationFn: () =>
      notificationsApi.upsertTemplate({
        event_key: eventKey,
        channel,
        subject_template: subjectTemplate || null,
        body_template: bodyTemplate,
        is_active: isActive,
      }),
    onSuccess: () => {
      toast.success("Template enregistre");
      queryClient.invalidateQueries({ queryKey: ["merchant-notification-templates"] });
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur template"),
  });

  const notifications = useMemo(
    () => (Array.isArray(notificationsData) ? notificationsData : []),
    [notificationsData],
  );
  const templates = templatesData?.items ?? [];
  const events = eventsData?.items ?? [];

  const tabs: Array<{ key: TabKey; label: string; icon: any }> = [
    { key: "inbox", label: "Boite", icon: Bell },
    { key: "templates", label: "Templates", icon: LayoutTemplate },
    { key: "events", label: "Evenements", icon: FileText },
  ];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <section className="px-5 pt-6 pb-6" style={{ background: "var(--fiissa-gradient)" }}>
        <div
          className="rounded-[28px] p-5 text-white relative overflow-hidden"
          style={{
            background:
              "linear-gradient(145deg, rgba(255,255,255,0.18), rgba(255,255,255,0.08))",
            border: "1px solid rgba(255,255,255,0.22)",
            boxShadow: "0 20px 40px rgba(13,18,39,0.18)",
          }}
        >
          <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-white/10" />
          <div className="absolute right-14 top-10 h-16 w-16 rounded-full bg-white/10" />
          <div className="relative">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em]">
              <Sparkles size={14} />
              Centre notifications
            </div>
            <h1 className="mt-4 text-3xl font-black leading-tight">
              Messages, templates et traces d'envoi
            </h1>
            <p className="mt-2 max-w-xl text-sm text-white/80">
              Une surface unique pour piloter l'experience de communication de ta boutique.
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-3xl bg-white/90 p-4 text-slate-900 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Non lues</p>
            <p className="mt-2 text-3xl font-black">{summary?.unread_count ?? 0}</p>
            <p className="mt-1 text-sm text-slate-500">a traiter par l'equipe</p>
          </div>
          <div className="rounded-3xl bg-slate-950/85 p-4 text-white shadow-sm">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-white/60">Events</p>
            <p className="mt-2 text-3xl font-black">{events.length}</p>
            <p className="mt-1 text-sm text-white/70">sur le dernier chargement</p>
          </div>
        </div>
      </section>

      <div className="px-4 py-5 space-y-5">
        <div className="flex gap-2 overflow-x-auto scrollbar-hide">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className="shrink-0 rounded-full px-4 py-2.5 text-sm font-bold transition-all"
              style={
                activeTab === key
                  ? { background: "var(--tx-head)", color: "white", boxShadow: "var(--sh-md)" }
                  : { background: "var(--bg-card)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }
              }
            >
              <span className="inline-flex items-center gap-2">
                <Icon size={15} />
                {label}
              </span>
            </button>
          ))}
        </div>

        {activeTab === "inbox" && (
          <>
            <div
              className="rounded-[28px] p-4"
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-black" style={{ color: "var(--tx-head)" }}>
                    Boite de reception
                  </h2>
                  <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
                    Les alertes recues par le compte connecte.
                  </p>
                </div>
                <button
                  onClick={() => markAllReadMutation.mutate()}
                  disabled={markAllReadMutation.isPending || !notifications.length}
                  className="rounded-full px-4 py-2 text-sm font-bold"
                  style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
                >
                  Tout lire
                </button>
              </div>
            </div>

            {loadingInbox &&
              [...Array(4)].map((_, index) => (
                <div key={index} className="rounded-[28px] p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
                  <div className="skeleton h-20 w-full" />
                </div>
              ))}

            {!loadingInbox && notifications.length === 0 && (
              <div
                className="rounded-[32px] p-10 text-center"
                style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              >
                <Bell size={56} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
                <p className="text-lg font-black" style={{ color: "var(--tx-head)" }}>
                  Aucune notification pour le moment
                </p>
                <p className="mt-2 text-sm" style={{ color: "var(--tx-muted)" }}>
                  Les validations de paiement, commandes pretes et recus apparaitront ici.
                </p>
              </div>
            )}

            {notifications.map((notification: any) => (
              <button
                key={notification.id}
                onClick={() => !notification.is_read && markReadMutation.mutate(notification.id)}
                className="w-full rounded-[28px] p-4 text-left transition-transform active:scale-[0.99]"
                style={{
                  background: notification.is_read
                    ? "var(--bg-card)"
                    : "linear-gradient(180deg, rgba(34,87,255,0.08), rgba(0,214,143,0.04))",
                  border: `1px solid ${notification.is_read ? "var(--bd)" : "rgba(34,87,255,0.18)"}`,
                  boxShadow: "var(--sh-sm)",
                }}
              >
                <div className="flex items-start gap-3">
                  <div
                    className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
                    style={{
                      background: notification.is_read ? "rgba(110,122,138,0.08)" : "rgba(34,87,255,0.1)",
                    }}
                  >
                    {notification.is_read ? (
                      <CheckCheck size={18} style={{ color: "var(--tx-muted)" }} />
                    ) : (
                      <Bell size={18} style={{ color: "var(--p-500)" }} />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-black" style={{ color: "var(--tx-head)" }}>
                        {notification.title}
                      </p>
                      {!notification.is_read && (
                        <span
                          className="rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em]"
                          style={{ background: "var(--p-500)", color: "white" }}
                        >
                          Nouveau
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm leading-6" style={{ color: "var(--tx-body)" }}>
                      {notification.body}
                    </p>
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <span className="text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--tx-muted)" }}>
                        {notification.type || notification.channel}
                      </span>
                      <span className="text-xs" style={{ color: "var(--tx-muted)" }}>
                        {new Date(notification.created_at).toLocaleString("fr-FR")}
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </>
        )}

        {activeTab === "templates" && (
          <div className="space-y-4">
            <div
              className="rounded-[28px] p-5"
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
            >
              <div className="mb-4">
                <h2 className="text-lg font-black" style={{ color: "var(--tx-head)" }}>
                  Composer un template
                </h2>
                <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
                  Tu peux personnaliser les messages sortants pour chaque evenement metier.
                </p>
              </div>

              <div className="space-y-3">
                <div className="grid gap-3 md:grid-cols-2">
                  <select
                    value={eventKey}
                    onChange={(e) => {
                      const next = e.target.value;
                      setEventKey(next);
                      setBodyTemplate(DEFAULT_TEMPLATE_BODY[next] || bodyTemplate);
                    }}
                    className="input-mobile"
                  >
                    {EVENT_OPTIONS.map((event) => (
                      <option key={event} value={event}>
                        {formatEventLabel(event)}
                      </option>
                    ))}
                  </select>

                  <select value={channel} onChange={(e) => setChannel(e.target.value)} className="input-mobile">
                    <option value="in_app">In app</option>
                    <option value="email">Email</option>
                  </select>
                </div>

                <input
                  value={subjectTemplate}
                  onChange={(e) => setSubjectTemplate(e.target.value)}
                  placeholder="Sujet email facultatif"
                  className="input-mobile"
                />

                <textarea
                  value={bodyTemplate}
                  onChange={(e) => setBodyTemplate(e.target.value)}
                  className="input-mobile min-h-[160px]"
                  placeholder="Corps du message"
                />

                <div
                  className="flex items-start gap-3 rounded-3xl p-4"
                  style={{ background: "rgba(34,87,255,0.05)", border: "1px solid rgba(34,87,255,0.08)" }}
                >
                  <button
                    onClick={() => setIsActive((current) => !current)}
                    className="relative mt-1 h-7 w-12 rounded-full transition-colors"
                    style={{ background: isActive ? "var(--p-500)" : "var(--n-300)" }}
                  >
                    <span
                      className="absolute top-1 h-5 w-5 rounded-full bg-white transition-transform"
                      style={{ transform: isActive ? "translateX(1.5rem)" : "translateX(0.25rem)" }}
                    />
                  </button>
                  <div>
                    <p className="text-sm font-bold" style={{ color: "var(--tx-head)" }}>
                      Template actif
                    </p>
                    <p className="text-xs leading-5" style={{ color: "var(--tx-muted)" }}>
                      Desactive le template si tu veux suspendre temporairement cet envoi.
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => saveTemplateMutation.mutate()}
                  disabled={!bodyTemplate.trim() || saveTemplateMutation.isPending}
                  className="btn-primary"
                >
                  <Save size={18} />
                  {saveTemplateMutation.isPending ? "Enregistrement..." : "Enregistrer le template"}
                </button>
              </div>
            </div>

            <div
              className="rounded-[28px] p-5"
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
            >
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-black" style={{ color: "var(--tx-head)" }}>
                    Templates existants
                  </h3>
                  <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
                    Lis, recharges puis clique pour reutiliser une configuration.
                  </p>
                </div>
                <button
                  onClick={() => queryClient.invalidateQueries({ queryKey: ["merchant-notification-templates"] })}
                  className="rounded-full p-2"
                  style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
                >
                  <RefreshCw size={16} />
                </button>
              </div>

              {loadingTemplates ? (
                <div className="skeleton h-24 w-full" />
              ) : templates.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
                  Aucun template personnalise pour cette entreprise.
                </p>
              ) : (
                <div className="space-y-3">
                  {templates.map((template: any) => (
                    <button
                      key={template.id}
                      onClick={() => {
                        setEventKey(template.event_key);
                        setChannel(template.channel);
                        setSubjectTemplate(template.subject_template || "");
                        setBodyTemplate(template.body_template || "");
                        setIsActive(!!template.is_active);
                        setActiveTab("templates");
                      }}
                      className="w-full rounded-[24px] p-4 text-left"
                      style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-black" style={{ color: "var(--tx-head)" }}>
                            {formatEventLabel(template.event_key)}
                          </p>
                          <p className="mt-1 text-xs uppercase tracking-[0.12em]" style={{ color: "var(--tx-muted)" }}>
                            {template.channel}
                          </p>
                        </div>
                        <span
                          className="rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em]"
                          style={{
                            background: template.is_active ? "rgba(0,214,143,0.1)" : "rgba(239,68,68,0.08)",
                            color: template.is_active ? "var(--s-600)" : "var(--error)",
                          }}
                        >
                          {template.is_active ? "Actif" : "Pause"}
                        </span>
                      </div>
                      <p className="mt-3 text-sm leading-6" style={{ color: "var(--tx-body)" }}>
                        {template.body_template}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "events" && (
          <div className="space-y-4">
            <div
              className="rounded-[28px] p-5"
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
            >
              <div className="mb-4 flex items-center gap-3">
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-2xl"
                  style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
                >
                  <MessageSquareText size={20} />
                </div>
                <div>
                  <h2 className="text-lg font-black" style={{ color: "var(--tx-head)" }}>
                    Journal des evenements
                  </h2>
                  <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
                    Trace les envois et echec de diffusion pour la boutique.
                  </p>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <select
                  value={eventFilter}
                  onChange={(e) => setEventFilter(e.target.value)}
                  className="input-mobile"
                >
                  <option value="">Tous les evenements</option>
                  {EVENT_OPTIONS.map((event) => (
                    <option key={event} value={event}>
                      {formatEventLabel(event)}
                    </option>
                  ))}
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="input-mobile"
                >
                  <option value="">Tous les statuts</option>
                  {STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {loadingEvents ? (
              <div className="rounded-[28px] p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
                <div className="skeleton h-28 w-full" />
              </div>
            ) : events.length === 0 ? (
              <div
                className="rounded-[28px] p-10 text-center"
                style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              >
                <TriangleAlert size={52} className="mx-auto mb-4" style={{ color: "var(--bd)" }} />
                <p className="text-lg font-black" style={{ color: "var(--tx-head)" }}>
                  Aucun evenement sur ce filtre
                </p>
                <p className="mt-2 text-sm" style={{ color: "var(--tx-muted)" }}>
                  Elargis les filtres pour voir davantage d'activite.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {events.map((event: any) => (
                  <div
                    key={event.id}
                    className="rounded-[28px] p-4"
                    style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-black" style={{ color: "var(--tx-head)" }}>
                          {formatEventLabel(event.event_key)}
                        </p>
                        <p className="mt-1 text-xs uppercase tracking-[0.12em]" style={{ color: "var(--tx-muted)" }}>
                          {event.resource_type || "resource"} {event.resource_id || ""}
                        </p>
                      </div>
                      <span
                        className="rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em]"
                        style={{
                          background:
                            event.status === "failed"
                              ? "rgba(239,68,68,0.08)"
                              : event.status === "sent"
                                ? "rgba(0,214,143,0.1)"
                                : "rgba(245,158,11,0.12)",
                          color:
                            event.status === "failed"
                              ? "var(--error)"
                              : event.status === "sent"
                                ? "var(--s-600)"
                                : "#B45309",
                        }}
                      >
                        {event.status}
                      </span>
                    </div>

                    {event.error_message && (
                      <div
                        className="mt-3 rounded-2xl px-3 py-2 text-sm"
                        style={{ background: "#FEF2F2", color: "#B91C1C", border: "1px solid #FECACA" }}
                      >
                        {event.error_message}
                      </div>
                    )}

                    <pre
                      className="mt-3 overflow-x-auto rounded-2xl p-3 text-xs leading-6"
                      style={{ background: "var(--bg-app)", color: "var(--tx-body)", border: "1px solid var(--bd)" }}
                    >
                      {JSON.stringify(event.payload || {}, null, 2)}
                    </pre>

                    <p className="mt-3 text-xs" style={{ color: "var(--tx-muted)" }}>
                      {new Date(event.created_at).toLocaleString("fr-FR")}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
