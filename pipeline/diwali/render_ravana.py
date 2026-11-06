#!/usr/bin/env python3
"""
Diwali Special #1 — "रावण की वो एक भूल" (Ravana's boon; Valmiki Ramayana, Uttara Kanda, Sarga 10)

Full sample pipeline, all local:
  voice  : Piper Hindi TTS (TEMPORARY placeholder voice, non-commercial model) -> pitch/EQ/reverb processing
  visuals: original 2D vector puppet characters drawn with skia (puppets.py), camera moves, FX, Hindi labels
  music  : original procedural score + SFX, styled after the reference reel's *feel* (deep drone, sub-bass hits,
           heavy pauses, -14 LUFS) — no audio is copied from any other video.

Usage: python3 pipeline/diwali/render_ravana.py [--stills t1,t2,...]
Env  : PIPER_MODEL=/path/hi_IN-pratham-medium.onnx
"""
import math, os, random, subprocess, sys
import numpy as np
import skia
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import puppets as P                       # noqa: E402
from script_ravana import LINES, SOURCE   # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
BUILD = os.path.join(ROOT, "build", "ravana")
OUT = os.path.join(ROOT, "renders", "diwali_01_ravana_sample.mp4")
FONT_T = os.path.join(ROOT, "assets/fonts/TiroDevanagariHindi-Regular.ttf")
FONT_B = os.path.join(ROOT, "assets/fonts/NotoSansDevanagari-Bold.ttf")
MODEL = os.environ.get("PIPER_MODEL", "")
random.seed(7); RNG = np.random.default_rng(7)


# ═══════════════════════════ VOICE ═══════════════════════════
def prepare_voice():
    os.makedirs(BUILD, exist_ok=True)
    segs = []
    for i, (k, text, pause, cap) in enumerate(LINES):
        raw = os.path.join(BUILD, f"vo_{i:02d}_raw.wav"); pro = os.path.join(BUILD, f"vo_{i:02d}.wav")
        if not os.path.exists(pro):
            subprocess.run([sys.executable, "-m", "piper", "-m", MODEL, "-f", raw, "--length-scale", "1.0"],
                           input=text.encode(), check=True, capture_output=True)
            # deeper, more cinematic: pitch down ~1.3 semitones keeping formants, resample to 48k
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                            "aresample=48000,rubberband=pitch=0.925:formant=preserved", "-ar", "48000", pro], check=True)
        x, _ = sf.read(pro, dtype="float32")
        idx = np.where(np.abs(x) > 0.03 * np.abs(x).max())[0]
        y = x[max(0, idx[0] - 600): idx[-1] + 4000].copy()
        f = 480; y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
        segs.append((k, y, pause, cap))
    t = 0.35; times = []
    for k, y, pause, cap in segs:
        d = len(y) / SR; times.append((k, t, t + d, cap)); t += d + pause * 0.8
    dur = t + 1.4
    narr = np.zeros(int(dur * SR), np.float32)
    for (k, y, _, _), (_, s, e, _) in zip(segs, times):
        i = int(s * SR); narr[i:i + len(y)] += y
    sf.write(os.path.join(BUILD, "narration.wav"), narr, SR)
    hop = SR // FPS
    env = np.array([np.sqrt((narr[i:i + hop] ** 2).mean()) for i in range(0, len(narr), hop)])
    env = np.clip(env / (np.percentile(env[env > 0.003], 90) + 1e-6), 0, 1)
    env = np.convolve(env, np.ones(3) / 3, mode="same")
    return times, dur, env


# ═══════════════════════════ TEXT IMAGES ═══════════════════════════
_TXT = {}


def text_img(text, font, size, color=(255, 255, 255), glow=None, stroke=0, stroke_col=(30, 16, 20)):
    key = (text, font, size, color, glow, stroke)
    if key in _TXT: return _TXT[key]
    text = text.replace("“", '"').replace("”", '"')
    f = ImageFont.truetype(font, size)
    w = int(f.getlength(text)) + 120; h = int(size * 1.9) + 60
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((60, 30), text, font=f, fill=color + (255,), stroke_width=stroke, stroke_fill=stroke_col + (255,))
    if glow:
        g = Image.new("RGBA", img.size, glow + (0,)); g.putalpha(img.getchannel("A").point(lambda v: int(v * 0.9)))
        g = g.filter(ImageFilter.GaussianBlur(14)); g.alpha_composite(img); img = g
    arr = np.ascontiguousarray(np.array(img))
    sk = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
    _TXT[key] = (sk, w, h); return _TXT[key]


SAMP = skia.SamplingOptions(skia.FilterMode.kLinear)


def draw_img(c, im, x, y, scale=1.0, alpha=1.0):
    sk, w, h = im
    c.save(); c.translate(x, y); c.scale(scale, scale)
    c.drawImage(sk, -w / 2, -h / 2, SAMP, skia.Paint(Alphaf=max(0.0, min(1.0, alpha))))
    c.restore()


def wrap(text, font, size, maxw):
    f = ImageFont.truetype(font, size); out, cur = [], ""
    for wd in text.split(" "):
        tt = (cur + " " + wd).strip()
        if f.getlength(tt) <= maxw or not cur: cur = tt
        else: out.append(cur); cur = wd
    out.append(cur); return out


# ═══════════════════════════ FX / BACKGROUNDS ═══════════════════════════
def ease(u): u = min(1, max(0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u
def pop(lt, d=0.22): return ease(lt / d)


def grad_bg(c, top, bot):
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeLinear(
        [(0, 0), (0, H)], [P.C(top), P.C(bot)])))


STARS = [(random.uniform(0, W), random.uniform(0, H * 0.6), random.uniform(1, 3.2), random.uniform(0, 6.3)) for _ in range(140)]


def stars(c, t, a=1.0):
    for x, y, r, ph in STARS:
        c.drawCircle(x, y, r, P.fill((255, 244, 220), 255 * a * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 2 + ph)))))


def rays(c, cx, cy, t, col, a=0.35, n=20, spin=4.0, length=2600):
    c.save(); c.translate(cx, cy); c.rotate(t * spin)
    for i in range(n):
        c.save(); c.rotate(i * 360 / n)
        p = skia.Path(); p.moveTo(0, 0); p.lineTo(-length * 0.07, -length); p.lineTo(length * 0.07, -length); p.close()
        c.drawPath(p, P.fill(col, 255 * a * (0.6 + 0.4 * math.sin(i * 1.7)), blur=10))
        c.restore()
    c.restore()
    c.drawCircle(cx, cy, 520, skia.Paint(Shader=skia.GradientShader.MakeRadial((cx, cy), 520, [P.C(col, 200 * a + 40), P.C(col, 0)])))


def orbit(c, cx, cy, rx, ry, rot, col, a=1.0, w=6):
    c.save(); c.translate(cx, cy); c.rotate(rot)
    r = skia.Rect.MakeLTRB(-rx, -ry, rx, ry)
    c.drawOval(r, P.stroke(col, w * 3, 160 * a, blur=10)); c.drawOval(r, P.stroke((255, 250, 240), w * 0.6, 230 * a))
    c.restore()


def mountains(c, col, base=1300):
    p = skia.Path(); p.moveTo(0, base)
    for x, y in [(120, base - 260), (260, base - 120), (420, base - 380), (560, base - 170), (720, base - 330), (880, base - 140), (1000, base - 290), (1080, base - 200)]:
        p.lineTo(x, y)
    p.lineTo(W, H); p.lineTo(0, H); p.close(); c.drawPath(p, P.fill(col))


def flame(c, x, y, s, t, k=1.0):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.drawCircle(0, -90, 170 * k, P.fill((255, 140, 40), 120, blur=60))
    for j, (col, sc) in enumerate([((214, 60, 30), 1.0), ((246, 132, 34), 0.78), ((255, 214, 90), 0.52), ((255, 248, 210), 0.28)]):
        for m in range(5 if j == 0 else 3):
            ox = (m - (2 if j == 0 else 1)) * 34 * sc
            hgt = (190 + 50 * math.sin(t * 9 + m * 1.3 + j)) * sc * k
            sw = 6 * math.sin(t * 7 + m)
            p = skia.Path(); p.moveTo(ox - 44 * sc, 0); p.cubicTo(ox - 50 * sc, -hgt * 0.45, ox + sw - 10 * sc, -hgt * 0.75, ox + sw, -hgt)
            p.cubicTo(ox + sw + 12 * sc, -hgt * 0.7, ox + 50 * sc, -hgt * 0.4, ox + 44 * sc, 0); p.close()
            c.drawPath(p, P.fill(col, 235))
    c.restore()


def havan(c, x, y, s, t, k=1.0):
    flame(c, x, y - 60 * s, s, t, k)
    c.save(); c.translate(x, y); c.scale(s, s)
    for i, (w_, h_) in enumerate([(300, 46), (250, 42), (200, 40)]):
        r = skia.Path(); r.addRect(skia.Rect.MakeXYWH(-w_ / 2, -i * 40 - 20, w_, h_)); P.shape(c, r, (150, 64, 40) if i % 2 == 0 else (176, 82, 48), ow=5)
    c.restore()


EMB = [(random.uniform(-300, 300), random.uniform(0, 1), random.uniform(40, 110), random.uniform(0, 6.3)) for _ in range(40)]


def embers(c, x, y, t, a=1.0):
    for ox, ph, sp, w in EMB:
        yy = y - ((t * sp + ph * 900) % 900)
        c.drawCircle(x + ox + 30 * math.sin(t + w), yy, 4, P.fill((255, 190, 90), 230 * a * (1 - ((t * sp + ph * 900) % 900) / 900), blur=2))


SPK = [(random.uniform(0, 6.28), random.uniform(80, 520), random.uniform(0, 1)) for _ in range(70)]


def sparkle(c, cx, cy, t, a=1.0, col=(255, 230, 140)):
    for ang, r, ph in SPK:
        rr = r * (0.6 + 0.4 * math.sin(t * 1.3 + ph * 6))
        x, y = cx + math.cos(ang + t * 0.4) * rr, cy + math.sin(ang + t * 0.4) * rr * 0.8
        s = 3 + 3 * (0.5 + 0.5 * math.sin(t * 5 + ph * 10))
        c.drawCircle(x, y, s, P.fill(col, 255 * a, blur=1.5))


def burst(c, cx, cy, lt, col=(255, 210, 110), n=26, dur=0.7):
    if lt < 0 or lt > dur: return
    u = lt / dur
    for i in range(n):
        ang = i * 6.283 / n + i
        r = 60 + 420 * ease(u) * (0.6 + 0.4 * math.sin(i * 3.1))
        c.drawCircle(cx + math.cos(ang) * r, cy + math.sin(ang) * r, 7 * (1 - u) + 2, P.fill(col, 255 * (1 - u), blur=2))
    c.drawCircle(cx, cy, 180 * (0.4 + u), P.fill(col, 200 * (1 - u), blur=50))


def vignette(c, a=170):
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (W / 2, H * 0.47), H * 0.72, [P.C((0, 0, 0), 0), P.C((0, 0, 0), 0), P.C((0, 0, 0), a)], [0, 0.55, 1.0])))


def overlay(c, rgb, a):
    if a > 0.003: c.drawRect(skia.Rect.MakeWH(W, H), P.fill(rgb, 255 * min(1, a)))


def diya(c, x, y, s, t, lit, ph=0):
    c.save(); c.translate(x, y); c.scale(s, s)
    if lit > 0:
        c.drawCircle(0, -40, 90, P.fill((255, 170, 60), 120 * lit, blur=40))
        fh = 46 + 6 * math.sin(t * 11 + ph)
        p = skia.Path(); p.moveTo(-12, -14); p.cubicTo(-14, -fh * 0.6, -2, -fh * 0.8, 0, -fh); p.cubicTo(3, -fh * 0.8, 14, -fh * 0.6, 12, -14); p.close()
        c.drawPath(p, P.fill((255, 196, 70), 255 * lit)); c.drawCircle(0, -22, 6, P.fill((255, 250, 220), 255 * lit))
    b = skia.Path(); b.moveTo(-46, -14); b.quadTo(0, 30, 46, -14); b.lineTo(30, -16); b.quadTo(0, -8, -30, -16); b.close()
    P.shape(c, b, (190, 90, 46), ow=4)
    c.restore()


DIYA_POS = [(x, y) for y in (1520, 1640, 1780) for x in np.linspace(80, 1000, 7 if y != 1640 else 6) + (0 if y != 1640 else 75)]


def ayodhya(c, t, lit_frac):
    grad_bg(c, (20, 18, 60), (96, 40, 90)); stars(c, t, 0.8)
    c.drawCircle(820, 330, 70, P.fill((255, 238, 200))); c.drawCircle(820, 330, 160, P.fill((255, 220, 160), 70, blur=60))
    base = 1430
    for x0, wd, ht, dome in [(-40, 260, 380, True), (180, 200, 520, True), (360, 360, 640, True), (700, 200, 470, True), (880, 260, 360, True)]:
        r = skia.Path(); r.addRect(skia.Rect.MakeLTRB(x0, base - ht, x0 + wd, base)); c.drawPath(r, P.fill((44, 26, 70)))
        c.drawPath(P.oval(x0 + wd / 2, base - ht, wd * 0.36, wd * 0.3), P.fill((44, 26, 70)))
        sp = skia.Path(); sp.moveTo(x0 + wd / 2 - 8, base - ht - wd * 0.26); sp.lineTo(x0 + wd / 2, base - ht - wd * 0.26 - 70); sp.lineTo(x0 + wd / 2 + 8, base - ht - wd * 0.26); sp.close()
        c.drawPath(sp, P.fill((44, 26, 70)))
        for j in range(5):
            wx = x0 + 30 + (j * 53) % max(60, wd - 60); wy = base - 60 - (j * 97) % max(80, ht - 120)
            c.drawRoundRect(skia.Rect.MakeXYWH(wx, wy, 26, 40), 12, 12, P.fill((255, 190, 90), 255 * min(1, lit_frac * 1.6)))
    c.drawRect(skia.Rect.MakeLTRB(0, base, W, H), P.fill((52, 26, 40)))
    n = len(DIYA_POS)
    for i, (x, y) in enumerate(DIYA_POS):
        lit = ease((lit_frac * n - i) / 1.0)
        diya(c, x, y, 1.0, t, lit, i)


PET = [(random.uniform(0, W), random.uniform(0, H), random.uniform(60, 140), random.uniform(0, 6.3)) for _ in range(40)]


def petals(c, t):
    for x, y, sp, ph in PET:
        yy = (y + t * sp) % (H + 60) - 30
        c.drawOval(skia.Rect.MakeXYWH(x + 40 * math.sin(t + ph), yy, 18, 12), P.fill((250, 150, 30) if int(ph * 10) % 2 else (240, 90, 40), 230))


def straw(c, x, y, rot, s=1.0):
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    p = skia.Path(); p.moveTo(-180, 10); p.cubicTo(-60, -20, 60, -30, 190, -6); p.cubicTo(60, -10, -60, 6, -180, 10); p.close()
    c.drawPath(p, P.fill((222, 190, 92))); c.drawPath(p, P.stroke((120, 90, 30), 3))
    c.restore()


def blink(t, ph=0.0):
    x = (t + ph) % 3.4
    return 1.0 - abs(x - 0.08) / 0.08 if x < 0.16 else 0.0


# ═══════════════════════════ SHOTS ═══════════════════════════
class Ctx:
    pass


def cam(c, cx, cy, z, shake=0.0, t=0.0):
    sx = shake * math.sin(t * 61) * 14; sy = shake * math.cos(t * 53) * 14
    c.translate(W / 2 + sx, H / 2 + sy); c.scale(z, z); c.translate(-cx, -cy)


RAV_SIL = dict(P.RAVANA, skin=(40, 22, 34), dhoti=(50, 20, 36), sash=(40, 20, 40))


def build_shots(times, dur):
    T = {k: (s, e) for k, s, e, _ in times}
    nxt = {}
    for i, (k, s, e, _) in enumerate(times):
        nxt[k] = times[i + 1][1] if i + 1 < len(times) else dur
    def win(k, a=0.0, b=1.0):
        s = T[k][0] if k != "hook" else 0.0
        e = nxt[k]; return (s + (e - s) * a, s + (e - s) * b)
    shots = []
    def add(rng, fn, label=None, lcol=(255, 255, 255), lglow=(255, 170, 60)):
        shots.append((rng[0], rng[1], fn, label, lcol, lglow))

    # 1 hook: ECU on Ravana's eyes
    def s_hook(c, t, lt, u):
        grad_bg(c, (30, 12, 50), (90, 30, 80)); rays(c, 540, 760, t, (150, 60, 200), 0.3)
        c.save(); cam(c, 540, 770, lerp(2.5, 2.3, u)); P.figure(c, 540, 1750, 1.15, P.RAVANA, dict(eyes="glow" if lt > 0.5 else "open", brow=1, blink=0, smile=0.1), t); c.restore()
        vignette(c, 200)
    add(win("hook"), s_hook, "रावण", (255, 236, 200))

    # 2 hook2: pull back to all ten heads
    def s_reveal(c, t, lt, u):
        grad_bg(c, (30, 12, 50), (110, 36, 90)); rays(c, 540, 760, t, (220, 120, 255), 0.35)
        orbit(c, 540, 760, 560, 130, -8 + 3 * math.sin(t), (200, 140, 255), 0.9)
        c.save(); cam(c, 540, lerp(770, 980, ease(lt / 1.3)), lerp(2.3, 1.0, ease(lt / 1.3)))
        P.figure(c, 540, 1750, 1.15, P.RAVANA, dict(eyes="glow", brow=1, smile=0.2, la=20, ra=20), t); c.restore()
        vignette(c)
    add(win("hook2", 0, 0.5), s_reveal, "अमरता?", (255, 236, 200), (200, 120, 255))

    def s_bhool(c, t, lt, u):
        grad_bg(c, (60, 8, 20), (140, 30, 40)); rays(c, 540, 700, t, (255, 80, 60), 0.25)
        c.save(); cam(c, 540, 860, 1.55, shake=0.4 if lt > 0.5 else 0, t=t)
        P.figure(c, 540, 1750, 1.15, P.RAVANA, dict(eyes="glow", brow=1.4, smile=-0.3, la=30, le=40, ra=30, re=40), t); c.restore()
        vignette(c, 210)
    add(win("hook2", 0.5, 1), s_bhool, "एक भूल", (255, 220, 200), (255, 60, 40))

    # 3 tapas: wide night, seated Ravana, havan
    def tapas_scene(c, t, lt, u, z, cy, pose, k=1.0):
        grad_bg(c, (10, 12, 40), (60, 30, 90)); stars(c, t)
        c.drawCircle(860, 300, 60, P.fill((250, 240, 210))); c.drawCircle(860, 300, 140, P.fill((250, 240, 210), 60, blur=50))
        mountains(c, (34, 22, 60), 1320)
        c.save(); cam(c, 540, cy, z)
        P.figure(c, 540, 1460, 0.82, P.RAVANA, pose, t)
        havan(c, 540, 1700, 1.0, t, k); embers(c, 540, 1600, t)
        c.restore(); vignette(c)
    add(win("tapas"), lambda c, t, lt, u: tapas_scene(c, t, lt, u, lerp(1.0, 1.08, u), 1050, dict(seated=True, eyes="closed", fold=True, smile=0.1)), "तपस्या", (255, 236, 200))

    # 4 head: raise sword / offering
    add(win("head", 0, 0.5), lambda c, t, lt, u: tapas_scene(c, t, lt, u, lerp(1.35, 1.45, u), 1050,
        dict(seated=True, eyes="open", brow=0.6, ra=lerp(30, 165, ease(lt / 0.8)), re=-30, hold_r="sword", la=25, le=110), 1.2),
        "बलिदान", (255, 220, 190), (255, 90, 40))

    def s_offer(c, t, lt, u):
        grad_bg(c, (40, 10, 20), (120, 40, 30))
        c.save(); cam(c, 540, 1500, 1.9)
        havan(c, 540, 1700, 1.0, t, 1.0 + 0.6 * ease((u - 0.75) / 0.25)); embers(c, 540, 1600, t)
        hy = lerp(1230, 1480, ease(u / 0.8)); a = 1 - ease((u - 0.7) / 0.2)
        c.drawCircle(540, hy, 110, P.fill((255, 220, 120), 160 * a, blur=40))
        c.drawPath(P.oval(540, hy, 62, 74), P.stroke((255, 240, 190), 6, 255 * a))
        cp = skia.Path(); cp.moveTo(-50, -60); cp.lineTo(-40, -120); cp.lineTo(0, -160); cp.lineTo(40, -120); cp.lineTo(50, -60)
        c.save(); c.translate(540, hy); c.drawPath(cp, P.stroke((255, 230, 150), 6, 255 * a)); c.restore()
        burst(c, 540, 1480, (u - 0.78) * 2.2)
        c.restore(); vignette(c)
    add(win("head", 0.5, 1), s_offer, "अर्पण", (255, 220, 190), (255, 120, 40))

    # 5 count: 1,2,3...9 heads vanish
    cs, ce = win("count")
    beats = [cs + (ce - cs) * f for f in (0.02, 0.22, 0.42, 0.66)]
    nums = ["१", "२", "३", "९"]; gone = [1, 2, 3, 9]
    def s_count(c, t, lt, u):
        j = max([i for i, b in enumerate(beats) if t >= b] or [-1])
        shown = 10 - (gone[j] if j >= 0 else 0)
        punch = 0.08 * math.exp(-(t - beats[j]) * 6) if j >= 0 else 0
        grad_bg(c, (40, 10, 30), (110, 30, 50)); rays(c, 540, 860, t, (255, 90, 50), 0.25)
        c.save(); cam(c, 540, 1080, 1.1 + punch)
        P.figure(c, 540, 1460, 0.82, P.RAVANA, dict(seated=True, eyes="closed", fold=True, heads_shown=shown, brow=0.5), t)
        havan(c, 540, 1700, 1.0, t, 1.0 + 3 * punch); embers(c, 540, 1600, t)
        if j >= 0: burst(c, 540, 1560, t - beats[j], (255, 160, 60))
        c.restore()
        if j >= 0:
            lt2 = t - beats[j]
            draw_img(c, text_img(nums[j], FONT_T, 300, (255, 214, 110), (255, 120, 40)), 540, 430, lerp(1.6, 1.0, ease(lt2 / 0.18)), ease(lt2 / 0.1))
        vignette(c)
    add((cs, ce), s_count)

    # 6 tenth: freeze, then Brahma appears
    def s_tenth(c, t, lt, u):
        grad_bg(c, (20, 10, 30), (70, 30, 60))
        c.save(); cam(c, 540, 900, lerp(1.5, 1.7, u))
        P.figure(c, 540, 1460, 0.82, P.RAVANA, dict(seated=True, heads_shown=1, eyes="open", brow=1, ra=165, re=-35, hold_r="sword", la=25, le=110), t)
        havan(c, 540, 1700, 1.0, t); c.restore()
        overlay(c, (255, 255, 255), ease((u - 0.82) / 0.18)); vignette(c)
    add(win("tenth", 0, 0.45), s_tenth, "दसवाँ सिर", (255, 236, 200), (255, 90, 40))

    def brahma_scene(c, t, lt, u, z, cy, pose, rise=False, flash=0.0):
        grad_bg(c, (70, 30, 10), (200, 120, 40)); rays(c, 540, 900, t, (255, 220, 120), 0.55, spin=8)
        orbit(c, 540, 820, 470, 110, -10 + 4 * math.sin(t), (255, 220, 140))
        sparkle(c, 540, 900, t)
        c.save(); cam(c, 540, cy, z)
        yb = lerp(2300, 1800, ease(lt / 1.0)) if rise else 1800
        P.lotus(c, 540, yb + 20, 2.2)
        P.figure(c, 540, yb - 60, 0.95, P.BRAHMA, pose, t)
        c.restore()
        overlay(c, (255, 255, 255), flash); vignette(c, 120)
    add(win("tenth", 0.45, 1), lambda c, t, lt, u: brahma_scene(c, t, lt, u, 1.0, 1000, dict(ra=50, re=-60, la=20, le=20, smile=0.6, blink=blink(t)), True, 1 - ease(lt / 0.35)),
        "ब्रह्मा जी", (255, 250, 230), (255, 190, 60))

    # 7 ask: Ravana pleads (lip-sync)
    def s_ask(c, t, lt, u):
        grad_bg(c, (30, 14, 60), (100, 50, 110)); rays(c, 540, 0, t, (255, 210, 120), 0.4)
        c.save(); cam(c, 540, 950, lerp(1.3, 1.4, u))
        P.figure(c, 540, 1750, 1.0, P.RAVANA, dict(heads_shown=1, fold=True, eyes="open", look=0, tilt=-6, mouth=CTX.lip(t), smile=0, blink=blink(t, 1)), t)
        c.restore(); vignette(c)
    add(win("ask"), s_ask, "अमरता", (255, 236, 200), (200, 120, 255))

    # 8 deny: Brahma refuses
    add(win("deny", 0, 0.5), lambda c, t, lt, u: brahma_scene(c, t, lt, u, 1.45, 820, dict(ra=150, re=-70, la=20, le=20, mouth=CTX.lip(t), tilt=4 * math.sin(t * 5), smile=0.2, blink=blink(t))),
        "असंभव", (255, 250, 230), (255, 120, 40))
    add(win("deny", 0.5, 1), lambda c, t, lt, u: brahma_scene(c, t, lt, u, 1.15, 950, dict(ra=60, re=-60, la=20, le=20, mouth=CTX.lip(t), smile=0.5, blink=blink(t))),
        "कुछ और माँगो", (255, 250, 230), (255, 190, 60))

    # 9 boon: heads restored + foes orbit
    bs, be = win("boon")
    def boon_scene(c, t, lt, u, words_from, miss=0.0, laugh=False, zoom=1.0, cy=980):
        grad_bg(c, (24, 8, 46), (110, 30, 80)); rays(c, 540, 760, t, (200, 100, 255), 0.35 * (1 - 0.7 * miss))
        orbit(c, 540, 820, 500, 150, -12, (210, 150, 255), 1 - 0.6 * miss)
        rb = (t - bs) / 1.4
        shown = int(1 + 9 * ease(rb)) if rb < 1 else 10
        c.save(); cam(c, 540, cy, zoom)
        pose = dict(heads_shown=shown, eyes="glow", brow=1, la=150, le=-20, ra=150, re=-20, smile=0.3)
        if laugh: pose.update(mouth=0.6 + 0.4 * abs(math.sin(t * 9)), tilt=-7, la=40, le=60, ra=40, re=60)
        P.figure(c, 540, 1750, 1.0, P.RAVANA, pose, t)
        if rb < 1.2: sparkle(c, 540, 820, t, 1 - ease((rb - 0.8) / 0.4))
        c.restore()
        words = ["देवता", "दानव", "यक्ष", "नाग"]
        pos = [(200, 640), (880, 640), (170, 1180), (910, 1180)]
        for i, (wd, (x, y)) in enumerate(zip(words, pos)):
            wt = words_from + i * 0.75
            if t < wt: continue
            a = ease((t - wt) / 0.2) * (1 - 0.65 * miss)
            sc = lerp(1.4, 1.0, ease((t - wt) / 0.2))
            c.save(); c.translate(x, y + 8 * math.sin(t * 2 + i)); c.scale(sc, sc)
            c.drawRoundRect(skia.Rect.MakeXYWH(-130, -55, 260, 110), 55, 55, P.fill((60, 20, 80), 230 * a))
            c.drawRoundRect(skia.Rect.MakeXYWH(-130, -55, 260, 110), 55, 55, P.stroke((255, 200, 120), 5, 255 * a))
            c.restore()
            draw_img(c, text_img(wd, FONT_B, 52, (255, 240, 220)), x, y + 8 * math.sin(t * 2 + i) - 4, sc, a)
        if miss > 0:
            overlay(c, (0, 0, 0), 0.45 * miss)
            x, y = 540, 1230; pa = ease(miss * 2)
            c.drawCircle(x, y, 120, P.stroke((255, 80, 70), 7, 255 * pa, dash=[22, 14]))
            c.drawCircle(x, y, 140, P.fill((255, 60, 50), 80 * pa, blur=40))
            draw_img(c, text_img("मनुष्य", FONT_B, 56, (255, 120, 110)), x, y - 4, 1.0, pa)
        vignette(c)
    add((bs, bs + (be - bs) * 0.3), lambda c, t, lt, u: boon_scene(c, t, lt, u, 1e9), "वरदान", (255, 236, 200), (255, 190, 60))
    add((bs + (be - bs) * 0.3, be), lambda c, t, lt, u: boon_scene(c, t, lt, u, bs + (be - bs) * 0.32, zoom=0.95, cy=1000), "कोई मार न सके", (255, 236, 200), (200, 120, 255))
    ms, me = win("miss")
    add((ms, me), lambda c, t, lt, u: boon_scene(c, t, lt, u, bs + (be - bs) * 0.32, miss=ease(lt / 0.8), zoom=lerp(0.95, 1.12, u), cy=lerp(1000, 1150, u)),
        "मनुष्य?", (255, 140, 120), (255, 40, 30))

    # 10 straw: arrogance
    def s_straw(c, t, lt, u):
        grad_bg(c, (40, 6, 20), (120, 20, 40)); rays(c, 540, 760, t, (255, 90, 60), 0.3)
        c.save(); cam(c, 540, 900, 1.4, shake=0.15, t=t)
        P.figure(c, 540, 1750, 1.0, P.RAVANA, dict(eyes="glow", brow=1, mouth=0.55 + 0.45 * abs(math.sin(t * 8)), tilt=-6, la=40, le=70, ra=40, re=70), t)
        c.restore()
        straw(c, lerp(-200, 1250, u), 1300 + 40 * math.sin(t * 2), 12 * math.sin(t * 1.5), 1.1)
        vignette(c, 200)
    add(win("straw"), s_straw, "अहंकार", (255, 210, 200), (255, 40, 30))

    # 11 rama: entrance + arrow
    rs, re_ = win("rama")
    def s_rama(c, t, lt, u):
        grad_bg(c, (30, 30, 80), (230, 150, 60)); rays(c, 540, 820, t, (255, 230, 150), 0.6, spin=6)
        orbit(c, 540, 760, 360, 90, -10, (255, 230, 160)); sparkle(c, 540, 900, t)
        c.save(); cam(c, 540, 1000, lerp(1.25, 1.1, ease(lt / 1.2)))
        P.figure(c, 540, 1760, 1.0, P.RAMA, dict(hold_l="bow", la=8, le=0, ra=20, re=30, smile=0.6, blink=blink(t, 2)), t)
        c.restore(); overlay(c, (0, 0, 0), 1 - ease(lt / 0.5)); vignette(c, 120)
    add((rs, rs + (re_ - rs) * 0.62), s_rama, "श्री राम", (255, 250, 230), (80, 150, 255))
    def s_arrow(c, t, lt, u):
        grad_bg(c, (40, 6, 20), (170, 40, 30))
        c.drawCircle(540, 520, 230, P.fill((20, 6, 10))); c.drawCircle(540, 520, 250, P.stroke((255, 140, 60), 10, 200, blur=8))
        c.save(); cam(c, 700, 1100, 1.0)
        P.figure(c, 760, 1800, 0.9, RAV_SIL, dict(eyes="glow", brow=1, la=60, le=40, ra=60, re=40), t)
        c.restore()
        k = ease(u / 0.55); x0, y0, x1, y1 = -100, 1700, 760, 820
        xa, ya = lerp(x0, x1, k), lerp(y0, y1, k)
        c.drawLine(lerp(x0, x1, max(0, k - 0.35)), lerp(y0, y1, max(0, k - 0.35)), xa, ya, P.stroke((180, 220, 255), 30, 200, blur=12))
        c.drawLine(lerp(x0, x1, max(0, k - 0.35)), lerp(y0, y1, max(0, k - 0.35)), xa, ya, P.stroke((255, 255, 255), 8))
        burst(c, x1, y1, (u - 0.55) * 1.6, (255, 240, 200), 40)
        overlay(c, (255, 255, 255), ease((u - 0.55) / 0.1) * (1 - ease((u - 0.7) / 0.3)))
        vignette(c)
    add((rs + (re_ - rs) * 0.62, re_), s_arrow, "विजय", (255, 250, 230), (255, 170, 60))

    # 12 diwali: Ayodhya lights up, trio returns
    ds, de = win("diwali")
    def s_ayo(c, t, lt, u):
        c.save(); cam(c, lerp(500, 580, u), 960, 1.06); ayodhya(c, t, ease(u * 1.1)); c.restore(); vignette(c, 130)
    add((ds, ds + (de - ds) * 0.45), s_ayo, "दीपावली", (255, 236, 200), (255, 170, 60))
    def trio(c, t, lt, u, z, cy, cx=540, lit=1.0, halo=False):
        ayodhya(c, t, lit)
        if halo: rays(c, 540, 820, t, (255, 220, 140), 0.35); orbit(c, 540, 700, 420, 100, -8, (255, 220, 150))
        c.save(); cam(c, cx, cy, z)
        P.figure(c, 270, 1880, 0.82, P.LAKSHMANA, dict(hold_r="bow", ra=8, re=0, smile=0.5, blink=blink(t, 0.7)), t)
        P.figure(c, 810, 1880, 0.86, P.RAMA, dict(hold_l="bow", la=8, le=0, ra=40, re=60, smile=0.6, blink=blink(t, 1.9)), t)
        P.figure(c, 540, 1860, 0.8, P.SITA, dict(fold=True, smile=0.6, blink=blink(t, 2.6)), t)
        c.restore(); petals(c, t); vignette(c, 120)
    add((ds + (de - ds) * 0.45, de), lambda c, t, lt, u: trio(c, t, lt, u, lerp(1.0, 1.06, u), 1100), "अयोध्या", (255, 236, 200), (255, 170, 60))

    # 13 cta
    cs2, ce2 = win("cta")
    add((cs2, cs2 + (ce2 - cs2) * 0.45), lambda c, t, lt, u: trio(c, t, lt, u, 1.65, 860, cx=810, halo=True), "अहंकार का अंत", (255, 236, 200), (255, 120, 40))
    def s_cta(c, t, lt, u):
        trio(c, t, lt, u, 1.0, 1100, halo=True)
        a = ease(lt / 0.3); x, y = 540, 1210
        c.save(); c.translate(x, y); c.scale(lerp(0.6, 1.0, a), lerp(0.6, 1.0, a))
        b = skia.Path(); b.addRoundRect(skia.Rect.MakeXYWH(-230, -70, 460, 140), 70, 70)
        b.moveTo(-60, 66); b.lineTo(-110, 120); b.lineTo(-10, 68); b.close()
        c.drawPath(b, P.fill((255, 255, 255), 240 * a)); c.drawPath(b, P.stroke((255, 170, 60), 6, 255 * a))
        c.restore()
        draw_img(c, text_img("जय श्री राम", FONT_B, 64, (200, 60, 20)), x, y - 4, lerp(0.6, 1.0, a), a)
        draw_img(c, text_img(SOURCE, FONT_T, 34, (255, 240, 220), (0, 0, 0)), 540, 470, 1.0, ease((lt - 0.6) / 0.4) * 0.9)
    add((cs2 + (ce2 - cs2) * 0.45, dur), s_cta, "कमेंट करें", (255, 236, 200), (255, 170, 60))
    return shots


# ═══════════════════════════ FRAME ═══════════════════════════
CTX = Ctx()


def render_frame(surface, shots, times, t, dur):
    c = surface.getCanvas(); c.clear(skia.ColorBLACK)
    for (s, e, fn, label, lcol, lglow) in shots:
        if s <= t < e or (e >= dur and t >= s):
            lt, u = t - s, (t - s) / max(1e-6, e - s)
            c.save(); fn(c, t, lt, u); c.restore()
            if label:
                a = pop(lt, 0.18)
                draw_img(c, text_img(label, FONT_T, 92, lcol, lglow), 540, 330, lerp(1.35, 1.0, a), a)
            break
    # captions (lower third, above platform UI)
    for k, s, e, cap in times:
        if s - 0.05 <= t <= e + 0.25:
            a = min(ease((t - s + 0.05) / 0.15), ease((e + 0.25 - t) / 0.15))
            lines = wrap(cap, FONT_B, 50, 900)
            for i, ln in enumerate(lines):
                draw_img(c, text_img(ln, FONT_B, 50, (255, 255, 255), stroke=6, stroke_col=(20, 10, 30)), 540, 1440 + i * 80 - (len(lines) - 1) * 40, 1.0, a)
    if t > dur - 0.6: overlay(c, (0, 0, 0), ease((t - (dur - 0.6)) / 0.6))
    return surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3]


# ═══════════════════════════ ORIGINAL SCORE + SFX ═══════════════════════════
def make_score(times, dur, shots):
    N = int(dur * SR); tt = np.arange(N) / SR
    out = np.zeros((N, 2), np.float32)
    T = {k: (s, e) for k, s, e, _ in times}

    def add(sig, at, gain=1.0, pan=0.5):
        i = int(at * SR); j = min(N, i + len(sig))
        if j <= i or i < 0: return
        s = sig[: j - i].astype(np.float32) * gain
        out[i:j, 0] += s * math.cos(pan * math.pi / 2); out[i:j, 1] += s * math.sin(pan * math.pi / 2)

    def env_t(d): return np.arange(int(d * SR)) / SR

    def sub(d=2.2, f0=55):
        x = env_t(d); f = f0 * (1 + 1.6 * np.exp(-x * 9)); return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 1.6)

    def dhol(d=0.7):
        x = env_t(d); f = 95 * np.exp(-x * 10) + 60
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9)
        slap = RNG.normal(0, 1, len(x)) * np.exp(-x * 60) * 0.35
        return body + slap

    def bell(f, d=4.0):
        x = env_t(d)
        return sum(a * np.sin(2 * np.pi * f * r * x) * np.exp(-x * dd) for a, r, dd in [(1, 1, 0.9), (0.5, 2.76, 1.8), (0.3, 5.4, 3), (0.15, 8.9, 5)])

    def noise_sweep(d=0.5, up=True):
        x = env_t(d); n = RNG.normal(0, 1, len(x))
        k = 30 if up else 6
        sm = np.convolve(n, np.ones(k) / k, mode="same")
        e = np.sin(np.pi * x / d) ** 2
        return (n - sm) * e * 0.5

    def riser(d=1.4):
        x = env_t(d); f = 200 + 1400 * (x / d) ** 2
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + RNG.normal(0, 1, len(x)) * 0.15) * (x / d) ** 2

    def thunder(d=2.5):
        x = env_t(d); n = RNG.normal(0, 1, len(x))
        lp = np.convolve(n, np.ones(60) / 60, mode="same")
        return lp * np.exp(-x * 1.4) * 6 + n * np.exp(-x * 25) * 0.4

    # drone bed (D minor-ish), section gains
    D = 73.42
    def pad(freqs, det=0.25):
        s = np.zeros(N)
        for f in freqs:
            for d in (-det, 0, det):
                for h, a in [(1, 1), (2, 0.35), (3, 0.18), (4, 0.08)]:
                    s += a * np.sin(2 * np.pi * (f + d) * h * tt + h * f)
        return s / (len(freqs) * 3)
    dark = pad([D, D * 1.5, D * 2 * 1.189]) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.09 * tt))
    bright = pad([D, D * 1.5, D * 2 * 1.26, D * 3])
    rs = T["rama"][0]; ds = T["diwali"][0]; ms, me = T["miss"]
    g_dark = np.interp(tt, [0, 0.4, ms - 0.3, ms, me + 0.9, rs, rs + 0.5, dur], [0, 1, 1, 0.0, 0.0, 0.6, 0, 0])
    g_bright = np.interp(tt, [0, rs, rs + 0.6, dur - 1.5, dur], [0, 0, 1, 1, 0])
    out += ((dark * g_dark * 0.11 + bright * g_bright * 0.09))[:, None].astype(np.float32)
    # air / wind
    n = RNG.normal(0, 1, N); air = np.convolve(n, np.ones(300) / 300, mode="same") * 6
    out += (air * 0.02 * np.interp(tt, [0, ms, ms + 0.3, me, me + 0.5, dur], [1, 1, 0.3, 0.3, 1, 1]))[:, None].astype(np.float32)

    # hits
    add(sub(), 0.02, 0.9)
    s2, e2 = T["hook2"]; add(sub(2.5, 48), e2 - 0.6, 0.9); add(thunder(), e2 - 0.6, 0.35)
    for b in [T["count"][0] + (T["count"][1] - T["count"][0] + 0.8) * f for f in (0.02, 0.22, 0.42, 0.66)]:
        add(dhol(), b - 0.02, 0.9); add(sub(1.0, 60), b, 0.4)
    ts, te = T["tenth"]; tb = ts + (T["ask"][0] - ts) * 0.45
    add(riser(1.4), tb - 1.4, 0.45); add(thunder(), tb, 0.5); add(sub(2.6, 50), tb, 0.8)
    for i, f in enumerate([D * 8, D * 10, D * 12, D * 16]): add(bell(f), tb + 0.05 + i * 0.12, 0.12, 0.3 + 0.13 * i)
    # choir-ish pad in Brahma section
    bs_, be_ = tb, T["boon"][0]
    x = env_t(be_ - bs_)
    ch = sum(np.sin(2 * np.pi * f * x) * (1 + 0.3 * np.sin(2 * np.pi * 5 * x)) for f in [D * 4, D * 5, D * 6]) / 3
    ch *= np.minimum(1, x / 0.8) * np.minimum(1, (x[-1] - x) / 0.8)
    add(ch, bs_, 0.07)
    # boon: restore sparkles + tension dhol pulse
    bs, be = T["boon"]
    for i in range(9): add(bell(D * (16 + i * 2)), bs + i * 0.15, 0.04, 0.2 + 0.07 * i)
    t0 = bs + 1.5
    while t0 < T["miss"][0] - 0.3: add(dhol(0.5), t0, 0.45); t0 += 0.62
    # miss: silence then heartbeat
    add(dhol(0.6), ms + 0.5, 0.6); add(dhol(0.6), ms + 0.75, 0.45)
    add(sub(2.4, 45), me - 0.2, 0.7)
    # straw: low drone pulse
    ss, se = T["straw"]; add(noise_sweep(0.6), ss, 0.5)
    # rama: big hit, bells, heroic dhol
    add(sub(2.8, 50), rs, 1.0); add(thunder(), rs, 0.3)
    for i, f in enumerate([D * 4, D * 6, D * 8]): add(bell(f, 5), rs + 0.05 + i * 0.1, 0.13)
    t0 = rs + 0.8
    while t0 < T["diwali"][0] + 0.2: add(dhol(0.5), t0, 0.55); t0 += 0.42
    ra_end = T["diwali"][0]; add(riser(0.8), ra_end - 1.0, 0.3); add(sub(1.8, 60), ra_end - 0.2, 0.6)
    # diwali: lamp tings + bansuri-style melody (original phrase)
    de = T["diwali"][1]
    for i in range(20): add(bell(D * 16 * (1.0 + 0.125 * (i % 5))), ds + i * (de - ds) * 0.45 / 20, 0.035, 0.2 + 0.03 * i)
    mel = [(0, 2), (2, 1), (4, 1), (7, 2), (4, 1), (2, 1), (0, 3), (7, 1), (9, 2), (7, 2), (4, 3)]
    st = ds + 0.3
    for semi, beats in mel:
        d = beats * 0.42; x = env_t(d + 0.3); f = D * 4 * 2 ** (semi / 12) * (1 + 0.006 * np.sin(2 * np.pi * 5.5 * x))
        tone = (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.25 * RNG.normal(0, 1, len(x)) * 0.1) * np.minimum(1, x / 0.06) * np.exp(-np.maximum(0, x - d) * 12)
        add(tone, st, 0.09, 0.55); st += d
        if st > dur - 1: break
    # cta: final dhol + bell
    cs, ce = T["cta"]
    for k in range(4): add(dhol(0.5), cs + 0.1 + k * 0.4, 0.4)
    add(bell(D * 8, 5), ce - 0.2, 0.15); add(sub(2.0, 55), ce - 0.2, 0.6)
    # whoosh on every cut
    for (s, e, *_r) in shots[1:]: add(noise_sweep(0.45), s - 0.2, 0.22, random.uniform(0.3, 0.7))
    out /= max(1e-6, np.abs(out).max()) / 0.8
    sf.write(os.path.join(BUILD, "score.wav"), out, SR)


# ═══════════════════════════ MAIN ═══════════════════════════
def main():
    times, dur, env = prepare_voice()
    CTX.lip = lambda t: float(env[min(len(env) - 1, int(t * FPS))]) * 0.95
    shots = build_shots(times, dur)
    surface = skia.Surface(W, H)
    if "--stills" in sys.argv:
        os.makedirs(os.path.join(BUILD, "stills"), exist_ok=True)
        ts = [float(v) for v in sys.argv[sys.argv.index("--stills") + 1].split(",")]
        for t in ts:
            Image.fromarray(render_frame(surface, shots, times, t, dur)).save(os.path.join(BUILD, "stills", f"{t:05.1f}.png"))
        print("dur", round(dur, 2), [(k, round(s, 2), round(e, 2)) for k, s, e, _ in times]); return
    make_score(times, dur, shots)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    silent = os.path.join(BUILD, "video_silent.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    n = int(dur * FPS)
    for i in range(n):
        p.stdin.write(np.ascontiguousarray(render_frame(surface, shots, times, i / FPS, dur)).tobytes())
        if i % 300 == 0: print(f"frame {i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    fc = ("[1:a]aformat=sample_rates=48000:channel_layouts=mono,highpass=f=65,equalizer=f=120:t=q:w=1:g=3,"
          "equalizer=f=3000:t=q:w=1.2:g=2.5,acompressor=threshold=-22dB:ratio=3.5:attack=6:release=120:makeup=4,"
          "aecho=0.85:0.6:55|105:0.16|0.09,pan=stereo|c0=c0|c1=c0,asplit=2[v][key];"
          "[2:a]volume=0.75[m];[m][key]sidechaincompress=threshold=0.035:ratio=7:attack=25:release=400[md];"
          "[v][md]amix=inputs=2:weights=1 1:normalize=0,loudnorm=I=-14:TP=-1.0:LRA=10[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", os.path.join(BUILD, "narration.wav"), "-i", os.path.join(BUILD, "score.wav"),
                    "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", OUT], check=True)
    print("done ->", OUT, "dur", round(dur, 2))


if __name__ == "__main__":
    main()
