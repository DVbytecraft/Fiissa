"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BadgePercent,
  ChevronRight,
  Gift,
  GraduationCap,
  Layers,
  Plus,
  Power,
  PowerOff,
  Tag,
  Users,
} from "lucide-react";
import { loyaltyApi } from "@/lib/api";
import { toast } from "sonner";

// ── Types d'onglets ──────────────────────────────────────────────────────────

type Tab = "programmes" | "niveaux" | "recompenses" | "templates";

const TABS: { key: Tab; label: string; icon: any }[] = [
  { key: "programmes", label: "Programmes", icon: BadgePercent },
  { key: "niveaux", label: "Niveaux", icon: GraduationCap },
  { key: "recompenses", label: "Récompenses", icon: Gift },
  { key: "templates", label: "Templates", icon: Layers },
];

// ── Onglet : Programmes ──────────────────────────────────────────────────────

function ProgramsTab() {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [pointsPerXof, setPointsPerXof] = useState("0.01");
  const [minSpend, setMinSpend] = useState("500");
  const [description, setDescription] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["merchant-loyalty-programs"],
    queryFn: () => loyaltyApi.getPrograms().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      loyaltyApi.createProgram({
        name: name.trim(),
        description: description.trim() || undefined,
        points_per_xof: parseFloat(pointsPerXof) || 0.01,
        min_spend_xof: parseInt(minSpend, 10) || 0,
      }),
    onSuccess: () => {
      setName(""); setDescription(""); setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["merchant-loyalty-programs"] });
      toast.success("Programme créé — activez-le pour émettre des cartes");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur création"),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => loyaltyApi.activateProgram(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["merchant-loyalty-programs"] });
      toast.success("Programme activé");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => loyaltyApi.deactivateProgram(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["merchant-loyalty-programs"] });
      toast.success("Programme désactivé");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur"),
  });

  const programs: any[] = data ?? [];
  const previewPoints = Math.max(1, Math.floor(10000 * (parseFloat(pointsPerXof) || 0)));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide" style={{ color: "var(--tx-muted)" }}>
          Programmes ({programs.length})
        </p>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-white"
          style={{ background: "var(--p-500)" }}
        >
          <Plus size={13} /> Créer
        </button>
      </div>

      {showForm && (
        <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <h3 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Nouveau programme</h3>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex : Club Fidélité" className="input-mobile" />
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optionnel)" className="input-mobile" />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Points / XOF</label>
              <input value={pointsPerXof} onChange={(e) => setPointsPerXof(e.target.value)} className="input-mobile" type="number" step="0.001" min="0" />
            </div>
            <div>
              <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Achat min. (XOF)</label>
              <input value={minSpend} onChange={(e) => setMinSpend(e.target.value)} className="input-mobile" type="number" min="0" />
            </div>
          </div>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
            Aperçu : 10 000 XOF = <strong>{previewPoints} points</strong>
          </p>
          <div className="flex gap-2">
            <button onClick={() => setShowForm(false)} className="flex-1 py-3 rounded-xl font-semibold text-sm" style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}>Annuler</button>
            <button onClick={() => createMutation.mutate()} disabled={!name.trim() || createMutation.isPending} className="flex-1 btn-primary">{createMutation.isPending ? "Création…" : "Créer"}</button>
          </div>
        </div>
      )}

      {isLoading && <div className="skeleton h-24 w-full rounded-2xl" />}

      {!isLoading && programs.length === 0 && !showForm && (
        <div className="rounded-2xl p-6 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <BadgePercent size={36} className="mx-auto mb-3" style={{ color: "var(--bd)" }} />
          <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>Aucun programme</p>
          <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>Créez votre premier programme avec le bouton Créer</p>
        </div>
      )}

      <div className="space-y-3">
        {programs.map((prog) => (
          <div key={prog.id} className="rounded-2xl p-4" style={{ background: "var(--bg-card)", border: `1px solid ${prog.is_active ? "rgba(34,87,255,0.3)" : "var(--bd)"}` }}>
            <div className="flex items-start justify-between gap-2 mb-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{prog.name}</p>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: prog.is_active ? "rgba(0,214,143,0.15)" : "rgba(107,114,128,0.1)", color: prog.is_active ? "#00A86B" : "var(--tx-muted)" }}>
                    {prog.is_active ? "Actif" : "Inactif"}
                  </span>
                </div>
                {prog.description && <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>{prog.description}</p>}
                <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
                  {prog.points_per_xof} pts/XOF · min {(prog.min_spend_xof || 0).toLocaleString("fr-FR")} XOF
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              {prog.is_active ? (
                <button onClick={() => deactivateMutation.mutate(prog.id)} disabled={deactivateMutation.isPending} className="flex-1 py-2.5 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5" style={{ background: "#FEF2F2", color: "#DC2626", border: "1px solid #FCA5A5" }}>
                  <PowerOff size={12} /> Désactiver
                </button>
              ) : (
                <button onClick={() => activateMutation.mutate(prog.id)} disabled={activateMutation.isPending} className="flex-1 py-2.5 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5" style={{ background: "rgba(0,214,143,0.1)", color: "#00A86B", border: "1px solid rgba(0,214,143,0.3)" }}>
                  <Power size={12} /> Activer
                </button>
              )}
              <Link href={`/merchant/customers?program=${prog.id}`} className="flex-1 py-2.5 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5" style={{ background: "var(--bg-app)", color: "var(--tx-head)", border: "1px solid var(--bd)" }}>
                <Users size={12} /> Clients
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Onglet : Niveaux ─────────────────────────────────────────────────────────

function TiersTab() {
  const [selectedProgram, setSelectedProgram] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [tierName, setTierName] = useState("");
  const [minPoints, setMinPoints] = useState("0");
  const [multiplier, setMultiplier] = useState("1.0");
  const queryClient = useQueryClient();

  const { data: programs } = useQuery({
    queryKey: ["merchant-loyalty-programs"],
    queryFn: () => loyaltyApi.getPrograms().then((r) => r.data),
  });

  const programList: any[] = programs ?? [];
  const programId = selectedProgram || programList[0]?.id || "";

  const { data: tiersData, isLoading } = useQuery({
    queryKey: ["loyalty-tiers", programId],
    queryFn: () => loyaltyApi.getTiers(programId).then((r) => r.data),
    enabled: !!programId,
  });

  const tiers: any[] = tiersData ?? [];

  const createMutation = useMutation({
    mutationFn: () =>
      loyaltyApi.createTier(programId, {
        name: tierName.trim(),
        min_points: parseInt(minPoints, 10) || 0,
        multiplier: parseFloat(multiplier) || 1,
      }),
    onSuccess: () => {
      setTierName(""); setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["loyalty-tiers", programId] });
      toast.success("Niveau créé");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur création niveau"),
  });

  if (programList.length === 0) {
    return (
      <div className="text-center py-10" style={{ color: "var(--tx-muted)" }}>
        <GraduationCap size={40} className="mx-auto mb-3" style={{ color: "var(--bd)" }} />
        <p className="text-sm">Créez d'abord un programme dans l'onglet Programmes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {programList.length > 1 && (
        <select value={programId} onChange={(e) => setSelectedProgram(e.target.value)} className="input-mobile">
          {programList.map((p: any) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      )}

      <div className="flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide" style={{ color: "var(--tx-muted)" }}>
          Niveaux ({tiers.length})
        </p>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-white" style={{ background: "var(--p-500)" }}>
          <Plus size={13} /> Ajouter
        </button>
      </div>

      {showForm && (
        <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <h3 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Nouveau niveau</h3>
          <input value={tierName} onChange={(e) => setTierName(e.target.value)} placeholder="Ex : Bronze, Argent, Or" className="input-mobile" />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Points minimum</label>
              <input value={minPoints} onChange={(e) => setMinPoints(e.target.value)} className="input-mobile" type="number" min="0" />
            </div>
            <div>
              <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Multiplicateur</label>
              <input value={multiplier} onChange={(e) => setMultiplier(e.target.value)} className="input-mobile" type="number" step="0.1" min="1" />
            </div>
          </div>
          <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
            Un multiplicateur de 2× double les points gagnés à ce niveau.
          </p>
          <div className="flex gap-2">
            <button onClick={() => setShowForm(false)} className="flex-1 py-3 rounded-xl font-semibold text-sm" style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}>Annuler</button>
            <button onClick={() => createMutation.mutate()} disabled={!tierName.trim() || createMutation.isPending} className="flex-1 btn-primary">{createMutation.isPending ? "Création…" : "Créer"}</button>
          </div>
        </div>
      )}

      {isLoading && <div className="skeleton h-20 w-full rounded-2xl" />}

      {!isLoading && tiers.length === 0 && (
        <div className="rounded-2xl p-5 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <p className="text-sm" style={{ color: "var(--tx-muted)" }}>Aucun niveau. Ajoutez Bronze, Argent, Or pour segmenter vos clients.</p>
        </div>
      )}

      <div className="space-y-2">
        {tiers.sort((a, b) => a.min_points - b.min_points).map((tier, i) => (
          <div key={tier.id} className="rounded-2xl p-4 flex items-center gap-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <div className="w-9 h-9 rounded-xl flex items-center justify-center font-semibold text-sm flex-shrink-0" style={{ background: "rgba(245,158,11,0.1)", color: "#D97706" }}>
              {i + 1}
            </div>
            <div className="flex-1">
              <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{tier.name}</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                Dès {tier.min_points.toLocaleString("fr-FR")} pts · ×{tier.multiplier}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Onglet : Récompenses ─────────────────────────────────────────────────────

function RewardsTab() {
  const [selectedProgram, setSelectedProgram] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [rewardName, setRewardName] = useState("");
  const [rewardType, setRewardType] = useState("discount_pct");
  const [value, setValue] = useState("10");
  const [pointsCost, setPointsCost] = useState("500");
  const [description, setDescription] = useState("");
  const queryClient = useQueryClient();

  const { data: programs } = useQuery({
    queryKey: ["merchant-loyalty-programs"],
    queryFn: () => loyaltyApi.getPrograms().then((r) => r.data),
  });

  const programList: any[] = programs ?? [];
  const programId = selectedProgram || programList[0]?.id || "";

  const { data: rewardsData, isLoading } = useQuery({
    queryKey: ["loyalty-rewards", programId],
    queryFn: () => loyaltyApi.getRewards(programId).then((r) => r.data),
    enabled: !!programId,
  });

  const rewards: any[] = rewardsData ?? [];

  const createMutation = useMutation({
    mutationFn: () =>
      loyaltyApi.createReward(programId, {
        name: rewardName.trim(),
        description: description.trim() || undefined,
        reward_type: rewardType,
        value: parseFloat(value) || 0,
        points_cost: parseInt(pointsCost, 10) || 100,
        is_active: true,
      }),
    onSuccess: () => {
      setRewardName(""); setDescription(""); setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["loyalty-rewards", programId] });
      toast.success("Récompense créée");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur création récompense"),
  });

  if (programList.length === 0) {
    return (
      <div className="text-center py-10" style={{ color: "var(--tx-muted)" }}>
        <Gift size={40} className="mx-auto mb-3" style={{ color: "var(--bd)" }} />
        <p className="text-sm">Créez d'abord un programme dans l'onglet Programmes.</p>
      </div>
    );
  }

  const REWARD_TYPES = [
    { value: "discount_pct", label: "Remise %" },
    { value: "discount_fixed", label: "Remise fixe (F)" },
    { value: "free_product", label: "Produit offert" },
    { value: "other", label: "Autre" },
  ];

  return (
    <div className="space-y-4">
      {programList.length > 1 && (
        <select value={programId} onChange={(e) => setSelectedProgram(e.target.value)} className="input-mobile">
          {programList.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      )}

      <div className="flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide" style={{ color: "var(--tx-muted)" }}>
          Récompenses ({rewards.length})
        </p>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-white" style={{ background: "var(--p-500)" }}>
          <Plus size={13} /> Créer
        </button>
      </div>

      {showForm && (
        <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <h3 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Nouvelle récompense</h3>
          <input value={rewardName} onChange={(e) => setRewardName(e.target.value)} placeholder="Ex : Remise 10% fidélité" className="input-mobile" />
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optionnel)" className="input-mobile" />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Type</label>
              <select value={rewardType} onChange={(e) => setRewardType(e.target.value)} className="input-mobile">
                {REWARD_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>
                Valeur {rewardType === "discount_pct" ? "(%)" : rewardType === "discount_fixed" ? "(F)" : ""}
              </label>
              <input value={value} onChange={(e) => setValue(e.target.value)} className="input-mobile" type="number" min="0" />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Coût en points</label>
            <input value={pointsCost} onChange={(e) => setPointsCost(e.target.value)} className="input-mobile" type="number" min="1" />
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowForm(false)} className="flex-1 py-3 rounded-xl font-semibold text-sm" style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}>Annuler</button>
            <button onClick={() => createMutation.mutate()} disabled={!rewardName.trim() || createMutation.isPending} className="flex-1 btn-primary">{createMutation.isPending ? "Création…" : "Créer"}</button>
          </div>
        </div>
      )}

      {isLoading && <div className="skeleton h-20 w-full rounded-2xl" />}
      {!isLoading && rewards.length === 0 && (
        <div className="rounded-2xl p-5 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <p className="text-sm" style={{ color: "var(--tx-muted)" }}>Aucune récompense. Créez des avantages que vos clients pourront réclamer.</p>
        </div>
      )}

      <div className="space-y-2">
        {rewards.map((reward: any) => (
          <div key={reward.id} className="rounded-2xl p-4 flex items-center gap-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", opacity: reward.is_active ? 1 : 0.6 }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "rgba(0,214,143,0.08)" }}>
              <Gift size={18} style={{ color: "var(--s-500)" }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="font-bold text-sm truncate" style={{ color: "var(--tx-head)" }}>{reward.name}</p>
                {!reward.is_active && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full flex-shrink-0" style={{ background: "rgba(110,122,138,0.1)", color: "var(--tx-muted)" }}>Inactif</span>}
              </div>
              <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                {reward.points_cost.toLocaleString("fr-FR")} pts ·{" "}
                {reward.reward_type === "discount_pct" ? `−${reward.value}%` : reward.reward_type === "discount_fixed" ? `−${reward.value} F` : reward.reward_type}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Onglet : Templates de cartes ─────────────────────────────────────────────

function TemplatesTab() {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [bgColor, setBgColor] = useState("#1A1A2E");
  const [textColor, setTextColor] = useState("#FFFFFF");
  const [isDefault, setIsDefault] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["card-templates"],
    queryFn: () => loyaltyApi.getCardTemplates().then((r) => r.data),
  });

  const templates: any[] = data ?? [];

  const createMutation = useMutation({
    mutationFn: () =>
      loyaltyApi.createCardTemplate({
        name: name.trim(),
        background_color: bgColor,
        text_color: textColor,
        is_default: isDefault,
      }),
    onSuccess: () => {
      setName(""); setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["card-templates"] });
      toast.success("Template créé");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erreur création template"),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide" style={{ color: "var(--tx-muted)" }}>
          Templates ({templates.length})
        </p>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-white" style={{ background: "var(--p-500)" }}>
          <Plus size={13} /> Créer
        </button>
      </div>

      {showForm && (
        <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <h3 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Nouveau template</h3>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex : Carte Bronze, Carte VIP" className="input-mobile" />

          {/* Prévisualisation */}
          <div className="rounded-2xl p-4 relative overflow-hidden" style={{ background: bgColor, color: textColor, minHeight: 100 }}>
            <div className="absolute -right-6 -top-6 w-24 h-24 rounded-full" style={{ background: "rgba(255,255,255,0.05)" }} />
            <p className="text-xs font-semibold mb-2" style={{ opacity: 0.7 }}>Prévisualisation</p>
            <p className="font-mono text-xs mb-1" style={{ opacity: 0.6 }}>•••• •••• 1234</p>
            <p className="font-bold text-xl">1 250 pts</p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Fond</label>
              <div className="flex items-center gap-2">
                <input type="color" value={bgColor} onChange={(e) => setBgColor(e.target.value)} className="w-10 h-10 rounded-lg border-0 cursor-pointer" style={{ border: "1px solid var(--bd)" }} />
                <input value={bgColor} onChange={(e) => setBgColor(e.target.value)} className="input-mobile flex-1 font-mono text-xs" placeholder="#1A1A2E" />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold mb-1 block" style={{ color: "var(--tx-muted)" }}>Texte</label>
              <div className="flex items-center gap-2">
                <input type="color" value={textColor} onChange={(e) => setTextColor(e.target.value)} className="w-10 h-10 rounded-lg cursor-pointer" style={{ border: "1px solid var(--bd)" }} />
                <input value={textColor} onChange={(e) => setTextColor(e.target.value)} className="input-mobile flex-1 font-mono text-xs" placeholder="#FFFFFF" />
              </div>
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} className="w-4 h-4 rounded" />
            <span className="text-sm" style={{ color: "var(--tx-head)" }}>Template par défaut</span>
          </label>

          <div className="flex gap-2">
            <button onClick={() => setShowForm(false)} className="flex-1 py-3 rounded-xl font-semibold text-sm" style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}>Annuler</button>
            <button onClick={() => createMutation.mutate()} disabled={!name.trim() || createMutation.isPending} className="flex-1 btn-primary">{createMutation.isPending ? "Création…" : "Créer"}</button>
          </div>
        </div>
      )}

      {isLoading && <div className="skeleton h-24 w-full rounded-2xl" />}
      {!isLoading && templates.length === 0 && (
        <div className="rounded-2xl p-5 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <Layers size={36} className="mx-auto mb-3" style={{ color: "var(--bd)" }} />
          <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>Aucun template</p>
          <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
            Les templates définissent l'apparence des cartes fidélité de vos clients.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {templates.map((t: any) => (
          <div key={t.id} className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--bd)" }}>
            {/* Mini carte preview */}
            <div className="p-4 relative overflow-hidden" style={{ background: t.background_color, color: t.text_color, minHeight: 80 }}>
              <div className="absolute -right-4 -top-4 w-20 h-20 rounded-full" style={{ background: "rgba(255,255,255,0.05)" }} />
              <p className="font-mono text-xs mb-1" style={{ opacity: 0.6 }}>•••• •••• 0000</p>
              <p className="font-semibold text-lg">Fiissa Card</p>
              {t.is_default && (
                <span className="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.2)", color: "#fff" }}>Défaut</span>
              )}
            </div>
            <div className="px-4 py-3" style={{ background: "var(--bg-card)" }}>
              <p className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>{t.name}</p>
              <p className="text-xs mt-0.5 font-mono" style={{ color: "var(--tx-muted)" }}>{t.background_color} / {t.text_color}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page principale ──────────────────────────────────────────────────────────

export default function MerchantLoyaltyPage() {
  const [tab, setTab] = useState<Tab>("programmes");

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div className="px-5 pt-4 pb-0 flex items-center gap-3" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <Link href="/merchant/dashboard" style={{ color: "var(--tx-muted)" }}>
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>Fidélité</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>Gérez vos programmes clients</p>
        </div>
        <Link
          href="/merchant/loyalty/coupons"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold"
          style={{ background: "rgba(34,87,255,0.08)", color: "var(--p-500)" }}
        >
          <Tag size={13} /> Coupons
        </Link>
      </div>

      {/* Tabs navigation */}
      <div className="flex gap-0 overflow-x-auto" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className="flex items-center gap-1.5 px-4 py-3.5 text-xs font-bold flex-shrink-0 transition-colors"
            style={{
              color: tab === key ? "var(--p-500)" : "var(--tx-muted)",
              borderBottom: tab === key ? "2px solid var(--p-500)" : "2px solid transparent",
              background: "transparent",
            }}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="px-4 py-4">
        {tab === "programmes" && <ProgramsTab />}
        {tab === "niveaux" && <TiersTab />}
        {tab === "recompenses" && <RewardsTab />}
        {tab === "templates" && <TemplatesTab />}
      </div>

      {/* Raccourcis */}
      {tab === "programmes" && (
        <div className="px-4 pb-8 space-y-3">
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <Link href="/merchant/loyalty/intelligence" className="flex items-center px-4 py-4 gap-3 active:opacity-70">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "rgba(34,87,255,0.08)" }}>
                <Users size={18} style={{ color: "var(--p-500)" }} />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>Intelligence clients</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>Segments RFM — VIP, fidèles, à risque…</p>
              </div>
              <ChevronRight size={16} style={{ color: "var(--bd)" }} />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
