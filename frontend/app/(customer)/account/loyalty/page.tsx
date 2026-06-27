"use client";

import Link from "next/link";
import Image from "next/image";
import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BadgePercent,
  Building2,
  Camera,
  ChevronDown,
  ChevronUp,
  Plus,
  QrCode,
  Scan,
  X,
} from "lucide-react";
import { loyaltyApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { toast } from "sonner";
import QRCode from "qrcode";
import { QrScanner } from "@/components/ui/qr-scanner";
import LoyaltyCard from "@/components/loyalty/loyalty-card";

// ── Scanner carte physique Fiissa ────────────────────────────────────────────

function ScanFiissaSheet({ onClose }: { onClose: () => void }) {
  const [scanned, setScanned] = useState(false);
  const queryClient = useQueryClient();

  const scanMutation = useMutation({
    mutationFn: (cardNumber: string) =>
      loyaltyApi.scanCard(cardNumber).then((r) => r.data),
    onSuccess: () => {
      toast.success("Carte physique liée à votre compte");
      queryClient.invalidateQueries({ queryKey: ["my-loyalty-cards"] });
      onClose();
    },
    onError: (e: any) => {
      setScanned(false);
      if (e.response?.status === 409) {
        toast.error("Cette carte est déjà liée à un autre compte");
      } else {
        toast.error(e.response?.data?.detail || "Erreur de lecture de carte");
      }
    },
  });

  return (
    <QrScanner
      onScan={(value) => {
        if (scanned || scanMutation.isPending) return;
        setScanned(true);
        scanMutation.mutate(value);
      }}
      onClose={onClose}
    />
  );
}

// ── Import externe (formulaire) ──────────────────────────────────────────────

function ImportCardSheet({
  onClose,
  customerId,
}: {
  onClose: () => void;
  customerId: string;
}) {
  const [issuer, setIssuer] = useState("");
  const [ref, setRef] = useState("");
  const [showScanner, setShowScanner] = useState(false);
  const queryClient = useQueryClient();

  const importMutation = useMutation({
    mutationFn: () =>
      loyaltyApi.importExternalCard({
        customer_id: customerId,
        external_issuer: issuer.trim(),
        external_ref: ref.trim(),
      }),
    onSuccess: () => {
      toast.success("Carte importée — elle apparaît maintenant dans votre wallet");
      queryClient.invalidateQueries({ queryKey: ["my-loyalty-cards"] });
      onClose();
    },
    onError: (e: any) =>
      toast.error(e.response?.data?.detail || "Erreur lors de l'import"),
  });

  if (showScanner) {
    return (
      <QrScanner
        onScan={(value) => {
          setRef(value);
          setShowScanner(false);
          toast.success("Code scanné — vérifiez et confirmez");
        }}
        onClose={() => setShowScanner(false)}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-end">
      <div
        className="w-full rounded-t-3xl p-6 space-y-4 max-h-[90vh] overflow-y-auto"
        style={{ background: "var(--bg-card)" }}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold" style={{ color: "var(--tx-head)" }}>
            Importer une carte externe
          </h3>
          <button onClick={onClose} aria-label="Fermer" style={{ color: "var(--tx-muted)" }}>
            <X size={22} />
          </button>
        </div>

        <p className="text-sm leading-relaxed" style={{ color: "var(--tx-muted)" }}>
          Ajoutez une carte de fidélité d'un autre commerce. Elle sera stockée dans votre wallet
          Fiissa mais ne génère pas de points Fiissa.
        </p>

        <div>
          <label className="text-xs font-semibold mb-1.5 block" style={{ color: "var(--tx-muted)" }}>
            Nom de l'enseigne
          </label>
          <input
            value={issuer}
            onChange={(e) => setIssuer(e.target.value)}
            placeholder="Ex : Auchan, Casino, Total"
            className="input-mobile"
          />
        </div>

        <div>
          <label className="text-xs font-semibold mb-1.5 block" style={{ color: "var(--tx-muted)" }}>
            Numéro ou référence de la carte
          </label>
          <div className="flex gap-2">
            <input
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              placeholder="Ex : 6012 3456 7890"
              className="input-mobile flex-1"
            />
            <button
              onClick={() => setShowScanner(true)}
              className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: "rgba(34,87,255,0.08)", border: "1px solid var(--bd)" }}
              aria-label="Scanner avec la caméra"
              title="Scanner QR / code-barres"
            >
              <Camera size={20} style={{ color: "var(--p-500)" }} />
            </button>
          </div>
          <p className="text-[11px] mt-1.5" style={{ color: "var(--tx-muted)" }}>
            Ou scannez le QR code / code-barres avec la caméra
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 rounded-xl font-semibold text-sm"
            style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}
          >
            Annuler
          </button>
          <button
            onClick={() => importMutation.mutate()}
            disabled={!issuer.trim() || !ref.trim() || importMutation.isPending}
            className="flex-1 py-3 rounded-xl font-bold text-sm text-white disabled:opacity-50"
            style={{ background: "var(--p-500)" }}
          >
            {importMutation.isPending ? "Import…" : "Importer"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page principale ──────────────────────────────────────────────────────────

export default function LoyaltyPage() {
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);
  const [qrCache, setQrCache] = useState<Record<string, string>>({});
  const [showImport, setShowImport] = useState(false);
  const [showScanFiissa, setShowScanFiissa] = useState(false);
  const { user } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ["my-loyalty-cards"],
    queryFn: () => loyaltyApi.getMyCards().then((r) => r.data),
  });

  const { data: transactions, isFetching: txLoading } = useQuery({
    queryKey: ["card-transactions", expandedCardId],
    queryFn: () =>
      expandedCardId
        ? loyaltyApi.getCardTransactions(expandedCardId).then((r) => r.data)
        : Promise.resolve([]),
    enabled: !!expandedCardId,
  });

  const handleExpand = useCallback(
    async (card: any) => {
      const isExpanding = expandedCardId !== card.id;
      setExpandedCardId(isExpanding ? card.id : null);
      if (isExpanding && !qrCache[card.card_number]) {
        try {
          const url = await QRCode.toDataURL(card.card_number, {
            width: 180,
            margin: 1,
            color: { dark: "#0F172A", light: "#FFFFFF" },
          });
          setQrCache((prev) => ({ ...prev, [card.card_number]: url }));
        } catch (_) {}
      }
    },
    [expandedCardId, qrCache]
  );

  const cards: any[] = data ?? [];
  const nativeCards = cards.filter((c) => c.card_type === "native");
  const externalCards = cards.filter((c) => c.card_type !== "native");

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      {/* Header */}
      <div
        className="px-5 pt-4 pb-4 flex items-center gap-3"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}
      >
        <Link href="/account" style={{ color: "var(--tx-muted)" }}>
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>
            Fidélité
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
            {cards.length > 0 ? `${cards.length} carte${cards.length > 1 ? "s" : ""}` : "Cartes et points"}
          </p>
        </div>
        <button
          onClick={() => setShowScanFiissa(true)}
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: "var(--n-100)", color: "var(--tx-head)" }}
          aria-label="Scanner une carte physique Fiissa"
          title="Scanner une carte physique Fiissa"
        >
          <Scan size={18} />
        </button>
        <button
          onClick={() => setShowImport(true)}
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: "var(--p-500)", color: "#fff" }}
          aria-label="Importer une carte externe"
          title="Importer une carte externe"
        >
          <Plus size={18} />
        </button>
      </div>

      <div className="px-4 py-4 space-y-5">
        {isLoading && (
          <div className="space-y-3">
            <div className="skeleton h-44 w-full rounded-3xl" />
            <div className="skeleton h-44 w-full rounded-3xl" />
          </div>
        )}

        {/* Cartes natives (commerçants Fiissa) */}
        {nativeCards.length > 0 && (
          <section>
            <p className="text-xs font-bold uppercase tracking-wide mb-3" style={{ color: "var(--tx-muted)" }}>
              Programmes Fiissa ({nativeCards.length})
            </p>
            <div className="space-y-3">
              {nativeCards.map((card) => (
                <div key={card.id} className="space-y-1">
                  <LoyaltyCard
                    customerName={user?.firstName + " " + user?.lastName || "Client"}
                    companyName={card.company_name || "Fiissa"}
                    points={card.points_balance}
                    cardNumber={card.card_number}
                    tierName={card.tier_name}
                    backgroundColor={card.background_color}
                    textColor={card.text_color}
                    logoUrl={card.logo_url}
                    isActive={card.status === "active"}
                  />
                  <CardActions card={card} isExpanded={expandedCardId === card.id} onExpand={() => handleExpand(card)} />
                  {expandedCardId === card.id && (
                     <CardDetails
                      card={card}
                      qrDataUrl={qrCache[card.card_number]}
                      transactions={transactions}
                      txLoading={txLoading}
                    />
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Cartes externes */}
        {externalCards.length > 0 && (
          <section>
            <p className="text-xs font-bold uppercase tracking-wide mb-3" style={{ color: "var(--tx-muted)" }}>
              Cartes externes ({externalCards.length})
            </p>
            <div className="space-y-3">
              {externalCards.map((card) => (
                 <div key={card.id} className="space-y-1">
                  <LoyaltyCard
                    customerName={user?.firstName + " " + user?.lastName || "Client"}
                    companyName={card.external_issuer || "Externe"}
                    points={0}
                    cardNumber={card.card_number}
                    backgroundColor={card.background_color}
                    textColor={card.text_color}
                    logoUrl={card.logo_url}
                    isActive={card.status === "active"}
                  />
                  <CardActions card={card} isExpanded={expandedCardId === card.id} onExpand={() => handleExpand(card)} />
                  {expandedCardId === card.id && (
                     <CardDetails
                      card={card}
                      qrDataUrl={qrCache[card.card_number]}
                      transactions={[]}
                      txLoading={false}
                    />
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Empty state */}
        {!isLoading && cards.length === 0 && (
          <div
            className="rounded-2xl p-8 text-center"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: "rgba(34,87,255,0.08)" }}
            >
              <BadgePercent size={32} style={{ color: "var(--p-500)" }} />
            </div>
            <p className="font-bold text-base" style={{ color: "var(--tx-head)" }}>
              Aucune carte de fidélité
            </p>
            <p className="text-sm mt-2 mb-5 leading-relaxed" style={{ color: "var(--tx-muted)" }}>
              Vos cartes Fiissa apparaissent ici après un achat chez un marchand partenaire.
              Importez aussi vos cartes d'autres enseignes.
            </p>
            <button
              onClick={() => setShowImport(true)}
              className="px-6 py-3 rounded-2xl font-bold text-sm text-white"
              style={{ background: "var(--p-500)" }}
            >
              Importer une carte externe
            </button>
          </div>
        )}

        {/* Lien raccourci import si cards > 0 */}
        {!isLoading && cards.length > 0 && (
          <button
            onClick={() => setShowImport(true)}
            className="w-full rounded-2xl p-4 flex items-center gap-3 active:opacity-70"
            style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
          >
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: "rgba(34,87,255,0.08)" }}
            >
              <Building2 size={18} style={{ color: "var(--p-500)" }} />
            </div>
            <div className="flex-1 text-left">
              <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>
                Importer une carte externe
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                QR code, code-barres ou saisie manuelle
              </p>
            </div>
            <Camera size={16} style={{ color: "var(--tx-muted)" }} />
          </button>
        )}
      </div>

      {showScanFiissa && (
        <ScanFiissaSheet onClose={() => setShowScanFiissa(false)} />
      )}

      {showImport && user?.id && (
        <ImportCardSheet customerId={user.id} onClose={() => setShowImport(false)} />
      )}
    </div>
  );
}

// ── Composant carte (extrait pour clarté) ────────────────────────────────────

function CardActions({
  card,
  isExpanded,
  onExpand,
}: {
  card: any;
  isExpanded: boolean;
  onExpand: () => void;
}) {
  return (
    <button
      className="w-full flex items-center justify-center gap-2 py-2 rounded-xl mt-1 transition-colors"
      style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", color: "var(--tx-muted)" }}
      onClick={onExpand}
    >
      <BadgePercent size={16} />
      <span className="text-xs font-semibold">{isExpanded ? "Masquer les détails" : "Voir détails et QR code"}</span>
      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
    </button>
  );
}

function CardDetails({
  card,
  qrDataUrl,
  transactions,
  txLoading,
}: {
  card: any;
  qrDataUrl?: string;
  transactions: any[];
  txLoading: boolean;
}) {
  const isNative = card.card_type === "native";
  return (
    <div
      className="rounded-2xl p-4 mt-1 space-y-4"
      style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
    >
      {/* QR Code */}
      <div className="flex flex-col items-center py-2">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-2" style={{ background: "rgba(34,87,255,0.08)" }}>
          <QrCode size={20} style={{ color: "var(--p-500)" }} />
        </div>
        <p className="text-xs font-semibold mb-3 text-center" style={{ color: "var(--tx-muted)" }}>
          {isNative ? "QR code pour paiement en caisse" : "QR code de la carte"}
        </p>
        {qrDataUrl ? (
          <Image
            src={qrDataUrl}
            alt="QR code fidélité"
            width={160}
            height={160}
            unoptimized
            className="w-40 h-40 rounded-xl"
            style={{ border: "4px solid white", boxShadow: "0 2px 8px rgba(0,0,0,0.15)" }}
          />
        ) : (
          <div className="w-40 h-40 rounded-xl skeleton" />
        )}
      </div>

      {/* Transactions (natives seulement) */}
      {isNative && (
        <div>
          <p className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: "var(--tx-muted)" }}>
            Dernières transactions
          </p>

          {txLoading && <div className="skeleton h-14 w-full rounded-xl" />}

          {!txLoading && transactions.length === 0 && (
            <p className="text-sm text-center py-3" style={{ color: "var(--tx-muted)" }}>
              Aucune transaction pour l'instant
            </p>
          )}

          {!txLoading && transactions.slice(0, 5).map((tx: any, i: number) => (
            <div
              key={tx.id}
              className="flex items-center justify-between py-2.5"
              style={{ borderBottom: i < Math.min(transactions.length, 5) - 1 ? "1px solid var(--bg-app)" : "none" }}
            >
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold truncate" style={{ color: "var(--tx-head)" }}>
                  {tx.description || tx.type}
                </p>
                <p className="text-[10px] mt-0.5" style={{ color: "var(--tx-muted)" }}>
                  {new Date(tx.created_at).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })}
                </p>
              </div>
              <p
                className="font-bold text-sm ml-3 flex-shrink-0"
                style={{ color: tx.points_delta > 0 ? "#00D68F" : "#F87171" }}
              >
                {tx.points_delta > 0 ? "+" : ""}{tx.points_delta} pts
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
