"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Boxes, Clock, CreditCard, Save, Settings2, Sparkles, Store, Truck } from "lucide-react";
import { toast } from "sonner";
import { companiesApi, storesApi } from "@/lib/api";

const OPERATORS = [
  { value: "wave", label: "Wave" },
  { value: "orange_money", label: "Orange Money" },
  { value: "mtn_momo", label: "MTN MoMo" },
  { value: "moov_money", label: "Moov Money" },
  { value: "free_money", label: "Free Money" },
];

const CATALOG_MODES = [
  { value: "internal", label: "Base Fiissa" },
  { value: "csv_import", label: "Import CSV" },
  { value: "external_api", label: "API externe" },
  { value: "hybrid", label: "Hybride" },
];

const DAYS = [
  { label: "Lun", key: "mon" },
  { label: "Mar", key: "tue" },
  { label: "Mer", key: "wed" },
  { label: "Jeu", key: "thu" },
  { label: "Ven", key: "fri" },
  { label: "Sam", key: "sat" },
  { label: "Dim", key: "sun" },
];

const DEFAULT_HOURS = Object.fromEntries(
  DAYS.map((day) => [day.key, { open: "08:00", close: "20:00" }]),
) as Record<string, { open: string; close: string }>;

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="surface-card p-5">
      <div className="mb-5">
        <h2 className="text-lg font-black" style={{ color: "var(--tx-head)" }}>
          {title}
        </h2>
        <p className="mt-1 text-sm leading-6" style={{ color: "var(--tx-muted)" }}>
          {description}
        </p>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function FeatureToggle({
  enabled,
  label,
  description,
  onToggle,
}: {
  enabled: boolean;
  label: string;
  description: string;
  onToggle: () => void;
}) {
  return (
    <div className="toggle-shell">
      <button onClick={onToggle} className={`toggle-switch ${enabled ? "active" : ""}`} aria-pressed={enabled} />
      <div>
        <p className="text-sm font-bold" style={{ color: "var(--tx-head)" }}>
          {label}
        </p>
        <p className="mt-1 text-xs leading-5" style={{ color: "var(--tx-muted)" }}>
          {description}
        </p>
      </div>
    </div>
  );
}

export default function MerchantSettingsPage() {
  const [activeTab, setActiveTab] = useState<"store" | "payment" | "catalog" | "hours" | "services" | "features">("store");
  const [storeName, setStoreName] = useState("");
  const [storeAddress, setStoreAddress] = useState("");
  const [storePhone, setStorePhone] = useState("");
  const [mmOperator, setMmOperator] = useState("wave");
  const [mmNumber, setMmNumber] = useState("");
  const [mmAccountName, setMmAccountName] = useState("");
  const [clickCollect, setClickCollect] = useState(true);
  const [delivery, setDelivery] = useState(false);
  const [scanGo, setScanGo] = useState(false);
  const [freeDeliveryThreshold, setFreeDeliveryThreshold] = useState("");
  const [catalogMode, setCatalogMode] = useState("internal");
  const [catalogEndpoint, setCatalogEndpoint] = useState("");
  const [catalogMethod, setCatalogMethod] = useState("GET");
  const [catalogApiKey, setCatalogApiKey] = useState("");
  const [catalogApiSecret, setCatalogApiSecret] = useState("");
  const [catalogHeaders, setCatalogHeaders] = useState('{\n  "Accept": "application/json"\n}');
  const [catalogMapping, setCatalogMapping] = useState(
    '{\n  "name": "name",\n  "price_xof": "price_xof",\n  "stock_available": "stock_quantity",\n  "barcode": "barcode",\n  "image_url": "image_url",\n  "unit": "unit"\n}',
  );
  const [catalogTimeout, setCatalogTimeout] = useState("10");
  const [catalogCacheTtl, setCatalogCacheTtl] = useState("300");
  const [catalogFallback, setCatalogFallback] = useState(true);
  const [openingHours, setOpeningHours] = useState<Record<string, { open: string; close: string }>>(DEFAULT_HOURS);
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({});

  const { data: store, isLoading } = useQuery({
    queryKey: ["store-settings"],
    queryFn: () => storesApi.getMyStore().then((response) => response.data),
  });

  const { data: companySettings } = useQuery({
    queryKey: ["company-settings"],
    queryFn: () => companiesApi.getMySettings().then((response) => response.data),
  });

  const { data: catalogConfig } = useQuery({
    queryKey: ["catalog-settings", store?.id],
    queryFn: () => companiesApi.getMyCatalog(store?.id).then((response) => response.data),
    enabled: Boolean(store?.id),
  });

  const { data: flagsData } = useQuery({
    queryKey: ["company-feature-flags"],
    queryFn: () => companiesApi.getMyFeatureFlags().then((response) => response.data),
  });

  useEffect(() => {
    if (!store) return;
    setStoreName(store.name || "");
    setStoreAddress(typeof store.address === "string" ? store.address : store.address?.full || "");
    setStorePhone(store.phone || "");
    setMmOperator(store.mobile_money_info?.operator || "wave");
    setMmNumber(store.mobile_money_info?.number || "");
    setMmAccountName(store.mobile_money_info?.account_name || "");
    setClickCollect(store.click_collect_enabled ?? true);
    setDelivery(store.delivery_enabled ?? false);
    setScanGo(store.scan_go_enabled ?? false);
    setFreeDeliveryThreshold(store.free_delivery_threshold_xof?.toString() || "");
    setOpeningHours({ ...DEFAULT_HOURS, ...(store.opening_hours || {}) });
  }, [store]);

  useEffect(() => {
    if (companySettings?.catalog_mode) setCatalogMode(companySettings.catalog_mode);
  }, [companySettings]);

  useEffect(() => {
    if (!catalogConfig) return;
    setCatalogMode(catalogConfig.mode || "internal");
    setCatalogEndpoint(catalogConfig.integration?.endpoint_url || "");
    setCatalogMethod(catalogConfig.integration?.http_method || "GET");
    setCatalogHeaders(JSON.stringify(catalogConfig.integration?.headers || { Accept: "application/json" }, null, 2));
    setCatalogMapping(
      JSON.stringify(
        catalogConfig.integration?.response_mapping || {
          name: "name",
          price_xof: "price_xof",
          stock_available: "stock_quantity",
          barcode: "barcode",
          image_url: "image_url",
          unit: "unit",
        },
        null,
        2,
      ),
    );
    setCatalogTimeout(String(catalogConfig.integration?.timeout_seconds || 10));
    setCatalogCacheTtl(String(catalogConfig.integration?.cache_ttl_seconds || 300));
    setCatalogFallback(catalogConfig.integration?.fallback_to_internal ?? true);
  }, [catalogConfig]);

  useEffect(() => {
    const items = flagsData?.items ?? [];
    const nextState: Record<string, boolean> = {};
    for (const item of items) nextState[item.key] = !!item.enabled;
    setFeatureFlags(nextState);
  }, [flagsData]);

  const updateStoreMutation = useMutation({
    mutationFn: (payload: any) => storesApi.updateMyStore(payload),
    onSuccess: () => toast.success("Parametres magasin sauvegardes"),
    onError: (error: any) => toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur sauvegarde"),
  });

  const updateCatalogMutation = useMutation({
    mutationFn: (payload: any) => companiesApi.updateMyCatalog(payload),
    onSuccess: () => toast.success("Configuration catalogue sauvegardee"),
    onError: (error: any) => toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur catalogue"),
  });

  const featureFlagMutation = useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) => companiesApi.upsertMyFeatureFlag({ key, enabled }),
    onSuccess: () => toast.success("Feature flag mise a jour"),
    onError: (error: any) => toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur feature flag"),
  });

  const handleSaveStore = () => {
    updateStoreMutation.mutate({
      name: storeName,
      address: storeAddress ? { full: storeAddress } : null,
      phone: storePhone,
    });
  };

  const handleSavePayment = () => {
    updateStoreMutation.mutate({
      mobile_money_info: {
        operator: mmOperator,
        number: mmNumber,
        account_name: mmAccountName,
      },
    });
  };

  const handleSaveServices = () => {
    updateStoreMutation.mutate({
      click_collect_enabled: clickCollect,
      delivery_enabled: delivery,
      scan_go_enabled: scanGo,
      free_delivery_threshold_xof: freeDeliveryThreshold ? parseInt(freeDeliveryThreshold, 10) : null,
    });
  };

  const handleSaveCatalog = () => {
    const payload: Record<string, any> = {
      store_id: store?.id,
      mode: catalogMode,
    };

    if (catalogMode === "external_api" || catalogMode === "hybrid") {
      try {
        payload.endpoint_url = catalogEndpoint;
        payload.http_method = catalogMethod;
        payload.api_key = catalogApiKey || undefined;
        payload.api_secret = catalogApiSecret || undefined;
        payload.headers = JSON.parse(catalogHeaders);
        payload.response_mapping = JSON.parse(catalogMapping);
        payload.timeout_seconds = parseInt(catalogTimeout, 10) || 10;
        payload.cache_ttl_seconds = parseInt(catalogCacheTtl, 10) || 300;
        payload.fallback_to_internal = catalogFallback;
      } catch {
        toast.error("Les champs JSON du catalogue sont invalides");
        return;
      }
    }

    updateCatalogMutation.mutate(payload);
  };

  const handleHoursChange = (dayKey: string, field: "open" | "close", value: string) => {
    setOpeningHours((current) => ({
      ...current,
      [dayKey]: { ...current[dayKey], [field]: value },
    }));
  };

  const handleSaveHours = () => {
    updateStoreMutation.mutate({ opening_hours: openingHours });
  };

  const handleToggleFlag = (key: string) => {
    const nextValue = !featureFlags[key];
    setFeatureFlags((current) => ({ ...current, [key]: nextValue }));
    featureFlagMutation.mutate({ key, enabled: nextValue });
  };

  const tabs = [
    { id: "store", label: "Boutique", icon: <Store size={16} /> },
    { id: "payment", label: "Paiement", icon: <CreditCard size={16} /> },
    { id: "catalog", label: "Catalogue", icon: <Boxes size={16} /> },
    { id: "services", label: "Services", icon: <Truck size={16} /> },
    { id: "hours", label: "Horaires", icon: <Clock size={16} /> },
    { id: "features", label: "Features", icon: <Settings2 size={16} /> },
  ];

  const featureFlagItems = [
    { key: "scan_go", label: "Scan & Go", desc: "Active les experiences Scan & Go cote client." },
    { key: "delivery", label: "Livraison", desc: "Expose les flux de livraison dans l'application." },
    { key: "loyalty", label: "Fidelite", desc: "Active les programmes, coupons et cartes client." },
    { key: "external_catalog", label: "Catalogue externe", desc: "Permet l'usage d'une source API externe." },
    { key: "webhooks", label: "Webhooks", desc: "Autorise les integrations sortantes webhook." },
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen grid place-items-center" style={{ background: "var(--bg-app)" }}>
        <div className="spinner border-blue-600 border-t-transparent w-8 h-8" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      <div className="px-4 pt-5 pb-4 space-y-4">
        <section className="hero-panel p-5">
          <div className="relative">
            <div className="eyebrow">
              <Sparkles size={14} />
              Configuration merchant
            </div>
            <div className="mt-4 flex items-start justify-between gap-4">
              <div>
                <h1 className="text-3xl font-black leading-tight">Parametres de votre espace</h1>
                <p className="mt-2 max-w-xl text-sm leading-6 text-white/75">
                  Reglez la boutique, les paiements, le catalogue, les horaires et les flags fonctionnels depuis un seul endroit.
                </p>
              </div>
              <div className="rounded-2xl bg-white/10 px-4 py-3 text-right backdrop-blur-sm">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-white/60">Boutique</p>
                <p className="mt-1 text-sm font-black">{storeName || "Non renseignee"}</p>
              </div>
            </div>
          </div>
        </section>

        <div className="surface-card p-3">
          <div className="flex gap-2 overflow-x-auto scrollbar-hide">
            {tabs.map(({ id, label, icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as typeof activeTab)}
                className={`segmented-chip ${activeTab === id ? "active" : ""}`}
              >
                <span className="inline-flex items-center gap-2">
                  {icon}
                  {label}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {activeTab === "store" && (
            <SectionCard title="Informations boutique" description="Nom commercial, adresse et telephone visibles dans les parcours client et support.">
              <div>
                <label className="field-label">Nom de la boutique</label>
                <input type="text" value={storeName} onChange={(e) => setStoreName(e.target.value)} className="input-mobile" />
              </div>
              <div>
                <label className="field-label">Adresse</label>
                <input type="text" value={storeAddress} onChange={(e) => setStoreAddress(e.target.value)} className="input-mobile" />
              </div>
              <div>
                <label className="field-label">Telephone</label>
                <input type="tel" value={storePhone} onChange={(e) => setStorePhone(e.target.value)} className="input-mobile" />
              </div>
              <button onClick={handleSaveStore} disabled={updateStoreMutation.isPending} className="btn-primary">
                <Save size={18} />
                {updateStoreMutation.isPending ? "Sauvegarde..." : "Sauvegarder"}
              </button>
            </SectionCard>
          )}

          {activeTab === "payment" && (
            <SectionCard title="Compte Mobile Money" description="Le numero et l'operateur utilises par l'equipe pour rapprocher les paiements manuels.">
              <div>
                <label className="field-label">Operateur</label>
                <select value={mmOperator} onChange={(e) => setMmOperator(e.target.value)} className="input-mobile">
                  {OPERATORS.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="field-label">Numero de reception</label>
                <input type="tel" value={mmNumber} onChange={(e) => setMmNumber(e.target.value)} className="input-mobile" />
              </div>
              <div>
                <label className="field-label">Nom du compte</label>
                <input type="text" value={mmAccountName} onChange={(e) => setMmAccountName(e.target.value)} className="input-mobile" />
              </div>
              <button onClick={handleSavePayment} disabled={updateStoreMutation.isPending} className="btn-primary">
                <Save size={18} />
                {updateStoreMutation.isPending ? "Sauvegarde..." : "Sauvegarder"}
              </button>
            </SectionCard>
          )}

          {activeTab === "catalog" && (
            <SectionCard title="Source catalogue produit" description="Choisissez entre catalogue interne, import CSV ou synchronisation API avec cache et fallback.">
              <div>
                <label className="field-label">Mode catalogue</label>
                <select value={catalogMode} onChange={(e) => setCatalogMode(e.target.value)} className="input-mobile">
                  {CATALOG_MODES.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              {(catalogMode === "external_api" || catalogMode === "hybrid") && (
                <>
                  <div>
                    <label className="field-label">Endpoint URL</label>
                    <input type="text" value={catalogEndpoint} onChange={(e) => setCatalogEndpoint(e.target.value)} className="input-mobile" placeholder="https://erp.example.com/products" />
                  </div>
                  <div>
                    <label className="field-label">Methode HTTP</label>
                    <select value={catalogMethod} onChange={(e) => setCatalogMethod(e.target.value)} className="input-mobile">
                      <option value="GET">GET</option>
                      <option value="POST">POST</option>
                    </select>
                  </div>
                  <div>
                    <label className="field-label">Cle API</label>
                    <input type="password" value={catalogApiKey} onChange={(e) => setCatalogApiKey(e.target.value)} className="input-mobile" placeholder="Laisse vide pour conserver l'existant" />
                  </div>
                  <div>
                    <label className="field-label">Secret / Token</label>
                    <input type="password" value={catalogApiSecret} onChange={(e) => setCatalogApiSecret(e.target.value)} className="input-mobile" placeholder="Laisse vide pour conserver l'existant" />
                  </div>
                  <div>
                    <label className="field-label">Headers JSON</label>
                    <textarea value={catalogHeaders} onChange={(e) => setCatalogHeaders(e.target.value)} className="input-mobile min-h-28 font-mono text-xs" />
                  </div>
                  <div>
                    <label className="field-label">Mapping reponse JSON</label>
                    <textarea value={catalogMapping} onChange={(e) => setCatalogMapping(e.target.value)} className="input-mobile min-h-36 font-mono text-xs" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="field-label">Timeout (s)</label>
                      <input type="number" value={catalogTimeout} onChange={(e) => setCatalogTimeout(e.target.value)} className="input-mobile" />
                    </div>
                    <div>
                      <label className="field-label">Cache TTL (s)</label>
                      <input type="number" value={catalogCacheTtl} onChange={(e) => setCatalogCacheTtl(e.target.value)} className="input-mobile" />
                    </div>
                  </div>
                  <FeatureToggle
                    enabled={catalogFallback}
                    label="Fallback vers le catalogue interne"
                    description="Si l'API externe echoue, Fiissa bascule sur votre catalogue local pour proteger l'experience client."
                    onToggle={() => setCatalogFallback(!catalogFallback)}
                  />
                </>
              )}

              <button onClick={handleSaveCatalog} disabled={updateCatalogMutation.isPending} className="btn-primary">
                <Save size={18} />
                {updateCatalogMutation.isPending ? "Sauvegarde..." : "Sauvegarder"}
              </button>
            </SectionCard>
          )}

          {activeTab === "services" && (
            <SectionCard title="Services disponibles" description="Activez les parcours exposes cote client selon le niveau de service reel de la boutique.">
              <div className="space-y-3">
                <FeatureToggle
                  enabled={clickCollect}
                  label="Click & Collect"
                  description="Le client commande puis recupere sa commande en boutique."
                  onToggle={() => setClickCollect(!clickCollect)}
                />
                <FeatureToggle
                  enabled={delivery}
                  label="Livraison a domicile"
                  description="Ajoute le tunnel livraison et l'adresse client dans le traitement marchand."
                  onToggle={() => setDelivery(!delivery)}
                />
                <FeatureToggle
                  enabled={scanGo}
                  label="Scan & Go"
                  description="Permet au client de scanner ses produits puis de payer avant la sortie."
                  onToggle={() => setScanGo(!scanGo)}
                />
              </div>

              {delivery && (
                <div>
                  <label className="field-label">Seuil livraison gratuite (FCFA)</label>
                  <input type="number" value={freeDeliveryThreshold} onChange={(e) => setFreeDeliveryThreshold(e.target.value)} className="input-mobile" />
                </div>
              )}

              <button onClick={handleSaveServices} disabled={updateStoreMutation.isPending} className="btn-primary">
                <Save size={18} />
                {updateStoreMutation.isPending ? "Sauvegarde..." : "Sauvegarder"}
              </button>
            </SectionCard>
          )}

          {activeTab === "hours" && (
            <SectionCard title="Horaires d'ouverture" description="Horaires affiches au client et reutilises par les parcours magasin et support.">
              <div className="space-y-3">
                {DAYS.map((day) => {
                  const hours = openingHours[day.key] || DEFAULT_HOURS[day.key];
                  return (
                    <div key={day.key} className="surface-card p-3">
                      <div className="flex items-center gap-3">
                        <p className="w-10 text-sm font-black" style={{ color: "var(--tx-head)" }}>
                          {day.label}
                        </p>
                        <input type="time" value={hours.open} onChange={(e) => handleHoursChange(day.key, "open", e.target.value)} className="input-mobile flex-1 py-3 text-center" />
                        <span className="text-sm font-bold" style={{ color: "var(--tx-muted)" }}>
                          →
                        </span>
                        <input type="time" value={hours.close} onChange={(e) => handleHoursChange(day.key, "close", e.target.value)} className="input-mobile flex-1 py-3 text-center" />
                      </div>
                    </div>
                  );
                })}
              </div>
              <button onClick={handleSaveHours} disabled={updateStoreMutation.isPending} className="btn-primary">
                <Save size={18} />
                {updateStoreMutation.isPending ? "Sauvegarde..." : "Sauvegarder les horaires"}
              </button>
            </SectionCard>
          )}

          {activeTab === "features" && (
            <SectionCard title="Feature flags entreprise" description="Controle fin des modules exposes par entreprise pour activer ou restreindre chaque capacite.">
              <div className="space-y-3">
                {featureFlagItems.map((flag) => (
                  <FeatureToggle
                    key={flag.key}
                    enabled={!!featureFlags[flag.key]}
                    label={flag.label}
                    description={flag.desc}
                    onToggle={() => handleToggleFlag(flag.key)}
                  />
                ))}
              </div>
            </SectionCard>
          )}
        </div>
      </div>
    </div>
  );
}
