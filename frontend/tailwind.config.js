/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-poppins)", "Poppins", "system-ui", "-apple-system", "sans-serif"],
      },

      /* ── Palette Fiissa extraite du logo ── */
      colors: {
        /* Bleu Fiissa — primary / CTA */
        primary: {
          50:  "#EBF0FF",
          100: "#D6E1FF",
          200: "#ADBFFF",
          300: "#849EFF",
          400: "#5B7CFF",
          500: "#2257FF",   // couleur principale
          600: "#1A44D9",
          700: "#1333B3",
          800: "#0D238C",
          900: "#071466",
        },
        /* Vert Fiissa — secondary / success / brand */
        brand: {
          50:  "#E6FBF4",
          100: "#CCFAE9",
          200: "#99F5D3",
          300: "#66EFBD",
          400: "#33E9A8",
          500: "#00D68F",   // vert logo
          600: "#00AB72",
          700: "#008056",
          800: "#005639",
          900: "#002B1D",
        },
        /* Gris bleutés neutres */
        neutral: {
          0:   "#FFFFFF",
          50:  "#F7F9FC",
          100: "#EFF2F8",
          200: "#E1E6F2",
          300: "#C7CFDF",
          400: "#99A4BC",
          500: "#6B7A99",
          600: "#485270",
          700: "#2F3A56",
          800: "#1C2540",
          900: "#0D1227",
        },
        /* Statuts */
        success: { DEFAULT: "#00D68F", bg: "#E6FBF4", dark: "#005639" },
        warning: { DEFAULT: "#F59E0B", bg: "#FFFBEB", dark: "#92400E" },
        error:   { DEFAULT: "#EF4444", bg: "#FEF2F2", dark: "#991B1B" },
        info:    { DEFAULT: "#2257FF", bg: "#EBF0FF", dark: "#1333B3" },
      },

      /* ── Gradient Fiissa ── */
      backgroundImage: {
        "fiissa":         "linear-gradient(135deg, #00D68F 0%, #00B8CC 50%, #2257FF 100%)",
        "fiissa-v":       "linear-gradient(180deg, #00D68F 0%, #2257FF 100%)",
        "fiissa-soft":    "linear-gradient(135deg, #E6FBF4 0%, #EBF0FF 100%)",
        "fiissa-dark":    "linear-gradient(135deg, #1333B3 0%, #0D1227 100%)",
      },

      /* ── Ombres avec teinte brand ── */
      boxShadow: {
        "sm":    "0 1px 4px rgba(34,87,255,0.06), 0 1px 2px rgba(13,18,39,0.04)",
        "md":    "0 4px 16px rgba(34,87,255,0.10), 0 2px 6px rgba(13,18,39,0.06)",
        "lg":    "0 8px 32px rgba(34,87,255,0.14), 0 4px 12px rgba(13,18,39,0.08)",
        "brand": "0 8px 24px rgba(34,87,255,0.28)",
        "green": "0 8px 24px rgba(0,214,143,0.28)",
        "card":  "0 2px 8px rgba(13,18,39,0.06)",
      },

      /* ── Border radius arrondi Fiissa ── */
      borderRadius: {
        "sm":   "0.5rem",
        "md":   "0.75rem",
        "lg":   "1rem",
        "xl":   "1.25rem",
        "2xl":  "1.5rem",
        "3xl":  "2rem",
        "full": "9999px",
      },

      /* ── Breakpoints mobile-first ── */
      screens: {
        xs:  "375px",
        sm:  "430px",
        md:  "768px",
        lg:  "1024px",
        xl:  "1280px",
        "2xl": "1536px",
      },

      /* ── Scale ── */
      scale: {
        "98": "0.98",
        "97": "0.97",
      },

      /* ── Animations ── */
      keyframes: {
        "slide-up": {
          "0%":   { transform: "translateY(100%)", opacity: "0" },
          "100%": { transform: "translateY(0)",    opacity: "1" },
        },
        "fade-in": {
          "0%":   { opacity: "0", transform: "scale(0.97)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition:  "200% 0" },
        },
      },
      animation: {
        "slide-up": "slide-up 0.28s ease forwards",
        "fade-in":  "fade-in 0.20s ease forwards",
        shimmer:    "shimmer 1.4s infinite",
      },

      /* ── Espacement supplémentaire ── */
      spacing: {
        "safe-bottom": "env(safe-area-inset-bottom, 0px)",
        "18": "4.5rem",
        "22": "5.5rem",
      },
    },
  },
  plugins: [],
};
