#!/usr/bin/env python3
"""
Génère les icônes PWA Fiissa en SVG et PNG.
Requiert: pip install cairosvg pillow
Usage: python scripts/generate_icons.py
"""

import os
import sys

SIZES = [72, 96, 128, 144, 192, 512]

# SVG Fiissa — "F" sur fond gradient bleu→vert
ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#00D68F"/>
      <stop offset="50%" style="stop-color:#00B8CC"/>
      <stop offset="100%" style="stop-color:#2257FF"/>
    </linearGradient>
    <clipPath id="r">
      <rect width="512" height="512" rx="112" ry="112"/>
    </clipPath>
  </defs>
  <!-- Background arrondi -->
  <rect width="512" height="512" rx="112" ry="112" fill="url(#g)"/>
  <!-- Lettre F centrée -->
  <text
    x="256" y="360"
    font-family="'Helvetica Neue', Arial, sans-serif"
    font-weight="900"
    font-size="340"
    fill="white"
    text-anchor="middle"
    dominant-baseline="auto"
    letter-spacing="-8"
  >F</text>
  <!-- Petit point vert bas-droite (optionnel, style marque) -->
  <circle cx="380" cy="390" r="32" fill="rgba(255,255,255,0.25)"/>
</svg>"""

MASKABLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#00D68F"/>
      <stop offset="50%" style="stop-color:#00B8CC"/>
      <stop offset="100%" style="stop-color:#2257FF"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" fill="url(#g)"/>
  <text
    x="256" y="340"
    font-family="'Helvetica Neue', Arial, sans-serif"
    font-weight="900"
    font-size="300"
    fill="white"
    text-anchor="middle"
    dominant-baseline="auto"
  >F</text>
</svg>"""

ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

# Écrire les SVG sources
with open(os.path.join(ICONS_DIR, "icon.svg"), "w") as f:
    f.write(ICON_SVG)
with open(os.path.join(ICONS_DIR, "icon-maskable.svg"), "w") as f:
    f.write(MASKABLE_SVG)

print(f"SVG sources créés dans {ICONS_DIR}")

# Tentative de génération PNG via cairosvg
try:
    import cairosvg
    for size in SIZES:
        svg = MASKABLE_SVG if size >= 192 else ICON_SVG
        out = os.path.join(ICONS_DIR, f"icon-{size}x{size}.png")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=out, output_width=size, output_height=size)
        print(f"  ✓ icon-{size}x{size}.png")
    print("✓ Toutes les icônes PNG générées avec cairosvg")
except ImportError:
    print("⚠ cairosvg non installé. Tentative avec pillow + rsvg...")
    try:
        from PIL import Image
        import io
        # Fallback: créer des PNG solides gradient avec PIL
        for size in SIZES:
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            # Fond gradient approximatif (vert → bleu)
            for y in range(size):
                ratio = y / size
                r = int(0 * (1 - ratio) + 34 * ratio)
                g = int(214 * (1 - ratio) + 87 * ratio)
                b = int(143 * (1 - ratio) + 255 * ratio)
                draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
            # Texte F
            try:
                from PIL import ImageFont
                font_size = int(size * 0.65)
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
            draw.text((size // 2, size // 2), "F", fill=(255, 255, 255, 255), font=font, anchor="mm")
            out = os.path.join(ICONS_DIR, f"icon-{size}x{size}.png")
            img.save(out, "PNG")
            print(f"  ✓ icon-{size}x{size}.png (PIL fallback)")
        print("✓ Icônes générées avec PIL")
    except Exception as e:
        print(f"⚠ Impossible de générer les PNG automatiquement : {e}")
        print("  → Placez manuellement vos PNG dans frontend/public/icons/")
        print("  → Fichiers requis: " + ", ".join(f"icon-{s}x{s}.png" for s in SIZES))
