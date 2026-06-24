"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Webhook,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  Link,
  RefreshCw,
  Send,
  X,
  Key,
  Copy,
  RotateCcw,
  Terminal,
} from "lucide-react";
import { companiesApi, integrationsApi } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmModal } from "@/components/ui/confirm-modal";

const WEBHOOK_EVENTS = [
  { value: "order.created", label: "Commande créée" },
  { value: "order.ready", label: "Commande prête" },
  { value: "order.cancelled", label: "Commande annulée" },
  { value: "payment.confirmed", label: "Paiement confirmé" },
  { value: "receipt.generated", label: "Reçu généré" },
];

const CATALOG_MODES = [
  { value: "internal", label: "Base Fiissa", desc: "Produits gérés directement" },
  { value: "csv_import", label: "Import CSV", desc: "Catalogue importé via fichier CSV" },
  { value: "external_api", label: "API externe", desc: "ERP / POS externe" },
  { value: "hybrid", label: "Hybride", desc: "API externe + fallback interne" },
];

function WebhookModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [selectedEvents, setSelectedEvents] = useState<string[]>(["order.created", "payment.confirmed"]);
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: () =>
      integrationsApi.createWebhook({
        name,
        target_url: url,
        secret: secret || undefined,
        events: selectedEvents,
        is_active: true,
      }),
    onSuccess: () => {
      toast.success("Webhook configuré");
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur création webhook"),
  });

  const toggleEvent = (event: string) => {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end">
      <div
        style={{ background: "var(--bg-card)" }}
        className="rounded-t-3xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between">
          <h3 style={{ color: "var(--tx-head)" }} className="text-lg font-bold">
            Ajouter un webhook
          </h3>
          <button onClick={onClose} style={{ color: "var(--tx-muted)" }} className="w-8 h-8 flex items-center justify-center rounded-full" onMouseOver={(e) => (e.currentTarget.style.background = "var(--n-100)")} onMouseOut={(e) => (e.currentTarget.style.background = "")}>
            <X size={18} />
          </button>
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Nom
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Mon ERP / Notifications Slack"
            className="input-mobile"
          />
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            URL cible *
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://votre-systeme.com/webhook"
            className="input-mobile"
          />
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Secret de signature (optionnel)
          </label>
          <div className="relative">
            <input
              type={showSecret ? "text" : "password"}
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="whsec_..."
              className="input-mobile pr-10"
            />
            <button
              onClick={() => setShowSecret(!showSecret)}
              style={{ color: "var(--tx-muted)" }}
              className="absolute right-3 top-1/2 -translate-y-1/2"
            >
              {showSecret ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-2 block">
            Événements déclencheurs
          </label>
          <div className="space-y-2">
            {WEBHOOK_EVENTS.map((event) => (
              <label key={event.value} className="flex items-center gap-3 cursor-pointer">
                <div
                  onClick={() => toggleEvent(event.value)}
                  style={{
                    background: selectedEvents.includes(event.value) ? "var(--p-500)" : "var(--bg-app)",
                    border: `2px solid ${selectedEvents.includes(event.value) ? "var(--p-500)" : "var(--bd)"}`,
                  }}
                  className="w-5 h-5 rounded flex items-center justify-center shrink-0"
                >
                  {selectedEvents.includes(event.value) && (
                    <CheckCircle size={12} className="text-white" />
                  )}
                </div>
                <span style={{ color: "var(--tx-head)" }} className="text-sm">
                  {event.label}
                </span>
                <code style={{ color: "var(--tx-muted)" }} className="text-xs font-mono ml-auto">
                  {event.value}
                </code>
              </label>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}
            className="flex-1 py-3 rounded-xl font-semibold"
          >
            Annuler
          </button>
          <button
            onClick={() => createMutation.mutate()}
            disabled={!url.trim() || selectedEvents.length === 0 || createMutation.isPending}
            style={{ background: "var(--p-500)" }}
            className="flex-1 py-3 text-white rounded-xl font-bold disabled:opacity-50"
          >
            {createMutation.isPending ? "Création..." : "Créer webhook"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ApiKeySection() {
  const [revealed, setRevealed] = useState(false);
  const [confirmRegen, setConfirmRegen] = useState(false);
  const queryClient = useQueryClient();

  const { data: apiKeyData, isLoading } = useQuery({
    queryKey: ["merchant-api-key"],
    queryFn: () => integrationsApi.getApiKey().then((r) => r.data),
  });

  const regenMutation = useMutation({
    mutationFn: () => integrationsApi.regenerateApiKey(),
    onSuccess: () => {
      toast.success("Clé API régénérée");
      setConfirmRegen(false);
      setRevealed(false);
      queryClient.invalidateQueries({ queryKey: ["merchant-api-key"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur régénération"),
  });

  const maskedKey = apiKeyData?.api_key
    ? `${apiKeyData.api_key.slice(0, 8)}${"•".repeat(24)}${apiKeyData.api_key.slice(-4)}`
    : "fsk_live_••••••••••••••••••••••••••••";

  const copyKey = () => {
    if (!apiKeyData?.api_key) return;
    navigator.clipboard.writeText(apiKeyData.api_key);
    toast.success("Clé copiée !");
  };

  const ENDPOINT_DOCS = [
    { method: "GET",  path: "/catalog/products/barcode/{barcode}", desc: "Lookup produit par code-barres" },
    { method: "GET",  path: "/catalog/products",                   desc: "Liste des produits du catalogue" },
    { method: "POST", path: "/orders",                             desc: "Créer une commande" },
    { method: "GET",  path: "/orders/{id}",                        desc: "Statut d'une commande" },
  ];

  return (
    <div className="space-y-4">
      {/* Carte clé API */}
      <div style={{ background: "var(--fiissa-gradient)", borderRadius: 24 }} className="p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-2xl flex items-center justify-center" style={{ background: "rgba(255,255,255,0.15)" }}>
            <Key size={20} className="text-white" />
          </div>
          <div>
            <p className="text-white font-black">Clé API Fiissa</p>
            <p className="text-white/60 text-xs">Connexion ERP · POS · API externe</p>
          </div>
        </div>

        {isLoading ? (
          <div className="skeleton h-12 w-full rounded-xl" />
        ) : (
          <div className="rounded-xl p-3 flex items-center gap-3" style={{ background: "rgba(0,0,0,0.25)" }}>
            <code className="flex-1 text-sm text-white/90 font-mono truncate">
              {revealed ? apiKeyData?.api_key || maskedKey : maskedKey}
            </code>
            <button
              onClick={() => setRevealed((v) => !v)}
              className="shrink-0 text-white/60 hover:text-white transition-colors"
            >
              {revealed ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
            <button onClick={copyKey} className="shrink-0 text-white/60 hover:text-white transition-colors">
              <Copy size={16} />
            </button>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <p className="text-white/50 text-xs">
            Généré le {apiKeyData?.created_at
              ? new Date(apiKeyData.created_at).toLocaleDateString("fr-FR")
              : "—"}
          </p>
          <button
            onClick={() => setConfirmRegen(true)}
            className="flex items-center gap-1.5 text-xs font-bold text-white/70 hover:text-white transition-colors"
          >
            <RotateCcw size={13} />
            Régénérer
          </button>
        </div>
      </div>

      {/* Avertissement régénération */}
      {confirmRegen && (
        <div className="rounded-2xl p-4 space-y-3" style={{ background: "rgba(220,38,38,0.06)", border: "1px solid rgba(220,38,38,0.15)" }}>
          <p className="font-bold text-sm" style={{ color: "#DC2626" }}>Régénérer la clé ?</p>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
            L'ancienne clé sera révoquée immédiatement. Toutes les intégrations actives cesseront de fonctionner jusqu'à mise à jour.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => setConfirmRegen(false)}
              className="flex-1 py-2.5 rounded-xl text-sm font-semibold"
              style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}
            >
              Annuler
            </button>
            <button
              onClick={() => regenMutation.mutate()}
              disabled={regenMutation.isPending}
              className="flex-1 py-2.5 rounded-xl text-sm font-bold text-white"
              style={{ background: "#DC2626" }}
            >
              {regenMutation.isPending ? "Révocation..." : "Confirmer"}
            </button>
          </div>
        </div>
      )}

      {/* Endpoints disponibles */}
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }} className="rounded-2xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Terminal size={16} style={{ color: "var(--p-500)" }} />
          <h3 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
            Endpoints disponibles
          </h3>
        </div>
        <div className="space-y-2">
          {ENDPOINT_DOCS.map((ep) => (
            <div key={ep.path} className="flex items-start gap-3 py-2" style={{ borderBottom: "1px solid var(--bg-app)" }}>
              <span
                className="shrink-0 text-xs font-black px-2 py-0.5 rounded-md mt-0.5"
                style={{
                  background: ep.method === "GET" ? "rgba(34,87,255,0.08)" : "rgba(0,214,143,0.08)",
                  color: ep.method === "GET" ? "var(--p-500)" : "var(--s-500)",
                }}
              >
                {ep.method}
              </span>
              <div className="flex-1 min-w-0">
                <code className="text-xs font-mono truncate block" style={{ color: "var(--tx-head)" }}>{ep.path}</code>
                <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>{ep.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Usage guide */}
      <div className="rounded-2xl p-4" style={{ background: "rgba(34,87,255,0.04)", border: "1px solid rgba(34,87,255,0.10)" }}>
        <p className="font-bold text-sm mb-2" style={{ color: "var(--p-500)" }}>Utilisation</p>
        <p className="text-xs leading-relaxed mb-3" style={{ color: "var(--tx-muted)" }}>
          Ajoutez l'en-tête suivant à chaque requête vers l'API Fiissa :
        </p>
        <div className="rounded-xl p-3" style={{ background: "var(--bg-dark)" }}>
          <code className="text-xs text-green-400 font-mono">
            Authorization: Bearer {"<votre-clé-api>"}
          </code>
        </div>
        <p className="text-xs mt-3 leading-relaxed" style={{ color: "var(--tx-muted)" }}>
          URL de base : <code className="font-mono" style={{ color: "var(--tx-head)" }}>https://api.fiissa.com/v1</code>
        </p>
      </div>
    </div>
  );
}

export default function MerchantIntegrationsPage() {
  const [showWebhookModal, setShowWebhookModal] = useState(false);
  const [activeTab, setActiveTab] = useState<"webhooks" | "catalog" | "api_key">("webhooks");
  const [confirmWebhook, setConfirmWebhook] = useState<{ id: string; name: string } | null>(null);
  const queryClient = useQueryClient();

  const { data: webhooks, isLoading: loadingWebhooks } = useQuery({
    queryKey: ["webhooks"],
    queryFn: () => integrationsApi.getWebhooks().then((r) => r.data),
    enabled: activeTab === "webhooks",
  });

  const { data: deliveries, isLoading: loadingDeliveries } = useQuery({
    queryKey: ["webhook-deliveries"],
    queryFn: () => integrationsApi.getWebhookDeliveries().then((r) => r.data),
    enabled: activeTab === "webhooks",
  });

  const { data: catalogConfig, isLoading: loadingCatalog } = useQuery({
    queryKey: ["catalog-config"],
    queryFn: () => companiesApi.getMyCatalog().then((r) => r.data),
    enabled: activeTab === "catalog",
  });

  const deleteWebhookMutation = useMutation({
    mutationFn: (id: string) => integrationsApi.deleteWebhook(id),
    onSuccess: () => {
      toast.success("Webhook supprimé");
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });

  const testWebhookMutation = useMutation({
    mutationFn: (id: string) => integrationsApi.testWebhook(id),
    onSuccess: () => {
      toast.success("Webhook teste");
      queryClient.invalidateQueries({ queryKey: ["webhook-deliveries"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur test webhook"),
  });

  const toggleWebhookMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      integrationsApi.updateWebhook(id, { is_active: active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });

  const webhookList = webhooks?.items || webhooks || [];
  const deliveryList = deliveries?.items || [];

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      {/* Header */}
      <div
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
        className="px-6 pt-6 pb-4"
      >
        <h1 style={{ color: "var(--tx-head)" }} className="text-xl font-bold mb-4">
          Intégrations
        </h1>

        <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-0.5">
          {[
            { id: "webhooks", label: "Webhooks" },
            { id: "catalog", label: "Catalogue API" },
            { id: "api_key", label: "Clé API" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={
                activeTab === tab.id
                  ? { background: "var(--p-500)", color: "#fff" }
                  : { background: "var(--bg-app)", color: "var(--tx-muted)" }
              }
              className="px-4 py-2 rounded-full text-sm font-medium"
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 py-4">
        {/* ── WEBHOOKS ── */}
        {activeTab === "webhooks" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <p style={{ color: "var(--tx-muted)" }} className="text-sm">
                {webhookList.length} webhook{webhookList.length !== 1 ? "s" : ""}
              </p>
              <button
                onClick={() => setShowWebhookModal(true)}
                style={{ background: "var(--p-500)" }}
                className="flex items-center gap-2 px-4 py-2 text-white rounded-xl text-sm font-semibold"
              >
                <Plus size={16} />
                Ajouter
              </button>
            </div>

            {loadingWebhooks &&
              [...Array(2)].map((_, i) => (
                <div key={i} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
                  <div className="skeleton h-16 w-full" />
                </div>
              ))}

            {!loadingWebhooks && webhookList.length === 0 && (
              <div className="text-center py-16">
                <Webhook size={64} style={{ color: "var(--bd)" }} className="mx-auto mb-4" />
                <p style={{ color: "var(--tx-head)" }} className="font-semibold mb-1">
                  Aucun webhook configuré
                </p>
                <p style={{ color: "var(--tx-muted)" }} className="text-sm mb-4">
                  Recevez des notifications HTTP pour chaque événement Fiissa
                </p>
                <button
                  onClick={() => setShowWebhookModal(true)}
                  style={{ background: "var(--p-500)" }}
                  className="px-6 py-3 text-white rounded-xl font-semibold text-sm mx-auto"
                >
                  Créer un webhook
                </button>
              </div>
            )}

            {webhookList.map((wh: any) => (
              <div
                key={wh.id}
                style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
                className="rounded-2xl p-4"
              >
                <div className="flex items-start gap-3">
                  <div
                    style={{
                      background: wh.is_active ? "rgba(0,214,143,0.1)" : "rgba(110,122,138,0.08)",
                    }}
                    className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  >
                    <Link
                      size={18}
                      style={{ color: wh.is_active ? "var(--s-500)" : "var(--tx-muted)" }}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p style={{ color: "var(--tx-head)" }} className="font-bold text-sm">
                      {wh.name || "Webhook"}
                    </p>
                    <p style={{ color: "var(--tx-muted)" }} className="text-xs truncate">
                      {wh.target_url}
                    </p>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {wh.events?.map((ev: string) => (
                        <span
                          key={ev}
                          style={{ background: "rgba(34,87,255,0.06)", color: "var(--p-500)" }}
                          className="text-xs font-mono px-1.5 py-0.5 rounded"
                        >
                          {ev}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div
                  style={{ borderTop: "1px solid var(--bd)" }}
                  className="mt-3 pt-3 flex items-center gap-3 flex-wrap"
                >
                  <button
                    onClick={() =>
                      toggleWebhookMutation.mutate({ id: wh.id, active: !wh.is_active })
                    }
                    style={{ color: wh.is_active ? "var(--s-500)" : "var(--tx-muted)" }}
                    className="flex items-center gap-1.5 text-xs font-semibold"
                  >
                    {wh.is_active ? (
                      <><CheckCircle size={14} /> Actif</>
                    ) : (
                      <><XCircle size={14} /> Inactif</>
                    )}
                  </button>
                  <button
                    onClick={() => testWebhookMutation.mutate(wh.id)}
                    disabled={testWebhookMutation.isPending}
                    style={{ color: "var(--p-500)" }}
                    className="flex items-center gap-1.5 text-xs font-semibold"
                  >
                    <Send size={14} />
                    Tester
                  </button>
                  <button
                    onClick={() => setConfirmWebhook({ id: wh.id, name: wh.name })}
                    className="ml-auto flex items-center gap-1.5 text-xs font-semibold"
                    style={{ color: "#DC2626" }}
                  >
                    <Trash2 size={14} />
                    Supprimer
                  </button>
                </div>
              </div>
            ))}

            <div
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              className="rounded-2xl p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <h3 style={{ color: "var(--tx-head)" }} className="font-bold text-sm">
                  Livraisons webhook recentes
                </h3>
                <button
                  onClick={() => queryClient.invalidateQueries({ queryKey: ["webhook-deliveries"] })}
                  style={{ color: "var(--tx-muted)" }}
                  className="flex items-center gap-1.5 text-xs font-semibold"
                >
                  <RefreshCw size={13} />
                  Rafraichir
                </button>
              </div>

              {loadingDeliveries ? (
                <div className="skeleton h-24 w-full" />
              ) : deliveryList.length === 0 ? (
                <p style={{ color: "var(--tx-muted)" }} className="text-sm">
                  Aucune livraison webhook pour le moment.
                </p>
              ) : (
                <div className="space-y-2">
                  {deliveryList.slice(0, 8).map((delivery: any) => (
                    <div
                      key={delivery.id}
                      style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
                      className="rounded-xl p-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <code style={{ color: "var(--tx-head)" }} className="text-xs font-mono">
                          {delivery.event_type}
                        </code>
                        <span
                          style={{
                            background:
                              delivery.status === "success"
                                ? "rgba(0,214,143,0.1)"
                                : delivery.status === "failed"
                                  ? "rgba(220,38,38,0.08)"
                                  : "rgba(245,158,11,0.08)",
                            color:
                              delivery.status === "success"
                                ? "var(--s-500)"
                                : delivery.status === "failed"
                                  ? "#DC2626"
                                  : "#D97706",
                          }}
                          className="text-xs font-bold px-2 py-0.5 rounded-full"
                        >
                          {delivery.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-1.5 text-xs">
                        <span style={{ color: "var(--tx-muted)" }}>
                          HTTP {delivery.response_status ?? "-"}
                        </span>
                        <span style={{ color: "var(--tx-muted)" }}>
                          Retries {delivery.retry_count}
                        </span>
                        <span style={{ color: "var(--tx-muted)" }} className="ml-auto">
                          {new Date(delivery.created_at).toLocaleString("fr-FR")}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── CATALOGUE API ── */}
        {activeTab === "catalog" && (
          <div className="space-y-4">
            {/* Mode actuel */}
            <div
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              className="rounded-2xl p-4"
            >
              <h3 style={{ color: "var(--tx-head)" }} className="font-bold mb-3">
                Mode catalogue actuel
              </h3>
              {loadingCatalog ? (
                <div className="skeleton h-8 w-32" />
              ) : (
                <div className="space-y-2">
                  {CATALOG_MODES.map((mode) => {
                    const isCurrent = catalogConfig?.mode === mode.value;
                    return (
                      <div
                        key={mode.value}
                        style={{
                          border: `2px solid ${isCurrent ? "var(--p-500)" : "var(--bd)"}`,
                          background: isCurrent ? "rgba(34,87,255,0.03)" : "transparent",
                        }}
                        className="rounded-xl p-3 flex items-center gap-3"
                      >
                        <div
                          style={{
                            background: isCurrent ? "var(--p-500)" : "var(--bg-app)",
                            border: `2px solid ${isCurrent ? "var(--p-500)" : "var(--bd)"}`,
                          }}
                          className="w-4 h-4 rounded-full shrink-0"
                        />
                        <div>
                          <p style={{ color: "var(--tx-head)" }} className="font-semibold text-sm">
                            {mode.label}
                          </p>
                          <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                            {mode.desc}
                          </p>
                        </div>
                        {isCurrent && (
                          <span
                            style={{ background: "rgba(0,214,143,0.1)", color: "var(--s-500)" }}
                            className="ml-auto text-xs font-bold px-2 py-0.5 rounded-full"
                          >
                            Actif
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Config API externe */}
            {(catalogConfig?.mode === "external_api" || catalogConfig?.mode === "hybrid") && (
              <div
                style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
                className="rounded-2xl p-4"
              >
                <h3 style={{ color: "var(--tx-head)" }} className="font-bold mb-3">
                  Configuration API externe
                </h3>
                <div className="space-y-2">
                  <div>
                    <p style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1">
                      URL de l'API
                    </p>
                    <p
                      style={{ background: "var(--bg-app)", color: "var(--tx-head)" }}
                      className="text-sm font-mono px-3 py-2 rounded-xl truncate"
                    >
                      {catalogConfig?.integration?.endpoint_url || "Non configuré"}
                    </p>
                  </div>
                  {catalogConfig?.integration?.masked_credentials && (
                    <div>
                      <p style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1">
                        Clé API
                      </p>
                      <p
                        style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}
                        className="text-sm font-mono px-3 py-2 rounded-xl"
                      >
                        {catalogConfig.integration.masked_credentials.api_key || "••••••••"}
                      </p>
                    </div>
                  )}
                  <div className="flex gap-3 text-sm pt-1">
                    <span style={{ color: "var(--tx-muted)" }}>
                      TTL cache : {catalogConfig?.integration?.cache_ttl_seconds || 300}s
                    </span>
                    <span style={{ color: "var(--tx-muted)" }}>·</span>
                    <span style={{ color: "var(--tx-muted)" }}>
                      Timeout : {catalogConfig?.integration?.timeout_seconds || 10}s
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Info */}
            <div
              style={{ background: "rgba(34,87,255,0.04)", border: "1px solid rgba(34,87,255,0.1)" }}
              className="rounded-2xl p-4"
            >
              <p style={{ color: "var(--tx-head)" }} className="text-sm font-semibold mb-1">
                Changer le mode catalogue
              </p>
              <p style={{ color: "var(--tx-muted)" }} className="text-xs leading-relaxed">
                La configuration du mode catalogue se fait dans les paramètres du magasin.
                Le frontend Scan & Go (GET /catalog/products/barcode/{`{barcode}`}) utilise
                automatiquement le mode configuré pour votre entreprise.
              </p>
            </div>
          </div>
        )}
        {/* ── CLÉ API ── */}
        {activeTab === "api_key" && <ApiKeySection />}
      </div>

      {showWebhookModal && <WebhookModal onClose={() => setShowWebhookModal(false)} />}

      <ConfirmModal
        open={!!confirmWebhook}
        title="Supprimer le webhook"
        message={`Supprimer "${confirmWebhook?.name}" ? Les notifications vers cet endpoint cesseront immédiatement.`}
        confirmLabel="Supprimer"
        variant="danger"
        onConfirm={() => {
          if (confirmWebhook) deleteWebhookMutation.mutate(confirmWebhook.id);
          setConfirmWebhook(null);
        }}
        onCancel={() => setConfirmWebhook(null)}
      />
    </div>
  );
}
