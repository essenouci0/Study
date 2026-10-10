#!/usr/bin/env python3
"""Render the Study logo (book + star + orbit) into Android launcher icons.

Output goes to resources/android/res/mipmap-*/ ; the CI workflow copies that
folder over the generated android/app/src/main/res after `cap add android`.
Run:  python3 -I tools/make_icons.py
"""
import math
import os
from PIL import Image, ImageDraw

SS = 4  # supersampling factor

# ---- logo geometry (100x100 viewBox, same as the in-app logo) -------------
BOOK_PAGES_SHADOW = ("M12 64C27 61 40 62 50 69C60 62 73 61 88 64V70C73 67 60 68 50 75C40 68 27 67 12 70Z", (102, 102, 102))
BOOK_LEFT = ("M50 64C40 58 26 57 14 60V34C26 31 40 32 50 38Z", (199, 199, 199))
BOOK_RIGHT = ("M50 64C60 58 74 57 86 60V34C74 31 60 32 50 38Z", (255, 255, 255))
STAR = ("M50 8Q51.4 15.6 59 17Q51.4 18.4 50 26Q48.6 18.4 41 17Q48.6 15.6 50 8Z", (255, 255, 255))


def parse_path(d):
    """Parse the tiny absolute-only path subset used by the logo into polygons."""
    import re
    toks = re.findall(r"[MCQVZ]|-?\d+\.?\d*", d)
    pts, i, cur, cmd = [], 0, (0.0, 0.0), None
    while i < len(toks):
        t = toks[i]
        if t in "MCQVZ":
            cmd = t
            i += 1
            if cmd == "Z":
                continue
        if cmd == "M":
            cur = (float(toks[i]), float(toks[i + 1])); i += 2
            pts.append(cur)
        elif cmd == "V":
            cur = (cur[0], float(toks[i])); i += 1
            pts.append(cur)
        elif cmd == "C":
            p1 = (float(toks[i]), float(toks[i + 1]))
            p2 = (float(toks[i + 2]), float(toks[i + 3]))
            p3 = (float(toks[i + 4]), float(toks[i + 5])); i += 6
            for k in range(1, 25):
                u = k / 24
                x = (1-u)**3*cur[0] + 3*(1-u)**2*u*p1[0] + 3*(1-u)*u*u*p2[0] + u**3*p3[0]
                y = (1-u)**3*cur[1] + 3*(1-u)**2*u*p1[1] + 3*(1-u)*u*u*p2[1] + u**3*p3[1]
                pts.append((x, y))
            cur = p3
        elif cmd == "Q":
            p1 = (float(toks[i]), float(toks[i + 1]))
            p2 = (float(toks[i + 2]), float(toks[i + 3])); i += 4
            for k in range(1, 17):
                u = k / 16
                x = (1-u)**2*cur[0] + 2*(1-u)*u*p1[0] + u*u*p2[0]
                y = (1-u)**2*cur[1] + 2*(1-u)*u*p1[1] + u*u*p2[1]
                pts.append((x, y))
            cur = p2
    return pts


def rot(p, deg, c=(50, 50)):
    a = math.radians(deg)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x*math.cos(a) - y*math.sin(a), c[1] + x*math.sin(a) + y*math.cos(a))


def draw_logo(size, box_frac, bg=None):
    """Return an RGBA image `size`x`size` with the logo fitted in `box_frac` of it.

    bg: None (transparent), 'square' (rounded square), 'circle', or 'full'.
    """
    S = size * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if bg == "square":
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.24), fill=(0, 0, 0, 255))
    elif bg == "circle":
        d.ellipse([0, 0, S - 1, S - 1], fill=(0, 0, 0, 255))
    elif bg == "full":
        d.rectangle([0, 0, S, S], fill=(0, 0, 0, 255))

    scale = S * box_frac / 100.0
    off = S * (1 - box_frac) / 2

    def T(p):
        return (off + p[0] * scale, off + p[1] * scale)

    # orbit ring (opacity .45) and orbiting dot
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    ell = [rot((50 + 40*math.cos(t), 52 + 12*math.sin(t)), -18) for t in [k * math.pi / 90 for k in range(181)]]
    rd.line([T(p) for p in ell], fill=(255, 255, 255, int(255 * .45)), width=max(2, int(1.8 * scale)), joint="curve")
    img.alpha_composite(ring)
    d = ImageDraw.Draw(img)

    for path, col in (BOOK_PAGES_SHADOW, BOOK_LEFT, BOOK_RIGHT, STAR):
        d.polygon([T(p) for p in parse_path(path)], fill=col + (255,))

    dot = T(rot((90, 52), -18))
    r = 2.3 * scale
    d.ellipse([dot[0] - r, dot[1] - r, dot[0] + r, dot[1] + r], fill=(255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


def main():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "android", "res")
    legacy = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
    for dens, px in legacy.items():
        out = os.path.join(root, f"mipmap-{dens}")
        os.makedirs(out, exist_ok=True)
        draw_logo(px, 0.94, "square").save(os.path.join(out, "ic_launcher.png"))
        draw_logo(px, 0.80, "circle").save(os.path.join(out, "ic_launcher_round.png"))
        # adaptive foreground: 108dp canvas, logo kept inside the 66dp safe zone
        fg = int(px * 108 / 48)
        draw_logo(fg, 0.60, None).save(os.path.join(out, "ic_launcher_foreground.png"))
    # store/preview icon
    draw_logo(512, 0.94, "square").save(os.path.join(root, "..", "icon-512.png"))
    print("icons written to", os.path.normpath(root))


if __name__ == "__main__":
    main()
