#!/usr/bin/env python3
"""
Generate PNG PWA icons from SVG source.
Usage: cd backend && python -m scripts.generate_icons
Requires: pip install cairosvg  (or pip install Pillow + cairosvg)
"""

import os
import sys
import struct
import zlib

ICON_SVG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend", "public", "icons", "icon.svg",
)
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend", "public", "icons",
)

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]


def generate_with_cairosvg():
    import cairosvg
    for size in SIZES:
        out = os.path.join(OUTPUT_DIR, f"icon-{size}x{size}.png")
        cairosvg.svg2png(url=ICON_SVG_PATH, write_to=out, output_width=size, output_height=size)
        print(f"  OK {out}")


def generate_fallback_png(size: int, out_path: str):
    """
    Minimal valid PNG — solid #2257FF square with 'F' lettermark.
    Pure stdlib, no dependencies.
    """
    width = height = size
    # RGBA: Fiissa Blue background
    r, g, b, a = 0x22, 0x57, 0xFF, 0xFF

    # Build raw pixel rows (RGBA, 4 bytes per pixel)
    row = bytes([r, g, b, a] * width)
    raw = b""
    for _ in range(height):
        raw += b"\x00" + row  # filter byte 0 = None per row

    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")

    with open(out_path, "wb") as f:
        f.write(png)


def main():
    if not os.path.exists(ICON_SVG_PATH):
        print(f"  ! SVG source not found: {ICON_SVG_PATH}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"  Source : {ICON_SVG_PATH}")
    print(f"  Output : {OUTPUT_DIR}")
    print()

    # Try cairosvg first
    try:
        import cairosvg
        print("  cairosvg détecté — génération haute qualité")
        generate_with_cairosvg()
        return
    except ImportError:
        pass

    # Try Pillow + cairosvg via subprocess fallback
    try:
        from PIL import Image
        import io
        import subprocess
        print("  Pillow détecté — tentative via inkscape CLI")
        for size in SIZES:
            out = os.path.join(OUTPUT_DIR, f"icon-{size}x{size}.png")
            result = subprocess.run(
                ["inkscape", ICON_SVG_PATH, f"--export-png={out}",
                 f"--export-width={size}", f"--export-height={size}"],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0:
                print(f"  + {size}x{size} (inkscape)")
            else:
                raise RuntimeError("inkscape failed")
        return
    except Exception:
        pass

    # Pure stdlib fallback — solid blue rectangles
    print("  ! cairosvg non disponible — génération PNG minimal (solid blue)")
    print("    Pour des icônes haute qualité : pip install cairosvg")
    print()
    for size in SIZES:
        out = os.path.join(OUTPUT_DIR, f"icon-{size}x{size}.png")
        generate_fallback_png(size, out)
        print(f"  + icon-{size}x{size}.png (fallback solid #{size}x{size})")


if __name__ == "__main__":
    print("-" * 50)
    print("  Fiissa PWA — Génération des icônes PNG")
    print("-" * 50)
    main()
    print()
    print("-" * 50)
    print("  DONE — Icônes générées dans frontend/public/icons/")
    print("-" * 50)
