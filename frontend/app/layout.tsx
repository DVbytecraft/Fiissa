import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Fiissa — Commerce intelligent",
  description: "Click & Collect, Livraison, Scan & Go et paiement Mobile Money pour vos commerces UEMOA",
  manifest: "/manifest.json",
  keywords: ["fiissa", "click collect", "mobile money", "UEMOA", "commerce", "Sénégal"],
  authors: [{ name: "Fiissa" }],
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Fiissa",
  },
  formatDetection: { telephone: false },
  openGraph: {
    type: "website",
    siteName: "Fiissa",
    title: "Fiissa — Commerce intelligent UEMOA",
    description: "Commandez, payez, récupérez. Simple.",
  },
  icons: {
    icon: [
      { url: "/icons/Fiissa.png", type: "image/png" },
    ],
    apple: "/icons/Fiissa.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#2257FF",   /* Bleu Fiissa */
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <link rel="apple-touch-icon" href="/icons/Fiissa.png" />
      </head>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
