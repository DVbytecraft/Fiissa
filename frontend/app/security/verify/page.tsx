"use client";

import { useState, useEffect, useRef } from "react";
import {
  Bluetooth, CheckCircle2, XCircle, Scale,
} from "lucide-react";
import { receiptsApi } from "@/lib/api";

type Phase = "scan" | "verifying" | "bluetooth" | "weighing" | "pass" | "fail";

/* GATT UUIDs (Weight Scale profile — Bluetooth SIG 0x181D / 0x2A9D) */
const GATT_SERVICE    = "0000181d-0000-1000-8000-00805f9b34fb";
const GATT_CHAR       = "00002a9d-0000-1000-8000-00805f9b34fb";
const BAG_TARE_G      = 50;      // tare sac standard : 50 g
const TOLERANCE       = 0.02;    // ±2 %

/* Parse Weight Measurement characteristic value (Bluetooth SIG spec) */
function parseWeightKg(dv: DataView): number {
  const flags  = dv.getUint8(0);
  const isLbs  = (flags & 0x01) !== 0;
  const raw    = dv.getUint16(1, true);
  // résolution : 0.005 kg (kg) ou 0.01 lb
  return isLbs ? (raw * 0.01 * 0.453592) : raw * 0.005;
}

/* ─────────────────────────────────────────────────────────────── */

export default function SecurityVerifyPage() {
  const [phase,        setPhase]        = useState<Phase>("scan");
  const [code,         setCode]         = useState("");
  const [receiptData,  setReceiptData]  = useState<any>(null);
  const [liveWeight,   setLiveWeight]   = useState<number | null>(null);
  const [errorMsg,     setErrorMsg]     = useState("");
  const charRef = useRef<any>(null);

  /* ── 1. Verify QR ────────────────────────────────────────────── */
  const verifyCode = async (c: string) => {
    if (!c.trim()) return;
    setPhase("verifying");
    setErrorMsg("");
    try {
      const res  = await receiptsApi.verify(c.trim());
      const data = res.data;
      if (!data.valid) {
        setErrorMsg(data.message || "Code invalide ou reçu déjà utilisé");
        setPhase("scan");
        return;
      }
      setReceiptData(data);
      setPhase("bluetooth");
    } catch (e: any) {
      setErrorMsg(e.response?.status === 404 ? "Code introuvable" : "Erreur réseau");
      setPhase("scan");
    }
  };

  /* ── 2. Connect Bluetooth scale ──────────────────────────────── */
  const connectScale = async () => {
    setErrorMsg("");
    const bt = (navigator as any).bluetooth;
    if (!bt) {
      setErrorMsg("Web Bluetooth non supporté sur ce navigateur (utilisez Chrome/Edge)");
      return;
    }
    try {
      const device: any = await bt.requestDevice({
        filters:          [{ services: [GATT_SERVICE] }],
        optionalServices: [GATT_SERVICE],
      });
      const server  = await device.gatt.connect();
      const service = await server.getPrimaryService(GATT_SERVICE);
      const char    = await service.getCharacteristic(GATT_CHAR);
      charRef.current = char;
      await char.startNotifications();
      char.addEventListener("characteristicvaluechanged", (e: any) => {
        setLiveWeight(parseWeightKg(e.target.value as DataView));
      });
      /* Lire la valeur initiale si disponible */
      try {
        const initial = await char.readValue();
        setLiveWeight(parseWeightKg(initial));
      } catch {}
      setPhase("weighing");
    } catch (e: any) {
      if (e.name !== "NotFoundError" && e.name !== "NotAllowedError") {
        setErrorMsg("Connexion balance échouée — vérifiez l'appairage Bluetooth.");
      }
    }
  };

  /* ── 3. Validate weight ──────────────────────────────────────── */
  const validateWeight = () => {
    const theoreticalG = receiptData?.total_weight_g ?? 0;
    if (theoreticalG === 0) {
      /* Poids théorique absent du backend → validation directe */
      setPhase("pass");
      return;
    }
    const expectedG  = theoreticalG + BAG_TARE_G;
    const realG      = (liveWeight ?? 0) * 1000;
    const withinTol  = Math.abs(realG - expectedG) / expectedG <= TOLERANCE;
    setPhase(withinTol ? "pass" : "fail");
  };

  /* ── Skip scale (validation sans pesée) ─────────────────────── */
  const skipScale = () => setPhase("pass");

  /* ── Reset ──────────────────────────────────────────────────── */
  const reset = () => {
    try { charRef.current?.stopNotifications(); } catch {}
    charRef.current = null;
    setPhase("scan");
    setCode("");
    setReceiptData(null);
    setLiveWeight(null);
    setErrorMsg("");
  };

  /* Auto-fill depuis l'URL (?code=XXXX) */
  useEffect(() => {
    const c = new URLSearchParams(window.location.search).get("code");
    if (c) { setCode(c); verifyCode(c); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ════════════════════════════════════════════════════════════
     ÉCRAN VERT — SORTIE VALIDÉE (plein écran)
  ════════════════════════════════════════════════════════════ */
  if (phase === "pass") {
    return (
      <div
        className="fixed inset-0 flex flex-col items-center justify-center gap-6 px-8 text-center"
        style={{ background: "#10B981" }}
      >
        <CheckCircle2 size={96} strokeWidth={1.2} className="text-white" />
        <div>
          <p className="text-white font-semibold leading-none" style={{ fontSize: 52 }}>SORTIE</p>
          <p className="text-white font-semibold leading-none mt-1" style={{ fontSize: 52 }}>VALIDÉE</p>
        </div>
        {receiptData?.receipt_number && (
          <p className="text-white/60 text-sm font-mono tracking-widest">{receiptData.receipt_number}</p>
        )}
        {receiptData?.amount_xof && (
          <p className="text-white/80 text-lg font-bold">
            {receiptData.amount_xof.toLocaleString("fr-FR")} FCFA
          </p>
        )}
        <button
          onClick={reset}
          className="mt-4 bg-white rounded-3xl px-10 py-4 font-semibold text-xl active:scale-95 transition-transform"
          style={{ color: "#10B981" }}
        >
          Contrôle suivant
        </button>
      </div>
    );
  }

  /* ════════════════════════════════════════════════════════════
     ÉCRAN ROUGE — ÉCART DÉTECTÉ (plein écran)
  ════════════════════════════════════════════════════════════ */
  if (phase === "fail") {
    const items: any[]   = receiptData?.items ?? [];
    const theoreticalG   = receiptData?.total_weight_g ?? 0;
    const expectedG      = theoreticalG + BAG_TARE_G;
    const realG          = liveWeight !== null ? Math.round(liveWeight * 1000) : null;

    return (
      <div className="fixed inset-0 overflow-auto" style={{ background: "#EF4444" }}>
        <div className="px-6 pt-14 pb-10 flex flex-col gap-5 min-h-full">

          {/* Titre */}
          <div className="text-center">
            <XCircle size={80} strokeWidth={1.2} className="text-white mx-auto mb-4" />
            <p className="text-white font-semibold tracking-tight" style={{ fontSize: 42 }}>
              ÉCART DÉTECTÉ
            </p>
          </div>

          {/* Tableau poids */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl py-4 px-4 text-center" style={{ background: "rgba(0,0,0,0.18)" }}>
              <p className="text-white/60 text-xs mb-1 uppercase tracking-wider">Balance</p>
              <p className="text-white font-semibold text-2xl">{realG !== null ? `${realG} g` : "—"}</p>
            </div>
            <div className="rounded-2xl py-4 px-4 text-center" style={{ background: "rgba(0,0,0,0.18)" }}>
              <p className="text-white/60 text-xs mb-1 uppercase tracking-wider">Attendu ±2%</p>
              <p className="text-white font-semibold text-2xl">{expectedG} g</p>
            </div>
          </div>

          {/* Liste articles — contrôle visuel */}
          <div className="rounded-2xl overflow-hidden flex-1" style={{ background: "rgba(0,0,0,0.20)" }}>
            <p
              className="px-4 py-3 text-white font-semibold text-xs uppercase tracking-widest"
              style={{ borderBottom: "1px solid rgba(255,255,255,0.12)" }}
            >
              Articles payés · contrôle visuel
            </p>
            {items.length === 0 && (
              <p className="px-4 py-6 text-white/50 text-sm text-center">Détails non disponibles</p>
            )}
            {items.map((item: any, i: number) => (
              <div
                key={i}
                className="flex items-center justify-between px-4 py-3.5"
                style={{ borderBottom: i < items.length - 1 ? "1px solid rgba(255,255,255,0.09)" : "none" }}
              >
                <p className="text-white font-bold text-sm flex-1 pr-3">
                  {item.name ?? item.product_name ?? "Article"}
                </p>
                <div className="flex items-center gap-3 flex-shrink-0">
                  {item.weight_g && (
                    <span className="text-white/50 text-xs">
                      {(item.weight_g * (item.quantity ?? 1))} g
                    </span>
                  )}
                  <span className="text-white/80 text-sm font-mono">×{item.quantity ?? 1}</span>
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={reset}
            className="w-full rounded-2xl py-4 font-semibold text-white text-lg active:scale-95 transition-transform"
            style={{ background: "rgba(0,0,0,0.28)", border: "1px solid rgba(255,255,255,0.22)" }}
          >
            Contrôle suivant
          </button>
        </div>
      </div>
    );
  }

  /* ════════════════════════════════════════════════════════════
     INTERFACE PRINCIPALE
  ════════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen pb-28" style={{ background: "#0F1629" }}>

      {/* Bandeau erreur */}
      {errorMsg && (
        <div
          className="mx-4 mt-4 rounded-2xl px-4 py-3"
          style={{ background: "rgba(239,68,68,0.18)", border: "1px solid rgba(239,68,68,0.3)" }}
        >
          <p className="text-red-300 text-sm font-bold">{errorMsg}</p>
        </div>
      )}

      {/* ── SCAN ── */}
      {phase === "scan" && (
        <div className="px-4 pt-2">
          <div className="rounded-3xl p-6" style={{ background: "rgba(255,255,255,0.06)" }}>
            <p className="text-white text-center text-sm mb-5" style={{ opacity: 0.65 }}>
              Entrez le code QR du reçu client
            </p>
            <form onSubmit={(e) => { e.preventDefault(); verifyCode(code); }} className="space-y-4">
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="CODE DE VÉRIFICATION"
                className="w-full py-5 px-4 text-center text-xl font-mono bg-white rounded-2xl outline-none tracking-widest"
                style={{ color: "#0F1629" }}
                autoFocus
                autoComplete="off"
                autoCapitalize="characters"
              />
              <button
                type="submit"
                disabled={!code.trim()}
                className="w-full py-5 rounded-2xl font-semibold text-xl text-white disabled:opacity-40 active:scale-95 transition-transform"
                style={{ background: "#FF9F00" }}
              >
                VÉRIFIER
              </button>
            </form>
          </div>
        </div>
      )}

      {/* ── VERIFYING ── */}
      {phase === "verifying" && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div
            className="w-16 h-16 border-4 rounded-full animate-spin"
            style={{ borderColor: "rgba(255,159,0,0.25)", borderTopColor: "#FF9F00" }}
          />
          <p className="text-white text-lg font-semibold">Vérification du reçu…</p>
        </div>
      )}

      {/* ── BLUETOOTH ── */}
      {phase === "bluetooth" && (
        <div className="px-4 space-y-4 pt-2">
          {/* Reçu valide */}
          <div
            className="rounded-2xl px-4 py-3 flex items-center gap-3"
            style={{ background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)" }}
          >
            <CheckCircle2 size={18} style={{ color: "#10B981" }} />
            <div className="min-w-0">
              <p className="text-white font-bold text-sm">Reçu valide</p>
              {receiptData?.receipt_number && (
                <p className="text-white/50 text-xs font-mono truncate">{receiptData.receipt_number}</p>
              )}
            </div>
            {receiptData?.amount_xof && (
              <p className="text-white font-semibold ml-auto flex-shrink-0">
                {receiptData.amount_xof.toLocaleString("fr-FR")} F
              </p>
            )}
          </div>

          {/* Connexion balance */}
          <div className="rounded-3xl p-7 text-center" style={{ background: "rgba(255,255,255,0.06)" }}>
            <Bluetooth size={52} className="mx-auto mb-4" style={{ color: "#2257FF" }} />
            <p className="text-white font-bold text-lg mb-1">Connecter la balance</p>
            <p className="text-white/50 text-sm mb-6">
              Appairez la balance électronique du magasin via Bluetooth GATT
            </p>
            <button
              onClick={connectScale}
              className="w-full py-4 rounded-2xl font-semibold text-white text-lg mb-3 active:scale-95 transition-transform flex items-center justify-center gap-2"
              style={{ background: "#2257FF" }}
            >
              <Bluetooth size={20} />
              Connecter la balance
            </button>
            <button
              onClick={skipScale}
              className="w-full py-3 rounded-xl text-sm font-bold"
              style={{ color: "rgba(255,255,255,0.35)" }}
            >
              Passer la pesée (validation directe)
            </button>
          </div>
        </div>
      )}

      {/* ── WEIGHING ── */}
      {phase === "weighing" && (
        <div className="px-4 space-y-4 pt-2">
          {/* Affichage poids en direct */}
          <div className="rounded-3xl p-8 text-center" style={{ background: "rgba(255,255,255,0.06)" }}>
            <Scale size={40} className="mx-auto mb-4" style={{ color: "#FF9F00", opacity: 0.75 }} />
            <p className="text-white/50 text-xs mb-2 uppercase tracking-widest">Poids mesuré</p>
            <p
              className="text-white font-semibold leading-none"
              style={{ fontSize: 72 }}
            >
              {liveWeight !== null ? Math.round(liveWeight * 1000) : "—"}
            </p>
            <p className="text-white/50 text-xl font-bold mt-2">grammes</p>
          </div>

          {/* Référence backend */}
          {receiptData?.total_weight_g ? (
            <div
              className="rounded-2xl px-4 py-3 grid grid-cols-2 gap-2 text-center"
              style={{ background: "rgba(255,255,255,0.04)" }}
            >
              <div>
                <p className="text-white/40 text-xs mb-0.5">Panier théorique</p>
                <p className="text-white font-bold">{receiptData.total_weight_g} g</p>
              </div>
              <div>
                <p className="text-white/40 text-xs mb-0.5">Attendu + sac (±2%)</p>
                <p className="text-white font-bold">{receiptData.total_weight_g + BAG_TARE_G} g</p>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl px-4 py-3 text-center" style={{ background: "rgba(255,255,255,0.04)" }}>
              <p className="text-white/40 text-xs">Poids théorique non communiqué — validation directe disponible</p>
            </div>
          )}

          <button
            onClick={validateWeight}
            disabled={liveWeight === null}
            className="w-full py-5 rounded-2xl font-semibold text-white text-xl disabled:opacity-40 active:scale-95 transition-transform"
            style={{ background: "#FF9F00" }}
          >
            VALIDER LE POIDS
          </button>
        </div>
      )}

      {/* Légende fixe en bas */}
      {(phase === "scan" || phase === "bluetooth" || phase === "weighing") && (
        <div className="fixed bottom-8 left-4 right-4">
          <div
            className="rounded-2xl p-3 grid grid-cols-2 gap-2 text-xs"
            style={{ background: "rgba(255,255,255,0.05)" }}
          >
            <div className="flex items-center gap-2" style={{ color: "rgba(255,255,255,0.4)" }}>
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#10B981" }} />Conforme
            </div>
            <div className="flex items-center gap-2" style={{ color: "rgba(255,255,255,0.4)" }}>
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#EF4444" }} />Écart détecté
            </div>
            <div className="flex items-center gap-2" style={{ color: "rgba(255,255,255,0.4)" }}>
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#2257FF" }} />Balance connectée
            </div>
            <div className="flex items-center gap-2" style={{ color: "rgba(255,255,255,0.4)" }}>
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#6B7280" }} />Hors ligne
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
