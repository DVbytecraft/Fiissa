"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  Scan, Minus, Plus, Trash2, ShoppingCart, X,
  ChevronLeft, Camera, CameraOff, CheckCircle,
} from "lucide-react";
import { catalogApi, ordersApi } from "@/lib/api";
import { useCartStore } from "@/lib/store";
import { toast } from "sonner";

interface ScannedItem {
  productId: string;
  productName: string;
  barcode: string;
  unitPrice: number;
  quantity: number;
  imageUrl?: string;
}

export default function ScanGoPage() {
  const router   = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef     = useRef<MediaStream | null>(null);
  const detectorRef   = useRef<any>(null);
  const scanIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [isScanning, setIsScanning]   = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [items, setItems]             = useState<ScannedItem[]>([]);
  const [lastScanned, setLastScanned] = useState<string | null>(null);
  const [lookupCode, setLookupCode]   = useState("");
  const [storeId, setStoreId]         = useState("");

  const total     = items.reduce((sum, i) => sum + i.unitPrice * i.quantity, 0);
  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  const lookupMutation = useMutation({
    mutationFn: (barcode: string) =>
      catalogApi.getByBarcode(barcode, storeId || undefined).then((r) => r.data),
    onSuccess: (product, barcode) => {
      setLastScanned(barcode);
      addItem(product, barcode);
    },
    onError: (e: any, barcode) => {
      if (e.response?.status === 404) {
        toast.error(`Code ${barcode} non trouvé dans le catalogue`);
      } else {
        toast.error("Erreur réseau — réessayez");
      }
    },
  });

  const addItem = (product: any, barcode: string) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.productId === product.id);
      if (existing) {
        toast.success(`${product.name} × ${existing.quantity + 1}`);
        return prev.map((i) =>
          i.productId === product.id ? { ...i, quantity: i.quantity + 1 } : i
        );
      }
      toast.success(`${product.name} ajouté`);
      return [
        ...prev,
        { productId: product.id, productName: product.name, barcode, unitPrice: product.price_xof, quantity: 1, imageUrl: product.image_url },
      ];
    });
  };

  const updateQty = (productId: string, delta: number) => {
    setItems((prev) =>
      prev.map((i) => (i.productId === productId ? { ...i, quantity: i.quantity + delta } : i)).filter((i) => i.quantity > 0)
    );
  };

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
          if (!videoRef.current || !detectorRef.current) return;
          try {
            const barcodes = await detectorRef.current.detect(videoRef.current);
            if (barcodes.length > 0) {
              const code = barcodes[0].rawValue;
              if (code !== lastScanned && !lookupMutation.isPending) {
                lookupMutation.mutate(code);
              }
            }
          } catch { /* ignore */ }
        }, 800);
      } else {
        setCameraError("BarcodeDetector non supporté. Utilisez la saisie manuelle.");
      }
      setIsScanning(true);
    } catch (err: any) {
      if (err.name === "NotAllowedError") {
        setCameraError("Accès à la caméra refusé. Autorisez-la dans les paramètres.");
      } else {
        setCameraError("Impossible d'accéder à la caméra.");
      }
    }
  }, [lastScanned, lookupMutation]);

  const stopCamera = useCallback(() => {
    if (scanIntervalRef.current) { clearInterval(scanIntervalRef.current); scanIntervalRef.current = null; }
    if (streamRef.current) { streamRef.current.getTracks().forEach((t) => t.stop()); streamRef.current = null; }
    setIsScanning(false);
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem("scan_go_store_id");
    if (saved) setStoreId(saved);
    return () => stopCamera();
  }, [stopCamera]);

  const convertToOrder = async () => {
    if (!items.length) return;
    try {
      const res = await ordersApi.createScanGoOrder({
        store_id: storeId,
        order_type: "scan_go",
        items: items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
      });
      stopCamera();
      router.push(`/payment/${res.data.id}`);
    } catch (e: any) {
      toast.error(e.response?.data?.message || "Erreur création commande");
    }
  };

  const handleManualBarcode = (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupCode.trim()) return;
    lookupMutation.mutate(lookupCode.trim());
    setLookupCode("");
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg-dark)" }}>

      {/* ── Header ── */}
      <div className="flex items-center gap-3 px-4 pt-safe pt-12 pb-4">
        <button
          onClick={() => { stopCamera(); router.back(); }}
          className="w-9 h-9 flex items-center justify-center rounded-full"
          style={{ background: "rgba(255,255,255,0.12)" }}
        >
          <ChevronLeft size={20} className="text-white" />
        </button>
        <div className="flex-1">
          <h1 className="text-white font-black text-lg">Scan & Go</h1>
          <p className="text-white/50 text-xs">Scannez vos articles · payez à la sortie</p>
        </div>
        {itemCount > 0 && (
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full"
            style={{ background: "var(--p-500)" }}
          >
            <ShoppingCart size={14} className="text-white" />
            <span className="text-white text-xs font-black">{itemCount}</span>
          </div>
        )}
      </div>

      {/* ── Zone caméra ── */}
      <div className="relative mx-4 rounded-3xl overflow-hidden" style={{ aspectRatio: "4/3", background: "#000" }}>
        <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />

        {/* Viseur */}
        {isScanning && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-56 h-32 border-2 border-white/60 rounded-xl relative">
              <div className="absolute top-0 left-0 w-6 h-6 border-t-4 border-l-4 border-white rounded-tl-md" />
              <div className="absolute top-0 right-0 w-6 h-6 border-t-4 border-r-4 border-white rounded-tr-md" />
              <div className="absolute bottom-0 left-0 w-6 h-6 border-b-4 border-l-4 border-white rounded-bl-md" />
              <div className="absolute bottom-0 right-0 w-6 h-6 border-b-4 border-r-4 border-white rounded-br-md" />
              <div className="absolute inset-x-0 top-1/2 h-0.5 -translate-y-1/2 animate-pulse" style={{ background: "var(--p-500)" }} />
            </div>
            {lookupMutation.isPending && (
              <div className="absolute top-3 right-3 w-7 h-7 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--p-400) transparent transparent transparent" }} />
            )}
          </div>
        )}

        {!isScanning && !cameraError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: "rgba(255,255,255,0.08)" }}>
              <Camera size={32} className="text-white/50" />
            </div>
            <p className="text-white/50 text-sm">Caméra désactivée</p>
          </div>
        )}

        {cameraError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center px-8 gap-3">
            <CameraOff size={32} className="text-white/50" />
            <p className="text-white/70 text-sm text-center leading-6">{cameraError}</p>
          </div>
        )}
      </div>

      {/* ── Bouton caméra ── */}
      <div className="px-4 mt-3">
        {!isScanning ? (
          <button
            onClick={startCamera}
            className="w-full py-4 rounded-2xl font-bold text-white flex items-center justify-center gap-2 active:scale-95 transition-transform"
            style={{ background: "var(--p-500)", boxShadow: "var(--sh-brand)" }}
          >
            <Scan size={20} />
            Démarrer le scan
          </button>
        ) : (
          <button
            onClick={stopCamera}
            className="w-full py-4 rounded-2xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform"
            style={{ background: "rgba(255,255,255,0.12)", color: "white" }}
          >
            <X size={20} />
            Arrêter le scan
          </button>
        )}
      </div>

      {/* ── Saisie manuelle ── */}
      <form onSubmit={handleManualBarcode} className="px-4 mt-3 flex gap-2">
        <input
          type="text"
          placeholder="Saisir un code-barres manuellement"
          value={lookupCode}
          onChange={(e) => setLookupCode(e.target.value)}
          className="flex-1 py-3 px-4 rounded-xl outline-none font-mono text-sm"
          style={{
            background: "rgba(255,255,255,0.10)",
            color: "white",
            border: "1px solid rgba(255,255,255,0.12)",
          }}
        />
        <button
          type="submit"
          disabled={!lookupCode.trim() || lookupMutation.isPending}
          className="px-5 py-3 rounded-xl font-bold text-white disabled:opacity-40"
          style={{ background: "var(--s-600)" }}
        >
          OK
        </button>
      </form>

      {/* ── Panier scanné ── */}
      {items.length > 0 && (
        <div
          className="flex-1 mx-4 mt-4 rounded-3xl p-4 overflow-y-auto"
          style={{ background: "var(--bg-card)" }}
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-black text-sm" style={{ color: "var(--tx-head)" }}>
              Mon panier · {itemCount} article{itemCount > 1 ? "s" : ""}
            </h2>
            <span className="text-xs font-bold" style={{ color: "var(--tx-muted)" }}>
              {total.toLocaleString("fr-FR")} FCFA
            </span>
          </div>

          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.productId}
                className="flex items-center gap-3 p-3 rounded-2xl"
                style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm truncate" style={{ color: "var(--tx-head)" }}>{item.productName}</p>
                  <p className="text-xs font-mono mt-0.5" style={{ color: "var(--tx-muted)" }}>{item.barcode}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => updateQty(item.productId, -1)}
                    className="w-7 h-7 rounded-full flex items-center justify-center"
                    style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
                  >
                    <Minus size={12} style={{ color: "var(--tx-muted)" }} />
                  </button>
                  <span className="w-6 text-center font-black text-sm" style={{ color: "var(--tx-head)" }}>{item.quantity}</span>
                  <button
                    onClick={() => updateQty(item.productId, 1)}
                    className="w-7 h-7 rounded-full flex items-center justify-center"
                    style={{ background: "var(--p-500)" }}
                  >
                    <Plus size={12} className="text-white" />
                  </button>
                </div>

                <p className="w-20 text-right font-bold text-sm shrink-0" style={{ color: "var(--p-500)" }}>
                  {(item.unitPrice * item.quantity).toLocaleString("fr-FR")} F
                </p>

                <button
                  onClick={() => setItems((prev) => prev.filter((i) => i.productId !== item.productId))}
                  className="shrink-0"
                  style={{ color: "var(--error)" }}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-3 flex items-center justify-between" style={{ borderTop: "1px solid var(--bd)" }}>
            <p className="font-semibold text-sm" style={{ color: "var(--tx-muted)" }}>Total</p>
            <p className="text-xl font-black" style={{ color: "var(--p-500)" }}>{total.toLocaleString("fr-FR")} FCFA</p>
          </div>
        </div>
      )}

      {/* ── Passer en caisse ── */}
      {items.length > 0 && (
        <div className="px-4 pt-3 pb-8">
          <button
            onClick={convertToOrder}
            className="w-full py-5 rounded-2xl font-black text-lg text-white flex items-center justify-center gap-3 active:scale-95 transition-transform"
            style={{ background: "var(--s-600)", boxShadow: "var(--sh-green)" }}
          >
            <CheckCircle size={22} />
            Passer en caisse — {total.toLocaleString("fr-FR")} F
          </button>
        </div>
      )}
    </div>
  );
}
