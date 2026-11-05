#!/usr/bin/env python3
"""
ROUGH SAMPLE render — "Trijata's dream" (Valmiki Ramayana, Sundara Kanda, Sarga 27).

This is a timing / motion / subtitle / format proof-of-concept ONLY:
  * All art is placeholder, drawn procedurally in code (no image model available yet).
  * There is NO narration (ElevenLabs is not reachable from this environment yet).
  * Music is an original procedural tanpura-style drone (no licensing issues).

Usage:
  python3 pipeline/sample_trijata.py                 # full render -> renders/sample_trijata_v0.mp4
  python3 pipeline/sample_trijata.py --stills 3,9,14 # write QA stills to qa/ only
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30
DUR = 49.0
LW, LH = 1300, 2300            # standard layer size (margin for parallax)
FONT_SUB = os.path.join(ROOT, "assets/fonts/NotoSansDevanagari-Bold.ttf")
FONT_TITLE = os.path.join(ROOT, "assets/fonts/TiroDevanagariHindi-Regular.ttf")
random.seed(11)
RNG = np.random.default_rng(11)


# ───────────────────────── drawing primitives ─────────────────────────
def comp(L, tmp, x0, y0):
    """alpha_composite tmp onto L at (x0,y0), clipping to bounds."""
    x0, y0 = int(x0), int(y0)
    sx, sy = max(0, -x0), max(0, -y0)
    ex, ey = min(tmp.width, L.width - x0), min(tmp.height, L.height - y0)
    if ex <= sx or ey <= sy:
        return
    L.alpha_composite(tmp.crop((sx, sy, ex, ey)), (x0 + sx, y0 + sy))


def blob_pts(cx, cy, rx, ry, n=30, irr=0.16, rot=0.0):
    ph = [random.uniform(0, 6.28) for _ in range(3)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 1 + irr * (0.5 * math.sin(3 * a + ph[0]) + 0.3 * math.sin(5 * a + ph[1]) + 0.2 * math.sin(7 * a + ph[2]))
        x, y = rx * r * math.cos(a), ry * r * math.sin(a)
        pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return pts


def _bbox(pts, pad):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return int(min(xs)) - pad, int(min(ys)) - pad, int(max(xs)) + pad, int(max(ys)) + pad


def wash(L, pts, color, alpha=200, passes=3, jitter=6, blur=2.0, edge=0.35):
    """Watercolour-style fill: jittered translucent passes + darker pigment edge."""
    pad = int(jitter * 3 + blur * 4 + 8)
    x0, y0, x1, y1 = _bbox(pts, pad)
    tmp = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    a = min(255, int(alpha / passes * 1.25))
    for _ in range(passes):
        jp = [(x - x0 + random.uniform(-jitter, jitter), y - y0 + random.uniform(-jitter, jitter)) for x, y in pts]
        layer = Image.new("RGBA", tmp.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(jp, fill=tuple(color) + (a,))
        tmp.alpha_composite(layer)
    if blur:
        tmp = tmp.filter(ImageFilter.GaussianBlur(blur))
    if edge > 0:
        ec = tuple(int(c * 0.62) for c in color)
        e = Image.new("RGBA", tmp.size, (0, 0, 0, 0))
        jp = [(x - x0, y - y0) for x, y in pts]
        ImageDraw.Draw(e).line(jp + [jp[0]], fill=ec + (int(255 * edge),), width=3, joint="curve")
        tmp.alpha_composite(e.filter(ImageFilter.GaussianBlur(1.0)))
    comp(L, tmp, x0, y0)


def pencil(L, pts, color=(46, 38, 34), width=2, alpha=170, passes=2, jitter=1.1, closed=False):
    pts = list(pts) + ([pts[0]] if closed else [])
    pad = int(width * 3 + 8)
    x0, y0, x1, y1 = _bbox(pts, pad)
    tmp = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    for _ in range(passes):
        layer = Image.new("RGBA", tmp.size, (0, 0, 0, 0))
        jp = [(x - x0 + random.uniform(-jitter, jitter), y - y0 + random.uniform(-jitter, jitter)) for x, y in pts]
        ImageDraw.Draw(layer).line(jp, fill=tuple(color) + (int(alpha / passes * 1.3),), width=width, joint="curve")
        tmp.alpha_composite(layer)
    comp(L, tmp.filter(ImageFilter.GaussianBlur(0.5)), x0, y0)


def stroke(L, pts, color, width, alpha=235, blur=1.0):
    pad = int(width * 2 + 8)
    x0, y0, x1, y1 = _bbox(pts, pad)
    tmp = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).line([(x - x0, y - y0) for x, y in pts], fill=tuple(color) + (alpha,), width=int(width), joint="curve")
    comp(L, tmp.filter(ImageFilter.GaussianBlur(blur)), x0, y0)


def glow(L, cx, cy, r, color, alpha=120):
    size = int(r * 2)
    g = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((size * 0.25, size * 0.25, size * 0.75, size * 0.75), fill=tuple(color) + (alpha,))
    comp(L, g.filter(ImageFilter.GaussianBlur(r / 4)), cx - r, cy - r)


def gradient(w, h, top, bottom):
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(top)[None, None, :] * (1 - t) + np.array(bottom)[None, None, :] * t)
    arr = np.repeat(arr, w, axis=1).astype(np.uint8)
    return Image.fromarray(np.dstack([arr, np.full((h, w), 255, np.uint8)]), "RGBA")


# ───────────────────────── characters (placeholder) ─────────────────────────
def seated_woman(L, x, y, s, saree, skin, hair, outline=(46, 38, 34), bow_head=0.0):
    hx, hy = x + 7 * s * bow_head, y - 206 * s + 9 * s * bow_head
    stroke(L, [(hx + 12 * s, hy + 8 * s), (hx + 28 * s, hy + 60 * s), (hx + 32 * s, hy + 120 * s), (hx + 27 * s, hy + 160 * s)], hair, 12 * s)  # single braid
    body = [(x - 34 * s, y - 172 * s), (x + 30 * s, y - 176 * s), (x + 48 * s, y - 112 * s), (x + 98 * s, y - 34 * s),
            (x + 92 * s, y + 4 * s), (x - 92 * s, y + 6 * s), (x - 74 * s, y - 46 * s), (x - 52 * s, y - 118 * s)]
    wash(L, body, saree, alpha=240, jitter=2.5 * s, blur=1.4)
    for fold in ([(x - 18 * s, y - 150 * s), (x - 38 * s, y - 70 * s), (x - 62 * s, y - 2 * s)],
                 [(x + 20 * s, y - 120 * s), (x + 30 * s, y - 60 * s), (x + 10 * s, y)]):
        pencil(L, fold, outline, width=max(1, int(1.5 * s)), alpha=110)
    pencil(L, body, outline, width=max(2, int(2 * s)), closed=True)
    stroke(L, [(x + 22 * s, y - 160 * s), (x + 42 * s, y - 100 * s), (x + 72 * s, y - 48 * s)], skin, 13 * s)
    head = blob_pts(hx, hy, 24 * s, 29 * s, irr=0.03)
    wash(L, head, skin, alpha=250, jitter=1.2, blur=0.8, edge=0.2)
    wash(L, blob_pts(hx + 4 * s, hy - 12 * s, 27 * s, 21 * s, irr=0.06), hair, alpha=245, jitter=1.2, blur=0.8, edge=0.1)
    pencil(L, head, outline, width=max(2, int(2 * s)), closed=True)


def standing(L, x, y, s, garment, skin, hair, bulk=1.0, prop=None, garland=False, arm_up=False,
             facing=1, sash=None, outline=(46, 38, 34), wild_hair=False, topknot=False):
    b = bulk
    lower = [(x - 34 * s * b, y - 212 * s), (x + 34 * s * b, y - 212 * s), (x + 48 * s * b, y), (x - 48 * s * b, y)]
    torso = [(x - 45 * s * b, y - 342 * s), (x + 45 * s * b, y - 342 * s), (x + 33 * s * b, y - 205 * s), (x - 33 * s * b, y - 205 * s)]
    hx, hy = x, y - 375 * s
    # arms
    stroke(L, [(x - 44 * s * b, y - 334 * s), (x - 56 * s * b, y - 270 * s), (x - 54 * s * b, y - 205 * s)], skin, 15 * s * b)
    if arm_up:
        stroke(L, [(x + 44 * s * b * facing, y - 334 * s), (x + 85 * s * facing, y - 380 * s), (x + 110 * s * facing, y - 440 * s)], skin, 15 * s * b)
    else:
        stroke(L, [(x + 44 * s * b, y - 334 * s), (x + 56 * s * b, y - 270 * s), (x + 54 * s * b, y - 205 * s)], skin, 15 * s * b)
    wash(L, torso, skin if sash else garment, alpha=245, jitter=2 * s, blur=1.2)
    wash(L, lower, garment, alpha=245, jitter=2 * s, blur=1.2)
    if sash:
        wash(L, [(x - 45 * s * b, y - 342 * s), (x - 20 * s * b, y - 342 * s), (x + 35 * s * b, y - 215 * s), (x + 8 * s * b, y - 205 * s)], sash, alpha=230, jitter=1.5, blur=1)
    pencil(L, torso, outline, width=max(2, int(2 * s)), closed=True)
    pencil(L, lower, outline, width=max(2, int(2 * s)), closed=True)
    pencil(L, [(x, y - 200 * s), (x + 6 * s, y - 100 * s), (x + 2 * s, y)], outline, width=max(1, int(1.4 * s)), alpha=100)
    if garland:
        for i in range(15):
            u = i / 14
            gx = x + (-34 + 68 * u) * s * b
            gy = y - 330 * s + 95 * s * math.sin(math.pi * u)
            glow(L, gx, gy, 9 * s, (255, 255, 250), 230)
    if prop == "bow":
        bx = x + 78 * s * facing
        pts = [(bx + 26 * s * math.sin(math.pi * u) * facing, y - 470 * s + 340 * s * u) for u in np.linspace(0, 1, 18)]
        stroke(L, pts, (96, 62, 34), 6 * s)
        pencil(L, [pts[0], pts[-1]], (230, 220, 200), width=max(1, int(1.2 * s)), alpha=200)
    if prop == "spear":
        sx = x + 70 * s * b * facing
        stroke(L, [(sx, y + 4 * s), (sx, y - 520 * s)], (40, 30, 28), 5 * s)
        wash(L, [(sx - 12 * s, y - 520 * s), (sx + 12 * s, y - 520 * s), (sx, y - 575 * s)], (150, 150, 160), alpha=250, jitter=1, blur=0.5)
    head = blob_pts(hx, hy, 25 * s * min(b, 1.15), 30 * s, irr=0.03)
    if wild_hair:
        wash(L, blob_pts(hx, hy - 6 * s, 48 * s, 44 * s, irr=0.35), hair, alpha=240, jitter=4, blur=1.5, edge=0.1)
    wash(L, head, skin, alpha=250, jitter=1.2, blur=0.8, edge=0.2)
    wash(L, blob_pts(hx, hy - 14 * s, 27 * s, 19 * s, irr=0.06), hair, alpha=245, jitter=1, blur=0.8, edge=0.1)
    if topknot:
        wash(L, blob_pts(hx, hy - 40 * s, 15 * s, 15 * s, irr=0.1), hair, alpha=245, jitter=1, blur=0.8, edge=0.1)
    pencil(L, head, outline, width=max(2, int(2 * s)), closed=True)


# ───────────────────────── scene layers ─────────────────────────
def night_sky(w=LW, h=LH, tint=(1, 1, 1)):
    top = tuple(int(c * k) for c, k in zip((13, 18, 42), tint))
    bot = tuple(int(c * k) for c, k in zip((44, 54, 92), tint))
    L = gradient(w, h, top, bot)
    d = ImageDraw.Draw(L)
    for _ in range(220):
        x, y = random.uniform(0, w), random.uniform(0, h * 0.55)
        r = random.choice([1, 1, 1.5, 2])
        a = random.randint(90, 230)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(240, 235, 210, a))
    for _ in range(5):
        wash(L, blob_pts(random.uniform(0, w), random.uniform(250, 1000), random.uniform(200, 380), random.uniform(30, 60), irr=0.3),
             (58, 66, 104), alpha=70, jitter=10, blur=12, edge=0)
    glow(L, 920, 470, 330, (242, 210, 122), 70)
    wash(L, blob_pts(920, 470, 82, 82, irr=0.02), (246, 232, 190), alpha=255, jitter=1.5, blur=1.2, edge=0.15)
    wash(L, blob_pts(900, 455, 22, 18), (220, 205, 165), alpha=110, jitter=2, blur=3, edge=0)
    wash(L, blob_pts(940, 500, 16, 12), (220, 205, 165), alpha=100, jitter=2, blur=3, edge=0)
    return L


def far_layer():
    L = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    base = 1300
    pal = (24, 30, 58)
    # Lanka palace silhouette (left, distant)
    for x0, wd, ht in [(90, 160, 210), (240, 120, 300), (350, 200, 250), (540, 110, 330), (640, 150, 220)]:
        wash(L, [(x0, base), (x0, base - ht), (x0 + wd, base - ht), (x0 + wd, base)], pal, alpha=250, jitter=2, blur=1, edge=0.15)
        wash(L, blob_pts(x0 + wd / 2, base - ht, wd * 0.42, wd * 0.36), pal, alpha=250, jitter=2, blur=1, edge=0.1)
        wash(L, [(x0 + wd / 2 - 6, base - ht - wd * 0.3), (x0 + wd / 2 + 6, base - ht - wd * 0.3), (x0 + wd / 2, base - ht - wd * 0.3 - 70)], pal, alpha=250, jitter=1, blur=0.5, edge=0)
        for _ in range(4):
            wx, wy = x0 + random.uniform(20, wd - 20), base - random.uniform(40, ht - 30)
            glow(L, wx, wy, 14, (236, 170, 90), 200)
    for i in range(16):
        x = i * 90 + random.uniform(-30, 30)
        wash(L, blob_pts(x, base + 20 - random.uniform(0, 120), random.uniform(90, 150), random.uniform(80, 150), irr=0.25),
             (20, 40, 42), alpha=240, jitter=6, blur=2.5, edge=0.15)
    wash(L, [(0, base + 40), (LW, base + 20), (LW, LH), (0, LH)], (18, 36, 34), alpha=255, jitter=4, blur=2, edge=0)
    return L


def ashoka_tree(L, cx, base, scale=1.0):
    trunk = [(cx - 40 * scale, base), (cx - 26 * scale, base - 300 * scale), (cx - 70 * scale, base - 560 * scale),
             (cx - 20 * scale, base - 560 * scale), (cx + 14 * scale, base - 330 * scale), (cx + 60 * scale, base - 580 * scale),
             (cx + 92 * scale, base - 560 * scale), (cx + 36 * scale, base - 280 * scale), (cx + 52 * scale, base)]
    wash(L, trunk, (58, 42, 36), alpha=250, jitter=3, blur=1.2)
    pencil(L, trunk, (26, 20, 18), width=3, closed=True)
    ccx, ccy = cx + 20 * scale, base - 700 * scale
    greens = [(30, 64, 50), (42, 82, 58), (26, 54, 44), (52, 92, 66)]
    for _ in range(34):
        a = random.uniform(0, 6.28); r = random.uniform(0, 1) ** 0.6
        bx, by = ccx + math.cos(a) * r * 380 * scale, ccy + math.sin(a) * r * 260 * scale
        wash(L, blob_pts(bx, by, random.uniform(90, 160) * scale, random.uniform(60, 110) * scale, irr=0.3),
             random.choice(greens), alpha=225, jitter=5, blur=1.8, edge=0.25)
    d_layer = Image.new("RGBA", L.size, (0, 0, 0, 0)); d = ImageDraw.Draw(d_layer)
    for _ in range(420):  # ashoka blossom clusters (orange-red)
        a = random.uniform(0, 6.28); r = random.uniform(0, 1) ** 0.7
        bx, by = ccx + math.cos(a) * r * 380 * scale, ccy + math.sin(a) * r * 250 * scale
        rr = random.uniform(3, 7) * scale
        c = random.choice([(196, 86, 46), (214, 124, 52), (176, 64, 42)])
        d.ellipse((bx - rr, by - rr, bx + rr, by + rr), fill=c + (random.randint(150, 230),))
    L.alpha_composite(d_layer.filter(ImageFilter.GaussianBlur(0.8)))


def garden_mid():
    L = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ashoka_tree(L, 560, 1380, 1.0)
    glow(L, 660, 1300, 260, (230, 214, 170), 70)   # moonlight pool on Sita
    seated_woman(L, 660, 1420, 1.0, saree=(214, 184, 118), skin=(176, 128, 98), hair=(24, 18, 18), bow_head=1.0)
    return L


def rakshasi_ring(positions, dark=True):
    L = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    for (x, y, s, f) in positions:
        standing(L, x, y, s, garment=(62, 26, 46), skin=(66, 54, 70), hair=(18, 14, 22), bulk=1.3,
                 prop="spear", facing=f, outline=(176, 66, 52), wild_hair=True)
    return L


def foreground():
    L = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    for (x, y, rot) in [(60, 2120, -0.6), (180, 2200, -0.9), (1250, 2140, 0.7), (1120, 2230, 0.4), (40, 330, 0.9), (150, 260, 1.2), (1260, 300, -0.9)]:
        for _ in range(3):
            wash(L, blob_pts(x + random.uniform(-60, 60), y + random.uniform(-60, 60), 170, 46, irr=0.12, rot=rot + random.uniform(-0.4, 0.4)),
                 (10, 20, 18), alpha=250, jitter=3, blur=1.5, edge=0.1)
    return L.filter(ImageFilter.GaussianBlur(3))  # shallow depth-of-field


def trijata_bg():
    L = night_sky(tint=(0.85, 0.85, 0.95))
    wash(L, [(0, 1700), (LW, 1650), (LW, LH), (0, LH)], (20, 30, 30), alpha=255, jitter=4, blur=2, edge=0)
    trunk = [(80, LH), (130, 900), (60, 0), (260, 0), (250, 900), (300, LH)]
    wash(L, trunk, (40, 30, 28), alpha=255, jitter=3, blur=1.5)
    pencil(L, trunk, (20, 14, 12), width=3, closed=True)
    for _ in range(14):
        wash(L, blob_pts(random.uniform(0, LW), random.uniform(0, 380), random.uniform(120, 220), random.uniform(60, 120), irr=0.3),
             random.choice([(20, 40, 36), (26, 48, 40)]), alpha=235, jitter=5, blur=2, edge=0.2)
    # torch on pole
    stroke(L, [(1060, 1720), (1050, 1290)], (50, 36, 28), 12)
    return L


def trijata_fig():
    L = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    seated_woman(L, 620, 1860, 2.3, saree=(98, 44, 74), skin=(132, 98, 86), hair=(198, 198, 204), outline=(40, 26, 30))
    return L


TRIJATA_HEAD = (620, 1860 - 206 * 2.3)   # layer coords of head centre (bow_head=0)


def dream_layer():
    w, h = LW, 3600
    L = gradient(w, h, (250, 244, 230), (238, 228, 205))
    glow(L, 650, 760, 900, (242, 210, 122), 90)
    for i in range(18):  # light rays
        a = -math.pi / 2 + (i - 8.5) * 0.13
        pencil(L, [(650, 720), (650 + math.cos(a) * 1300, 720 + math.sin(a) * 1300)], (232, 196, 110), width=6, alpha=50, passes=1)
    mtn = [(80, 1560), (300, 1200), (420, 1260), (560, 820), (650, 690), (760, 840), (880, 1180), (1000, 1120), (1220, 1560)]
    wash(L, mtn, (232, 236, 242), alpha=255, jitter=4, blur=1.5, edge=0.3)
    wash(L, [(650, 690), (760, 840), (880, 1180), (1000, 1120), (1220, 1560), (700, 1560)], (196, 206, 222), alpha=150, jitter=5, blur=4, edge=0)
    pencil(L, mtn, (90, 96, 110), width=3)
    glow(L, 650, 640, 200, (255, 236, 170), 150)
    seated_woman(L, 650, 760, 0.62, saree=(252, 252, 246), skin=(196, 146, 112), hair=(30, 24, 22), outline=(120, 110, 100))
    # ocean
    wash(L, [(0, 1500), (w, 1500), (w, 2760), (0, 2760)], (120, 168, 206), alpha=235, jitter=8, blur=4, edge=0)
    for _ in range(26):
        wash(L, blob_pts(random.uniform(0, w), random.uniform(1550, 2700), random.uniform(160, 340), random.uniform(18, 40), irr=0.3),
             random.choice([(96, 146, 192), (146, 190, 220), (82, 128, 178)]), alpha=120, jitter=8, blur=6, edge=0)
    # shore
    wash(L, [(0, 2740), (w * 0.4, 2700), (w, 2760), (w, h), (0, h)], (226, 210, 172), alpha=255, jitter=6, blur=3, edge=0.2)
    standing(L, 500, 3330, 1.55, garment=(250, 250, 244), skin=(80, 96, 130), hair=(26, 22, 22), prop="bow", garland=True,
             sash=(248, 246, 236), outline=(90, 90, 100), topknot=True)          # Rama
    standing(L, 800, 3350, 1.45, garment=(250, 250, 244), skin=(206, 162, 122), hair=(30, 24, 22), prop="bow", garland=True,
             sash=(248, 246, 236), outline=(90, 90, 100), topknot=True)          # Lakshmana
    return L


def wave_layer(seed):
    random.seed(seed)
    L = Image.new("RGBA", (LW, 3600), (0, 0, 0, 0))
    for _ in range(26):
        y = random.uniform(1560, 2700); x = random.uniform(-100, LW)
        pts = [(x + i * 14, y + 6 * math.sin(i * 0.6)) for i in range(18)]
        pencil(L, pts, (250, 252, 255), width=3, alpha=170, passes=1)
    return L


def trijata_standing():
    L = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    standing(L, 330, 2120, 1.6, garment=(98, 44, 74), skin=(132, 98, 86), hair=(198, 198, 204), bulk=1.05,
             arm_up=True, facing=1, outline=(220, 120, 80))
    return L


# ───────────────────────── camera & composition ─────────────────────────
def ease(u):
    u = min(1, max(0, u)); return u * u * (3 - 2 * u)


def lerp(a, b, u): return a + (b - a) * u


def view(img, depth, panx, pany, zoom, dx=0, dy=0):
    z = 1 + (zoom - 1) * depth
    cw, ch = W / z, H / z
    cx = img.width / 2 + panx * depth - dx
    cy = img.height / 2 + pany * depth - dy
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return img.resize((W, H), Image.BILINEAR, box=box), (box, z)


def to_screen(px, py, tf):
    (bx0, by0, _, _), z = tf
    return (px - bx0) * z, (py - by0) * z


def fade_alpha(img, a):
    if a >= 0.999: return img
    r, g, b, al = img.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))


# sprites
def sprite(r, color, alpha=255, blur=None):
    s = Image.new("RGBA", (r * 4, r * 4), (0, 0, 0, 0))
    ImageDraw.Draw(s).ellipse((r * 1.5, r * 1.5, r * 2.5, r * 2.5), fill=color + (alpha,))
    return s.filter(ImageFilter.GaussianBlur(blur or r * 0.6))


FIREFLY = [sprite(r, (226, 236, 140)) for r in (5, 7, 9)]
MOTE = [sprite(r, (240, 200, 110)) for r in (4, 6)]
PETAL = sprite(6, (214, 104, 50), blur=1.2)
FLAME_GLOW = sprite(60, (255, 160, 70), alpha=150, blur=45)

FF = [(random.uniform(0, W), random.uniform(500, 1800), random.uniform(0, 6.28), random.uniform(0.2, 0.6), random.choice(FIREFLY)) for _ in range(34)]
PT = [(random.uniform(-100, W), random.uniform(0, H), random.uniform(0, 6.28), random.uniform(40, 90)) for _ in range(16)]
MT = [(random.uniform(0, W), random.uniform(0, H), random.uniform(0, 6.28), random.uniform(25, 60), random.choice(MOTE)) for _ in range(40)]


def put(frame, spr, x, y, a=1.0):
    spr = fade_alpha(spr, a) if a < 0.99 else spr
    comp(frame, spr, x - spr.width / 2, y - spr.height / 2)


def fireflies(frame, t, k=1.0):
    for (x, y, ph, sp, spr) in FF:
        fx = x + 40 * math.sin(t * sp + ph); fy = y + 30 * math.sin(t * sp * 1.3 + ph * 2)
        a = 0.5 + 0.5 * math.sin(t * 2.2 + ph * 3)
        put(frame, spr, fx, fy, max(0, a) * k)


def petals(frame, t):
    for (x, y, ph, sp) in PT:
        py = (y + t * sp) % (H + 100) - 50
        px = x + 50 * math.sin(t * 0.8 + ph) + t * 8
        put(frame, PETAL, px % W, py, 0.85)


def motes(frame, t):
    for (x, y, ph, sp, spr) in MT:
        py = (y - t * sp) % (H + 100) - 50
        put(frame, spr, x + 30 * math.sin(t * 0.7 + ph), py, 0.5 + 0.5 * math.sin(t * 1.7 + ph))


# ───────────────────────── text ─────────────────────────
def text_block(text, font_path, size, max_w=900, fill=(255, 255, 255), stroke_fill=(20, 26, 48), sw=5, lh=1.6):
    font = ImageFont.truetype(font_path, size)
    lines, cur = [], ""
    for wd in text.split(" "):
        test = (cur + " " + wd).strip()
        if font.getlength(test) <= max_w or not cur: cur = test
        else: lines.append(cur); cur = wd
    lines.append(cur)
    lhp = int(size * lh)
    img = Image.new("RGBA", (W, lhp * len(lines) + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        d.text(((W - font.getlength(l)) / 2, 25 + i * lhp), l, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke_fill)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(img.getchannel("A").point(lambda v: int(v * 0.55)))
    out = shadow.filter(ImageFilter.GaussianBlur(10))
    out.alpha_composite(img)
    return out


SUBS = [
    (0.4, 3.9, "रावण की अपनी अशोक वाटिका में…"),
    (4.0, 7.6, "एक राक्षसी ने रावण के अंत का सपना देखा था।"),
    (7.9, 11.2, "राक्षसियाँ सीता को घेरकर डरा-धमका रही थीं…"),
    (11.6, 15.2, "तभी एक बूढ़ी राक्षसी नींद से जागी — त्रिजटा।"),
    (15.4, 18.9, "उसने कहा — मैंने आज रात एक सपना देखा है…"),
    (20.2, 24.0, "राम और लक्ष्मण — सफ़ेद वस्त्रों और सफ़ेद मालाओं में…"),
    (24.3, 28.2, "और सीता — समुद्र से घिरे एक सफ़ेद पर्वत पर।"),
    (30.0, 34.0, "त्रिजटा समझ गई — ये राक्षसों के विनाश का संकेत है।"),
    (34.2, 38.2, "उसने बाकी राक्षसियों से कहा — सीता को डराना बंद करो।"),
    (39.0, 43.4, "रावण के अपने घर में… उसका अंत सबसे पहले एक सपने ने देखा।"),
]
SUB_Y = 1330   # top of subtitle block (keeps clear of bottom ~380px UI zone)


# ───────────────────────── build everything ─────────────────────────
def build():
    print("building layers…", flush=True)
    A = {}
    A["sky"] = night_sky()
    A["far"] = far_layer()
    A["mid"] = garden_mid()
    A["rk"] = rakshasi_ring([(380, 1480, 0.95, 1), (930, 1480, 0.95, -1), (210, 1600, 1.05, 1), (1110, 1580, 1.05, -1)])
    A["fg"] = foreground()
    A["tj_bg"] = trijata_bg()
    A["tj"] = trijata_fig()
    A["dream"] = dream_layer()
    A["wave1"] = wave_layer(3); A["wave2"] = wave_layer(9)
    A["tj_st"] = trijata_standing()
    A["rk2"] = rakshasi_ring([(820, 2010, 1.2, -1), (1000, 2060, 1.25, -1), (1180, 1990, 1.15, -1)])
    A["subs"] = [(a, b, text_block(s, FONT_SUB, 56, max_w=960)) for a, b, s in SUBS]
    A["wm"] = text_block("नमूना · SAMPLE — placeholder art, no voiceover", FONT_SUB, 28, fill=(255, 255, 255), sw=2)
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    panel = Image.new("RGBA", (860, 420), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle((0, 0, 859, 419), 36, fill=(14, 20, 40, 190), outline=(226, 196, 120, 200), width=3)
    comp(card, panel, 110, 380)
    for txt, size, y, col in [("स्रोत", 74, 395, (242, 210, 122)), ("वाल्मीकि रामायण", 64, 500, (250, 245, 232)),
                              ("सुन्दरकाण्ड · सर्ग 27", 58, 605, (250, 245, 232))]:
        comp(card, text_block(txt, FONT_TITLE, size, fill=col, sw=0, lh=1.3), 0, y)
    A["card"] = card
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.38 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    n = RNG.normal(0, 1, (H // 3, W // 3)).astype(np.float32)
    coarse = np.asarray(Image.fromarray(((n * 30) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
    fine = RNG.normal(0, 1, (H, W)).astype(np.float32)
    grain = 1 + 0.05 * (coarse - 128) / 64 + 0.025 * fine
    A["post"] = (np.clip(vig, 0.5, 1) * grain)[:, :, None]
    return A


def layers_frame(stack):
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    tfs = {}
    for key, img, depth, panx, pany, zoom, dx, dy, alpha in stack:
        if alpha <= 0.01: continue
        v, tf = view(img, depth, panx, pany, zoom, dx, dy)
        tfs[key] = tf
        frame.alpha_composite(fade_alpha(v, alpha))
    return frame, tfs


def scene(A, name, t):
    if name == "garden" or name == "ending":
        if name == "garden":
            if t < 7.5: u = ease(t / 7.5); zoom, pany = lerp(1.0, 1.08, u), lerp(0, 60, u)
            else: u = ease((t - 7.5) / 4.3); zoom, pany = lerp(1.08, 1.32, u), lerp(60, 190, u)
            rk = ease((t - 7.6) / 1.0)
        else:
            u = ease((t - 38.4) / 8.0); zoom, pany = lerp(1.38, 1.0, u), lerp(200, 0, u); rk = 0
        panx = 25 * math.sin(t * 0.15)
        br = 1.6 * math.sin(t * 2 * math.pi / 4.2)                   # Sita breathing (tiny vertical drift)
        f, tf = layers_frame([("sky", A["sky"], 0.25, panx, pany, zoom, 0, 0, 1), ("far", A["far"], 0.5, panx, pany, zoom, 0, 0, 1),
                              ("mid", A["mid"], 1.0, panx, pany, zoom, 0, br, 1),
                              ("rk", A["rk"], 1.05, panx, pany, zoom, 4 * math.sin(t * 0.9), 0, rk),
                              ("fg", A["fg"], 1.35, panx, pany, zoom, 8 * math.sin(t * 0.6), 0, 1)])
        fireflies(f, t); petals(f, t)
        return f
    if name == "trijata":
        u = ease((t - 11.2) / 8.6)
        zoom, pany, panx = lerp(1.0, 1.16, u), lerp(0, 140, u), lerp(-20, 10, u)
        f, tf = layers_frame([("bg", A["tj_bg"], 0.45, panx, pany, zoom, 0, 0, 1), ("tj", A["tj"], 1.0, panx, pany, zoom, 0, 1.2 * math.sin(t * 1.4), 1),
                              ("fg", A["fg"], 1.3, panx, pany, zoom, 0, 0, 1)])
        # torch flame + flicker glow
        fx, fy = to_screen(1050, 1260, tf["bg"])
        fl = 0.75 + 0.15 * math.sin(t * 13) + 0.1 * math.sin(t * 23 + 1)
        put(f, FLAME_GLOW, fx, fy, fl)
        put(f, sprite(14, (255, 214, 120), blur=5), fx, fy + 10 * math.sin(t * 9), 1)
        # eyes open at 12.2, blink at 16.6
        op = ease((t - 12.2) / 0.35)
        if 16.6 < t < 16.85: op *= abs(math.cos((t - 16.6) / 0.25 * math.pi))
        if op > 0.02:
            hx, hy = TRIJATA_HEAD
            for ex in (-10, 10):
                sx, sy = to_screen(hx + ex * 2.3, hy + 2 * 2.3, tf["tj"])
                z = tf["tj"][1]
                e = Image.new("RGBA", (60, 40), (0, 0, 0, 0))
                ImageDraw.Draw(e).ellipse((30 - 9 * z, 20 - 4.5 * z * op, 30 + 9 * z, 20 + 4.5 * z * op), fill=(250, 236, 200, 240))
                ImageDraw.Draw(e).ellipse((30 - 3 * z, 20 - 3 * z * op, 30 + 3 * z, 20 + 3 * z * op), fill=(30, 20, 20, 255))
                put(f, e, sx, sy)
        fireflies(f, t, 0.7)
        return f
    if name == "dream":
        lt = t - 19.0
        u = ease((lt - 4.3) / 4.2)
        pany = lerp(840, -820, u); zoom = lerp(1.0, 1.06, ease(lt / 9.5))
        f, tf = layers_frame([("dream", A["dream"], 1.0, 0, pany, zoom, 0, 0, 1),
                              ("w1", A["wave1"], 1.0, 0, pany, zoom, 22 * math.sin(t * 0.9), 3 * math.sin(t * 1.3), 0.9),
                              ("w2", A["wave2"], 1.0, 0, pany, zoom, -26 * math.sin(t * 0.7 + 1), 0, 0.7)])
        motes(f, t)
        return f
    if name == "warning":
        lt = t - 29.3
        zoom = lerp(1.04, 1.12, ease(lt / 9)); panx = lerp(-25, 25, ease(lt / 9))
        back = 120 * ease((t - 34.6) / 2.6)
        f, tf = layers_frame([("sky", A["sky"], 0.25, panx, 0, zoom, 0, 0, 1), ("far", A["far"], 0.5, panx, 0, zoom, 0, 0, 1),
                              ("mid", A["mid"], 0.75, panx, 0, zoom, 0, 0, 1),
                              ("rk2", A["rk2"], 1.0, panx, 0, zoom, back + 5 * math.sin(t), 0, 1),
                              ("tj", A["tj_st"], 1.1, panx, 0, zoom, 0, 1.5 * math.sin(t * 1.3), 1)])
        fireflies(f, t, 0.5)
        return f
    raise ValueError(name)


def render_frame(A, t):
    def S(n): return scene(A, n, t)
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255)); white = Image.new("RGBA", (W, H), (255, 250, 238, 255))
    tint = None
    if t < 11.2: f = S("garden")
    elif t < 11.8: f = Image.blend(S("garden"), S("trijata"), ease((t - 11.2) / 0.6))
    elif t < 19.0: f = S("trijata")
    elif t < 19.5: f = Image.blend(S("trijata"), white, ease((t - 19.0) / 0.5))
    elif t < 20.1: f = Image.blend(white, S("dream"), ease((t - 19.5) / 0.6))
    elif t < 28.4: f = S("dream")
    elif t < 29.2: f = Image.blend(S("dream"), black, ease((t - 28.4) / 0.8))
    elif t < 29.5: f = black
    elif t < 30.0: f = Image.blend(black, S("warning"), ease((t - 29.5) / 0.5)); tint = 1
    elif t < 38.4: f = S("warning"); tint = 1
    elif t < 38.9:
        f = Image.blend(S("warning"), S("ending"), ease((t - 38.4) / 0.5))
    else: f = S("ending")
    for a, b, img in A["subs"]:
        if a - 0.01 <= t <= b + 0.01:
            al = min(ease((t - a) / 0.25), ease((b - t) / 0.25))
            comp(f, fade_alpha(img, al), 0, SUB_Y)
    if t >= 43.8:
        comp(f, fade_alpha(A["card"], ease((t - 43.8) / 0.8)), 0, 0)
    comp(f, fade_alpha(A["wm"], 0.6), 0, 70)
    arr = np.asarray(f.convert("RGB"), np.float32) * A["post"]
    if tint: arr *= np.array([1.10, 0.88, 0.90], np.float32)
    if t > 48.0: arr *= 1 - ease((t - 48.0) / 1.0)
    return np.clip(arr, 0, 255).astype(np.uint8)


# ───────────────────────── original procedural music ─────────────────────────
def make_audio(path):
    SR = 48000; N = int(DUR * SR)
    out = np.zeros((N, 2), np.float32)
    tt = np.arange(N) / SR

    def add(sig, start, pan=0.5, gain=1.0):
        i = int(start * SR); j = min(N, i + len(sig))
        if j <= i: return
        s = sig[: j - i] * gain
        out[i:j, 0] += s * math.cos(pan * math.pi / 2); out[i:j, 1] += s * math.sin(pan * math.pi / 2)

    def pluck(freq, dur=4.5):
        n = int(dur * SR); x = np.arange(n) / SR; sig = np.zeros(n)
        for k in range(1, 15):
            jaw = 1 + 0.7 * np.sin(2 * np.pi * (0.35 + 0.05 * k) * x)    # jawari-like shimmer
            sig += (1 / k ** 1.05) * jaw * np.sin(2 * np.pi * freq * k * x * (1 + 0.0004 * k)) * np.exp(-x * (0.45 + 0.22 * k))
        return (sig * np.minimum(1, x / 0.008)).astype(np.float32)

    def bell(freq, dur=6.0):
        n = int(dur * SR); x = np.arange(n) / SR
        sig = sum(a * np.sin(2 * np.pi * freq * r * x) * np.exp(-x * d) for a, r, d in [(1, 1, 0.7), (0.5, 2.76, 1.4), (0.25, 5.4, 2.5), (0.12, 8.9, 4)])
        return (sig * np.minimum(1, x / 0.004)).astype(np.float32)

    def thump(dur=0.9):
        n = int(dur * SR); x = np.arange(n) / SR
        f = 70 * np.exp(-x * 6) + 42
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 7)).astype(np.float32)

    SA = 146.83
    # section gain for tanpura
    keys_t = [0, 1.5, 19.0, 20.0, 27.8, 28.6, 29.4, 30.2, 38.4, 39.5, 46.0, 49.0]
    keys_g = [0, 1, 1, 0.7, 0.7, 0.0, 0.0, 0.8, 0.8, 1.0, 0.9, 0.0]
    t0 = 0.0
    while t0 < DUR:
        for off, fr, pan in [(0, SA * 0.75, 0.35), (1.1, SA, 0.55), (2.2, SA, 0.6), (3.3, SA * 0.5, 0.45)]:
            st = t0 + off
            g = float(np.interp(st, keys_t, keys_g))
            if g > 0.01: add(pluck(fr), st, pan, 0.22 * g)
        t0 += 4.4
    # low drone pad
    pad = (np.sin(2 * np.pi * SA / 2 * tt) + 0.5 * np.sin(2 * np.pi * SA * 0.75 * tt + 1) + 0.25 * np.sin(2 * np.pi * SA * tt)) \
        * (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * tt))
    pad_g = np.interp(tt, [0, 2, 19, 20.5, 27.8, 28.6, 29.4, 30.5, 46, 49], [0, 1, 1, 1.3, 1.3, 0, 0, 1, 1, 0])
    out += (pad * pad_g * 0.05)[:, None].astype(np.float32)
    # night crickets (garden / trijata / warning / ending)
    chirp = np.sin(2 * np.pi * 4700 * tt) * (np.sin(2 * np.pi * 30 * tt) > 0) * (np.sin(2 * np.pi * 1.6 * tt) > 0.55)
    cr_g = np.interp(tt, [0, 1, 19, 19.6, 29.6, 31, 46, 49], [0, 1, 1, 0, 0, 0.6, 0.6, 0])
    out[:, 0] += (chirp * cr_g * 0.010).astype(np.float32); out[:, 1] += (np.roll(chirp, 9000) * cr_g * 0.010).astype(np.float32)
    # wind (filtered noise)
    nz = RNG.normal(0, 1, N).astype(np.float32)
    k = np.ones(400, np.float32) / 400
    wind = np.convolve(nz, k, mode="same") * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt))
    out += (wind * 0.18)[:, None].astype(np.float32)
    # dream shimmer bells (pentatonic)
    scale = [1, 9 / 8, 5 / 4, 3 / 2, 5 / 3, 2]
    st = 19.6
    while st < 28.0:
        add(bell(SA * 4 * random.choice(scale)), st, random.uniform(0.2, 0.8), 0.05)
        st += random.uniform(0.6, 1.3)
    # reveal: low boom + bell after the silence
    add(thump(3.0) * 1.2, 29.5, 0.5, 0.5); add(bell(SA * 2), 29.55, 0.5, 0.12)
    # tension pulse during the warning
    st = 30.6
    while st < 38.2:
        add(thump(), st, 0.5, 0.28); st += 0.95
    # resolution bell at the ending + card
    add(bell(SA * 2), 39.0, 0.4, 0.10); add(bell(SA * 3), 43.8, 0.6, 0.10); add(bell(SA * 4), 44.4, 0.5, 0.06)
    out /= max(1e-6, np.abs(out).max()) / 0.85
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())


# ───────────────────────── main ─────────────────────────
def main():
    A = build()
    if "--stills" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]
        os.makedirs(os.path.join(ROOT, "qa"), exist_ok=True)
        for t in ts:
            Image.fromarray(render_frame(A, t)).save(os.path.join(ROOT, "qa", f"still_{t:05.1f}.png"))
            print("still", t, flush=True)
        return
    out = os.path.join(ROOT, "renders", "sample_trijata_v0.mp4")
    wav = os.path.join(ROOT, "audio", "music", "sample_trijata_bed.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True); os.makedirs(os.path.dirname(wav), exist_ok=True)
    print("audio…", flush=True); make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-filter:a", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i in range(n):
        p.stdin.write(render_frame(A, i / FPS).tobytes())
        if i % 150 == 0: print(f"frame {i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print("done ->", out)


if __name__ == "__main__":
    main()
