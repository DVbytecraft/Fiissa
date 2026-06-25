"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  ScanLine, Minus, Plus, Trash2,
  ChevronLeft, CameraOff,
} from "lucide-react";
import { catalogApi, ordersApi } from "@/lib/api";
import { toast } from "sonner";

interface ScannedItem {
  productId:   string;
  productName: string;
  barcode:     string;
  unitPrice:   number;
  quantity:    number;
  imageUrl?:   string;
}

export default function ScanGoPage() {
  const router          = useRouter();
  const videoRef        = useRef<HTMLVideoElement>(null);
  const streamRef       = useRef<MediaStream | null>(null);
  const detectorRef     = useRef<any>(null);
  const scanIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastScannedRef  = useRef<string>("");

  const [isScanning,  setIsScanning]  = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [items,       setItems]       = useState<ScannedItem[]>([]);
  const [lookupCode,  setLookupCode]  = useState("");
  const [storeId,     setStoreId]     = useState("");
  const [submitting,  setSubmitting]  = useState(false);

  const total     = items.reduce((s, i) => s + i.unitPrice * i.quantity, 0);
  const itemCount = items.reduce((s, i) => s + i.quantity, 0);

  /* ── Lookup produit par code-barres ── */
  const lookupMutation = useMutation({
    mutationFn: (barcode: string) =>
      catalogApi.getByBarcode(barcode, storeId || undefined).then((r) => r.data),
    onSuccess: (product, barcode) => {
      lastScannedRef.current = barcode;
      setItems((prev) => {
        const ex = prev.find((i) => i.productId === product.id);
        if (ex) {
          toast.success(`${product.name} ×${ex.quantity + 1}`, { duration: 900 });
          return prev.map((i) => i.productId === product.id ? { ...i, quantity: i.quantity + 1 } : i);
        }
        toast.success(product.name, { duration: 900 });
        return [...prev, {
          productId:   product.id,
          productName: product.name,
          barcode,
          unitPrice:   product.price_xof,
          quantity:    1,
          imageUrl:    product.image_url,
        }];
      });
    },
    onError: (e: any, barcode) => {
      lastScannedRef.current = barcode;
      if (e.response?.status === 404) toast.error(`Code ${barcode} inconnu`);
      else toast.error("Erreur réseau");
    },
  });

  /* ── Caméra ── */
  const startCamera = useCallback(async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      if ("BarcodeDetector" in window) {
        detectorRef.current = new (window as any).BarcodeDetector({
          formats: ["ean_13", "ean_8", "qr_code", "code_128", "code_39", "upc_a", "upc_e"],
        });
        scanIntervalRef.current = setInterval(async () => {
          if (!videoRef.current || !detectorRef.current || lookupMutation.isPending) return;
          try {
            const barcodes = await detectorRef.current.detect(videoRef.current);
            if (barcodes.length > 0) {
              const code = barcodes[0].rawValue;
              if (code !== lastScannedRef.current) lookupMutation.mutate(code);
            }
          } catch {}
        }, 700);
      } else {
        setCameraError("Scanner non supporté — utilisez la saisie manuelle ci-dessous.");
      }
      setIsScanning(true);
    } catch (err: any) {
      if (err.name === "NotAllowedError")
        setCameraError("Accès caméra refusé — autorisez-le dans les paramètres.");
      else
        setCameraError("Impossible d'accéder à la caméra.");
    }
  }, [lookupMutation]);

  const stopCamera = useCallback(() => {
    if (scanIntervalRef.current) { clearInterval(scanIntervalRef.current); scanIntervalRef.current = null; }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setIsScanning(false);
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem("scan_go_store_id");
    if (saved) setStoreId(saved);
    return () => stopCamera();
  }, [stopCamera]);

  /* ── Quantité ── */
  const updateQty = (productId: string, delta: number) =>
    setItems((prev) =>
      prev.map((i) => i.productId === productId ? { ...i, quantity: i.quantity + delta } : i)
          .filter((i) => i.quantity > 0)
    );

  /* ── Validation commande ── */
  const handleCheckout = async () => {
    if (!items.length || submitting) return;
    setSubmitting(true);
    try {
      const res = await ordersApi.createScanGoOrder({
        store_id:   storeId,
        order_type: "scan_go",
        items:      items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
      });
      stopCamera();
      router.push(`/payment/${res.data.id}`);
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Erreur création commande");
      setSubmitting(false);
    }
  };

  const handleManualBarcode = (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupCode.trim() || lookupMutation.isPending) return;
    lookupMutation.mutate(lookupCode.trim());
    setLookupCode("");
  };

  /* ═══════════════════════════════════════════
     RENDU
  ═══════════════════════════════════════════ */
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#0A0A0F" }}>

      {/* ── Header ── */}
      <div className="flex items-center gap-3 px-5 pt-12 pb-4">
        <button
          onClick={() => { stopCamera(); router.back(); }}
          className="w-9 h-9 flex items-center justify-center rounded-full flex-shrink-0 transition-colors active:bg-white/10"
          style={{ background: "rgba(255,255,255,0.07)" }}
        >
          <ChevronLeft size={18} className="text-white" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-white font-bold text-base leading-tight">Scan & Go</h1>
          <p className="text-white/40 text-xs mt-0.5 font-medium">Scannez vos articles · payez à la sortie</p>
        </div>
        {itemCount > 0 && (
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full flex-shrink-0"
            style={{ background: "var(--p-500)" }}
          >
            <ScanLine size={13} className="text-white" strokeWidth={1.8} />
            <span className="text-white text-xs font-bold">{itemCount}</span>
          </div>
        )}
      </div>

      {/* ── Zone caméra ── */}
      <div
        className="relative mx-4 overflow-hidden"
        style={{ borderRadius: 20, aspectRatio: "4/3", background: "#000" }}
      >
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="w-full h-full object-cover"
          style={{ opacity: isScanning ? 1 : 0 }}
        />

        {/* Viseur ultra-fin 1px blanc */}
        {isScanning && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            {/* Overlay sombre autour du cadre */}
            <div className="absolute inset-0" style={{ background: "rgba(0,0,0,0.35)" }} />
            <div
              className="relative z-10"
              style={{ width: 220, height: 140 }}
            >
              {/* Zone transparente au centre */}
              <div
                className="absolute inset-0"
                style={{ boxShadow: "0 0 0 9999px rgba(0,0,0,0.35)", borderRadius: 4 }}
              />
              {/* Coins 1px */}
              <div className="absolute top-0 left-0 w-8 h-8 border-t border-l border-white" style={{ borderRadius: "3px 0 0 0" }} />
              <div className="absolute top-0 right-0 w-8 h-8 border-t border-r border-white" style={{ borderRadius: "0 3px 0 0" }} />
              <div className="absolute bottom-0 left-0 w-8 h-8 border-b border-l border-white" style={{ borderRadius: "0 0 0 3px" }} />
              <div className="absolute bottom-0 right-0 w-8 h-8 border-b border-r border-white" style={{ borderRadius: "0 0 3px 0" }} />
              {/* Ligne de scan fine 1px */}
              <div
                className="absolute inset-x-8 top-1/2 -translate-y-1/2"
                style={{ height: 1, background: "rgba(255,255,255,0.60)", animation: "pulse 1.4s ease-in-out infinite" }}
              />
            </div>
            {/* Spinner lookup */}
            {lookupMutation.isPending && (
              <div
                className="absolute top-3 right-3 w-6 h-6 rounded-full border border-t-transparent animate-spin"
                style={{ borderColor: "rgba(255,255,255,0.5) transparent transparent transparent" }}
              />
            )}
          </div>
        )}

        {/* Idle state */}
        {!isScanning && !cameraError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: "rgba(255,255,255,0.06)" }}>
              <ScanLine size={28} className="text-white/30" strokeWidth={1.2} />
            </div>
            <p className="text-white/30 text-xs font-medium">Caméra inactive</p>
          </div>
        )}

        {/* Erreur caméra */}
        {cameraError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center px-8 gap-3">
            <CameraOff size={28} className="text-white/30" strokeWidth={1.2} />
            <p className="text-white/50 text-sm text-center leading-relaxed">{cameraError}</p>
          </div>
        )}
      </div>

      {/* ── Bouton Démarrer / Arrêter ── */}
      <div className="px-4 mt-3">
        {!isScanning ? (
          <button
            onClick={startCamera}
            className="w-full py-3.5 rounded-xl font-semibold text-sm text-white flex items-center justify-center gap-2 active:scale-95 transition-transform"
            style={{ background: "var(--p-500)", boxShadow: "0 4px 16px rgba(34,87,255,0.30)" }}
          >
            <ScanLine size={17} strokeWidth={1.8} />
            Démarrer le scan
          </button>
        ) : (
          <button
            onClick={stopCamera}
            className="w-full py-3.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 active:scale-95 transition-transform"
            style={{ background: "rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.10)" }}
          >
            Pause
          </button>
        )}
      </div>

      {/* ── Saisie manuelle ── */}
      <form onSubmit={handleManualBarcode} className="px-4 mt-2.5 flex gap-2">
        <input
          type="text"
          inputMode="numeric"
          placeholder="Code-barres manuel…"
          value={lookupCode}
          onChange={(e) => setLookupCode(e.target.value)}
          className="flex-1 py-2.5 px-4 rounded-xl outline-none font-mono text-sm"
          style={{
            background: "rgba(255,255,255,0.06)",
            color: "white",
            border: "1px solid rgba(255,255,255,0.10)",
          }}
        />
        <button
          type="submit"
          disabled={!lookupCode.trim() || lookupMutation.isPending}
          className="px-5 py-2.5 rounded-xl font-semibold text-sm text-white disabled:opacity-40 transition-opacity"
          style={{ background: "rgba(255,255,255,0.10)", border: "1px solid rgba(255,255,255,0.12)" }}
        >
          OK
        </button>
      </form>

      {/* ── Panier scanné ── */}
      {items.length > 0 && (
        <div
          className="mx-4 mt-3 rounded-2xl overflow-hidden"
          style={{ background: "#FFFFFF" }}
        >
          {/* En-tête panier */}
          <div
            className="flex items-center justify-between px-4 py-3"
            style={{ borderBottom: "1px solid var(--bd)" }}
          >
            <p className="font-semibold text-sm" style={{ color: "#0F172A" }}>
              Panier · <span className="font-bold">{itemCount} article{itemCount > 1 ? "s" : ""}</span>
            </p>
            <span className="text-sm font-bold" style={{ color: "#0F172A" }}>
              {total.toLocaleString("fr-FR")} FCFA
            </span>
          </div>

          {/* Lignes articles */}
          {items.map((item, idx) => (
            <div
              key={item.productId}
              className="flex items-center gap-3 px-4 py-3"
              style={{ borderBottom: idx < items.length - 1 ? "1px solid var(--bg-layout)" : "none" }}
            >
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm truncate" style={{ color: "#0F172A" }}>{item.productName}</p>
                <p className="text-xs font-mono mt-0.5" style={{ color: "#94A3B8" }}>{item.barcode}</p>
              </div>

              <div className="flex items-center gap-1.5 flex-shrink-0">
                <button
                  onClick={() => updateQty(item.productId, -1)}
                  className="w-7 h-7 rounded-lg flex items-center justify-center"
                  style={{ background: "var(--n-100)" }}
                >
                  <Minus size={11} style={{ color: "#64748B" }} />
                </button>
                <span className="w-5 text-center font-bold text-sm" style={{ color: "#0F172A" }}>
                  {item.quantity}
                </span>
                <button
                  onClick={() => updateQty(item.productId, 1)}
                  className="w-7 h-7 rounded-lg flex items-center justify-center"
                  style={{ background: "var(--p-500)" }}
                >
                  <Plus size={11} className="text-white" />
                </button>
              </div>

              <p className="w-20 text-right font-bold text-sm flex-shrink-0" style={{ color: "#0F172A" }}>
                {(item.unitPrice * item.quantity).toLocaleString("fr-FR")} F
              </p>

              <button
                onClick={() => setItems((prev) => prev.filter((i) => i.productId !== item.productId))}
                className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: "#FEF2F2" }}
              >
                <Trash2 size={12} style={{ color: "#EF4444" }} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── Bouton Passer en caisse ── */}
      {items.length > 0 && (
        <div className="px-4 pt-3 pb-10 mt-auto">
          <button
            onClick={handleCheckout}
            disabled={submitting}
            className="w-full py-4 rounded-xl font-semibold text-base text-white flex items-center justify-between px-5 active:scale-[0.98] transition-transform disabled:opacity-60"
            style={{
              background: "var(--p-500)",
              boxShadow: "0 6px 20px rgba(34,87,255,0.28)",
            }}
          >
            <span className="text-sm font-medium text-white/70">
              {itemCount} article{itemCount > 1 ? "s" : ""}
            </span>
            <span>{submitting ? "Création…" : "Passer en caisse"}</span>
            <span className="font-bold">{total.toLocaleString("fr-FR")} F</span>
          </button>
        </div>
      )}
    </div>
  );
}
