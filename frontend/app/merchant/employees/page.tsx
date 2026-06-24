"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UserPlus, Trash2, User, X } from "lucide-react";
import { authApi } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmModal } from "@/components/ui/confirm-modal";

const ROLE_LABELS: Record<string, { label: string; bg: string; color: string }> = {
  company_owner: { label: "Propriétaire", bg: "rgba(124,58,237,0.08)", color: "#7C3AED" },
  store_manager: { label: "Gérant", bg: "rgba(34,87,255,0.08)", color: "var(--p-500)" },
  cashier: { label: "Caissier", bg: "rgba(245,158,11,0.08)", color: "#F59E0B" },
  accountant: { label: "Comptable", bg: "rgba(0,214,143,0.1)", color: "var(--s-500)" },
  preparer: { label: "Préparateur", bg: "rgba(245,158,11,0.08)", color: "#F59E0B" },
  security_agent: { label: "Agent sécurité", bg: "rgba(110,122,138,0.08)", color: "var(--tx-muted)" },
  support_agent: { label: "Support", bg: "rgba(236,72,153,0.08)", color: "#EC4899" },
};

function CreateEmployeeModal({ onClose }: { onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("preparer");
  const queryClient = useQueryClient();

  const inviteMutation = useMutation({
    mutationFn: () =>
      authApi.inviteStaff({
        email,
        first_name: firstName,
        last_name: lastName,
        role,
      }),
    onSuccess: () => {
      toast.success("Compte créé — un email avec les identifiants a été envoyé.");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur lors de la création"),
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end">
      <div
        style={{ background: "var(--bg-card)" }}
        className="rounded-t-3xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 style={{ color: "var(--tx-head)" }} className="text-xl font-black">
              Ajouter un employé
            </h3>
            <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
              Le compte est créé immédiatement. Les identifiants sont envoyés par email.
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full"
            style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
            aria-label="Fermer"
          >
            <X size={16} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
              Prénom
            </label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="Ibrahima"
              className="input-mobile py-3"
            />
          </div>
          <div>
            <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
              Nom
            </label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Diallo"
              className="input-mobile py-3"
            />
          </div>
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Email professionnel
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="ibrahima@boutique.sn"
            className="input-mobile"
          />
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Rôle
          </label>
          <select value={role} onChange={(e) => setRole(e.target.value)} className="input-mobile">
            {Object.entries(ROLE_LABELS).map(([val, { label }]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}
            className="flex-1 py-3 rounded-xl font-semibold"
          >
            Annuler
          </button>
          <button
            onClick={() => inviteMutation.mutate()}
            disabled={!email || !firstName || inviteMutation.isPending}
            style={{ background: "var(--p-500)" }}
            className="flex-1 py-3 text-white rounded-xl font-bold disabled:opacity-50"
          >
            {inviteMutation.isPending ? "Création…" : "Créer le compte"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MerchantEmployeesPage() {
  const [showInvite, setShowInvite] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<{ id: string; name: string } | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["employees"],
    queryFn: () => authApi.getStaff().then((r) => r.data),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => authApi.removeStaff(userId),
    onSuccess: () => {
      toast.success("Accès révoqué");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Erreur lors de la révocation"),
  });

  const handleConfirmRemove = () => {
    if (!confirmTarget) return;
    removeMutation.mutate(confirmTarget.id);
    setConfirmTarget(null);
  };

  const employees: any[] = data?.items ?? [];

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      <div
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
        className="px-5 pt-6 pb-5"
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <User size={15} style={{ color: "var(--p-500)" }} />
              <span className="text-xs font-black uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>Gestion</span>
            </div>
            <h1 style={{ color: "var(--tx-head)" }} className="text-2xl font-black">
              Équipe
            </h1>
            <p style={{ color: "var(--tx-muted)" }} className="text-sm mt-0.5">
              {employees.length} membre{employees.length > 1 ? "s" : ""} actif{employees.length > 1 ? "s" : ""}
            </p>
          </div>
          <button
            onClick={() => setShowInvite(true)}
            style={{ background: "var(--p-500)", boxShadow: "var(--sh-brand)" }}
            className="flex items-center gap-2 px-4 py-2.5 text-white rounded-2xl text-sm font-bold active:scale-95 transition-transform"
          >
            <UserPlus size={16} />
            Ajouter
          </button>
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        {isLoading &&
          [...Array(3)].map((_, i) => (
            <div key={i} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
              <div className="skeleton h-16 w-full" />
            </div>
          ))}

        {employees.map((emp: any) => {
          const roleInfo = ROLE_LABELS[emp.role] ?? {
            label: emp.role,
            bg: "rgba(110,122,138,0.08)",
            color: "var(--tx-muted)",
          };
          return (
            <div
              key={emp.id}
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              className="rounded-2xl p-4"
            >
              <div className="flex items-center gap-3">
                <div
                  style={{ background: "rgba(34,87,255,0.08)" }}
                  className="w-12 h-12 rounded-full flex items-center justify-center shrink-0"
                >
                  <User size={22} style={{ color: "var(--p-500)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p style={{ color: "var(--tx-head)" }} className="font-bold text-sm">
                    {emp.first_name} {emp.last_name}
                  </p>
                  <p style={{ color: "var(--tx-muted)" }} className="text-xs">
                    {emp.email}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span
                      style={{ background: roleInfo.bg, color: roleInfo.color }}
                      className="text-xs font-medium px-2 py-0.5 rounded-full"
                    >
                      {roleInfo.label}
                    </span>
                    {!emp.is_active && (
                      <span className="text-xs font-medium" style={{ color: "#DC2626" }}>Inactif</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setConfirmTarget({ id: emp.id, name: emp.first_name })}
                  className="p-2 rounded-lg"
                  style={{ color: "#DC2626", background: "#FEF2F2" }}
                  aria-label={`Révoquer l'accès de ${emp.first_name}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          );
        })}

        {!isLoading && employees.length === 0 && (
          <div className="text-center py-16">
            <User size={64} style={{ color: "var(--bd)" }} className="mx-auto mb-4" />
            <p style={{ color: "var(--tx-muted)" }} className="font-medium">
              Aucun employé
            </p>
            <button
              onClick={() => setShowInvite(true)}
              className="mt-4 btn-primary max-w-xs mx-auto"
            >
              Créer le premier employé
            </button>
          </div>
        )}
      </div>

      {showInvite && <CreateEmployeeModal onClose={() => setShowInvite(false)} />}

      <ConfirmModal
        open={!!confirmTarget}
        title="Révoquer l'accès"
        message={`Êtes-vous sûr de vouloir révoquer l'accès de ${confirmTarget?.name} ? Cette action est immédiate.`}
        confirmLabel="Révoquer"
        variant="danger"
        onConfirm={handleConfirmRemove}
        onCancel={() => setConfirmTarget(null)}
      />
    </div>
  );
}
