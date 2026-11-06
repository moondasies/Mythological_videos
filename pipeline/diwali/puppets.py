"""
2D vector cut-out puppet kit (skia). Original character designs — flat colours, bold outlines,
one cel-shadow tone, glowing FX. Every figure is built from separately transformable parts
(arms with shoulder/elbow angles, head tilt, blink, mouth open, extra heads) so it can be animated.
"""
import math
import skia

OUT = skia.ColorSetARGB(255, 42, 24, 20)       # outline colour
OUTW = 7


def C(rgb, a=255):
    return skia.ColorSetARGB(int(a), int(rgb[0]), int(rgb[1]), int(rgb[2]))


def fill(rgb, a=255, blur=0):
    p = skia.Paint(AntiAlias=True, Color=C(rgb, a))
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def stroke(rgb, w, a=255, blur=0, dash=None):
    p = skia.Paint(AntiAlias=True, Color=C(rgb, a), Style=skia.Paint.kStroke_Style, StrokeWidth=w,
                   StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if dash: p.setPathEffect(skia.DashPathEffect.Make(dash, 0))
    return p


def shade(rgb, k=0.78):
    return tuple(max(0, int(c * k)) for c in rgb)


def shape(c, path, rgb, outline=True, cel=True, a=255, ow=OUTW):
    c.drawPath(path, fill(rgb, a))
    if cel:  # one cel-shadow tone on the right side (light from upper-left)
        b = path.getBounds()
        c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
        sp = skia.Path()
        sp.moveTo(b.centerX() + b.width() * 0.12, b.top() - 5); sp.lineTo(b.right() + 5, b.top() - 5)
        sp.lineTo(b.right() + 5, b.bottom() + 5); sp.lineTo(b.centerX() + b.width() * 0.02, b.bottom() + 5); sp.close()
        c.drawPath(sp, fill(shade(rgb), a * 0.55 if a < 255 else 140))
        c.restore()
    if outline: c.drawPath(path, stroke((42, 24, 20), ow, a))


def oval(cx, cy, rx, ry):
    p = skia.Path(); p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry)); return p


def glow(c, x, y, r, rgb, a=160):
    c.drawCircle(x, y, r, fill(rgb, a, blur=r * 0.45))


GOLD = (236, 184, 72)
GOLD_D = (190, 132, 40)
WHITE = (250, 246, 236)


# ───────────────────────── face / head ─────────────────────────
def head(c, x, y, s, spec, pose, small=False, extra_idx=0):
    sk = spec["skin"]
    c.save(); c.translate(x, y); c.scale(s, s); c.rotate(pose.get("tilt", 0))
    # back hair
    if spec.get("female"):
        hp = oval(0, -18, 78, 82); shape(c, hp, (24, 18, 22), cel=False)
        shape(c, oval(0, -95, 40, 30), (24, 18, 22), cel=False)                 # bun
        for i in range(5): c.drawCircle(-30 + i * 15, -118, 7, fill(WHITE)); c.drawCircle(-30 + i * 15, -118, 7, stroke((42, 24, 20), 2))
    else:
        shape(c, oval(0, -12, 74, 80), spec.get("hair", (24, 18, 22)), cel=False)
    # ears + earrings
    for sx in (-1, 1):
        shape(c, oval(sx * 66, 4, 13, 20), sk, cel=False, ow=5)
        c.drawCircle(sx * 68, 34, 11, fill(GOLD)); c.drawCircle(sx * 68, 34, 11, stroke((42, 24, 20), 3))
    # face
    face = skia.Path()
    face.moveTo(0, -78); face.cubicTo(52, -78, 68, -40, 66, 0); face.cubicTo(64, 50, 34, 84, 0, 86)
    face.cubicTo(-34, 84, -64, 50, -66, 0); face.cubicTo(-68, -40, -52, -78, 0, -78); face.close()
    shape(c, face, sk)
    # fringe hair
    fr = skia.Path(); fr.moveTo(-66, -10); fr.cubicTo(-66, -70, -20, -86, 0, -84); fr.cubicTo(30, -86, 66, -70, 66, -10)
    fr.cubicTo(50, -52, 18, -60, 0, -58); fr.cubicTo(-18, -60, -50, -52, -66, -10); fr.close()
    shape(c, fr, spec.get("hair", (24, 18, 22)), cel=False, ow=5)
    eyes = pose.get("eyes", "open"); blink = pose.get("blink", 0.0)
    # brows
    ang = pose.get("brow", 0)   # + angry
    for sx in (-1, 1):
        bp = skia.Path(); bp.moveTo(sx * 14, -30 + ang * 6); bp.quadTo(sx * 30, -42 - ang * 2, sx * 48, -34 - ang * 8)
        c.drawPath(bp, stroke((30, 18, 16), 7))
    # eyes
    for sx in (-1, 1):
        ex, ey = sx * 28, -10
        if eyes == "closed" or blink > 0.8:
            lp = skia.Path(); lp.moveTo(ex - 16, ey); lp.quadTo(ex, ey + 9, ex + 16, ey); c.drawPath(lp, stroke((30, 18, 16), 5))
            continue
        h = 13 * (1 - blink)
        e = skia.Path(); e.moveTo(ex - 19, ey); e.quadTo(ex, ey - h * 1.5, ex + 19, ey); e.quadTo(ex, ey + h * 1.1, ex - 19, ey); e.close()
        if eyes == "glow":
            c.drawPath(e, fill((255, 236, 140)))
            glow(c, ex, ey, 34, (255, 210, 90), 190)
            c.drawPath(e, fill((255, 250, 210)))
        else:
            c.drawPath(e, fill(WHITE))
            c.save(); c.clipPath(e, skia.ClipOp.kIntersect, True)
            gx = pose.get("look", 0) * 6
            c.drawCircle(ex + gx, ey + 1, 9, fill((40, 26, 20))); c.drawCircle(ex + gx + 3, ey - 3, 3, fill(WHITE))
            c.restore()
        c.drawPath(e, stroke((30, 18, 16), 4))
        ul = skia.Path(); ul.moveTo(ex - 20, ey + 1); ul.quadTo(ex, ey - h * 1.55, ex + 21, ey - 1); c.drawPath(ul, stroke((30, 18, 16), 6))
    # nose
    n = skia.Path(); n.moveTo(-4, 4); n.quadTo(-10, 26, 0, 30); n.quadTo(6, 31, 9, 27); c.drawPath(n, stroke(shade(sk, 0.55), 4))
    # mouth
    mo = pose.get("mouth", 0.0)
    if mo > 0.08:
        m = oval(0, 50, 15 + mo * 6, 4 + mo * 15); c.drawPath(m, fill((110, 30, 36))); c.drawPath(m, stroke((42, 24, 20), 4))
        c.drawPath(oval(0, 50 + mo * 8, 9, 3 + mo * 4), fill((200, 90, 90)))
    else:
        m = skia.Path(); sm = pose.get("smile", 0.4)
        m.moveTo(-17, 48); m.quadTo(0, 48 + 10 * sm, 17, 48); c.drawPath(m, stroke((120, 40, 40), 5))
    # facial hair / marks
    if spec.get("mustache"):
        for sx in (-1, 1):
            mp = skia.Path(); mp.moveTo(0, 38); mp.cubicTo(sx * 16, 30, sx * 34, 34, sx * 44, 22); mp.cubicTo(sx * 40, 42, sx * 18, 46, 0, 42); mp.close()
            c.drawPath(mp, fill((24, 16, 14))); c.drawPath(mp, stroke((24, 16, 14), 2))
    if spec.get("beard"):
        bd = skia.Path(); bd.moveTo(-58, 20); bd.cubicTo(-60, 120, -20, 170, 0, 176); bd.cubicTo(20, 170, 60, 120, 58, 20)
        bd.cubicTo(40, 70, 20, 64, 0, 64); bd.cubicTo(-20, 64, -40, 70, -58, 20); bd.close()
        shape(c, bd, spec["beard"], cel=True, ow=5)
        mp = skia.Path(); mp.moveTo(-34, 40); mp.quadTo(0, 26, 34, 40); mp.quadTo(0, 48, -34, 40); mp.close(); c.drawPath(mp, fill(spec["beard"]))
    mark = spec.get("mark")
    if mark == "tilak":
        t = skia.Path(); t.moveTo(-8, -40); t.lineTo(-8, -64); t.moveTo(8, -40); t.lineTo(8, -64); c.drawPath(t, stroke((250, 240, 225), 5))
        c.drawLine(0, -38, 0, -62, stroke((210, 40, 40), 5))
    elif mark == "tripundra":
        for k in range(3): c.drawLine(-26, -44 - k * 8, 26, -44 - k * 8, stroke((246, 240, 230), 4))
        c.drawCircle(0, -52, 6, fill((210, 40, 40)))
    elif mark == "bindi":
        c.drawCircle(0, -44, 7, fill((210, 30, 40)))
    # crown
    crown = spec.get("crown")
    if crown:
        tall = 1.35 if crown == "tall" else 1.0
        if small: tall *= 0.9
        cp = skia.Path(); cp.moveTo(-60, -62); cp.lineTo(-52, -120 * tall); cp.lineTo(-26, -100 * tall); cp.lineTo(0, -170 * tall)
        cp.lineTo(26, -100 * tall); cp.lineTo(52, -120 * tall); cp.lineTo(60, -62); cp.quadTo(0, -74, -60, -62); cp.close()
        shape(c, cp, GOLD, ow=5)
        c.drawLine(-58, -70, 58, -70, stroke(GOLD_D, 8))
        jew = (200, 30, 50) if crown == "tall" else (40, 120, 200)
        c.drawCircle(0, -98 * tall, 12, fill(jew)); c.drawCircle(0, -98 * tall, 12, stroke((42, 24, 20), 3))
        c.drawCircle(-3, -101 * tall, 3, fill(WHITE))
    c.restore()


# ───────────────────────── body ─────────────────────────
def arm(c, sx, sy, side, a_sh, a_el, w, rgb, hold=None, bangle=True):
    """side: -1 left / +1 right. Angles in degrees: 0 = hanging down, + = raised outward."""
    L1, L2 = 165, 150
    a1 = math.radians(a_sh); a2 = math.radians(a_sh + a_el)
    ex, ey = sx + side * math.sin(a1) * L1, sy + math.cos(a1) * L1
    hx, hy = ex + side * math.sin(a2) * L2, ey + math.cos(a2) * L2
    for (x0, y0, x1, y1, ww) in ((sx, sy, ex, ey, w), (ex, ey, hx, hy, w * 0.85)):
        c.drawLine(x0, y0, x1, y1, stroke((42, 24, 20), ww + 12))
        c.drawLine(x0, y0, x1, y1, stroke(rgb, ww))
    if bangle:
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        c.drawCircle(mx, my, w * 0.5, fill(GOLD)); c.drawCircle(mx, my, w * 0.5, stroke((42, 24, 20), 3))
        bx, by = ex + (hx - ex) * 0.82, ey + (hy - ey) * 0.82
        c.drawCircle(bx, by, w * 0.46, fill(GOLD)); c.drawCircle(bx, by, w * 0.46, stroke((42, 24, 20), 3))
    if hold == "sword":
        c.save(); c.translate(hx, hy); c.rotate(math.degrees(-side * a2) + 180)
        bl = skia.Path(); bl.moveTo(-9, 20); bl.lineTo(9, 20); bl.lineTo(5, 250); bl.lineTo(0, 280); bl.lineTo(-5, 250); bl.close()
        shape(c, bl, (214, 222, 232), ow=4)
        c.drawLine(-34, 18, 34, 18, stroke(GOLD_D, 14)); c.drawLine(0, -26, 0, 18, stroke((90, 40, 30), 12))
        c.restore()
    if hold == "bow":
        c.save(); c.translate(hx, hy)
        bp = skia.Path(); bp.moveTo(0, -260); bp.cubicTo(side * 80, -150, side * 80, 150, 0, 260)
        c.drawPath(bp, stroke((42, 24, 20), 18)); c.drawPath(bp, stroke((150, 90, 40), 10))
        c.drawLine(0, -258, 0, 258, stroke((240, 230, 210), 2.5))
        c.restore()
    if hold == "lotus":
        lotus(c, hx, hy - 30, 0.45)
    if hold == "book":
        bk = skia.Path(); bk.addRect(skia.Rect.MakeXYWH(hx - 40, hy - 30, 80, 56)); shape(c, bk, (180, 50, 40), ow=4)
        c.drawLine(hx, hy - 30, hx, hy + 26, stroke(GOLD, 4))
    if hold == "pot":
        shape(c, oval(hx, hy - 10, 34, 30), (200, 140, 60), ow=4); c.drawLine(hx - 14, hy - 40, hx + 14, hy - 40, stroke((42, 24, 20), 8))
    c.drawCircle(hx, hy, w * 0.62, fill(rgb)); c.drawCircle(hx, hy, w * 0.62, stroke((42, 24, 20), 5))
    return hx, hy


def lotus(c, x, y, s):
    c.save(); c.translate(x, y); c.scale(s, s)
    for k, (ang, r) in enumerate([(-60, 1.0), (60, 1.0), (-30, 1.1), (30, 1.1), (0, 1.25)]):
        c.save(); c.rotate(ang)
        p = skia.Path(); p.moveTo(0, 0); p.cubicTo(-38 * r, -50 * r, -20 * r, -110 * r, 0, -130 * r); p.cubicTo(20 * r, -110 * r, 38 * r, -50 * r, 0, 0); p.close()
        shape(c, p, (242, 150, 180) if k % 2 else (250, 180, 200), ow=4)
        c.restore()
    c.restore()


def figure(c, x, y, s, spec, pose, t=0.0):
    """Draw a whole puppet. (x,y) = feet centre on screen, s = scale (1 => ~1000px tall)."""
    c.save(); c.translate(x, y); c.scale(s, s)
    seated = pose.get("seated", False)
    W0 = -300 if seated else -470
    br = math.sin(t * 2 * math.pi / 3.6) * 4 * pose.get("breathe", 1)
    sk = spec["skin"]
    # extra arms (Brahma) behind
    if spec.get("four_arms"):
        arm(c, -100, W0 - 262, -1, 145, -40, 40, sk, hold="pot")
        arm(c, 100, W0 - 262, 1, 145, -40, 40, sk, hold="book")
    # lower garment
    if seated:
        d = skia.Path(); d.moveTo(-85, W0); d.lineTo(85, W0); d.cubicTo(150, W0 + 120, 230, W0 + 210, 225, W0 + 260)
        d.quadTo(0, W0 + 300, -225, W0 + 260); d.cubicTo(-230, W0 + 210, -150, W0 + 120, -85, W0); d.close()
        shape(c, d, spec["dhoti"])
        c.drawPath(_band(-220, W0 + 255, 220, W0 + 255, 0, W0 + 292), stroke(GOLD, 12))
    else:
        d = skia.Path(); d.moveTo(-82, W0); d.lineTo(82, W0); d.lineTo(120, -36); d.quadTo(0, -18, -120, -36); d.close()
        shape(c, d, spec["dhoti"])
        c.drawLine(0, W0 + 30, 6, -40, stroke(shade(spec["dhoti"], 0.6), 4))
        c.drawLine(-30, W0 + 40, -44, -40, stroke(shade(spec["dhoti"], 0.6), 3))
        bb = skia.Path(); bb.moveTo(-118, -42); bb.quadTo(0, -24, 118, -42); c.drawPath(bb, stroke(GOLD, 12))
        for sx in (-1, 1):
            shape(c, oval(sx * 48, -14, 42, 18), sk, ow=5)
            c.drawCircle(sx * 48, -30, 10, fill(GOLD))
    # back arm
    la, le = pose.get("la", 12), pose.get("le", 10)
    ra, re = pose.get("ra", 12), pose.get("re", 10)
    if pose.get("fold"):
        la, le, ra, re = 18, -128, 18, -128
    shy = W0 - 262 + br * 0.3
    # torso
    c.save(); c.translate(0, W0); c.scale(1, 1 + br / 600); c.translate(0, -W0)
    tor = skia.Path(); tor.moveTo(-74, W0); tor.lineTo(74, W0)
    tor.cubicTo(92, W0 - 120, 126, W0 - 210, 122, W0 - 268); tor.quadTo(0, W0 - 306, -122, W0 - 268)
    tor.cubicTo(-126, W0 - 210, -92, W0 - 120, -74, W0); tor.close()
    shape(c, tor, spec.get("blouse", sk))
    if spec.get("female"):
        pal = skia.Path(); pal.moveTo(-122, W0 - 262); pal.lineTo(-60, W0 - 285); pal.lineTo(80, W0 + 10); pal.lineTo(10, W0 + 10); pal.close()
        shape(c, pal, spec["dhoti"]); c.drawLine(-60, W0 - 285, 80, W0 + 10, stroke(GOLD, 10))
    elif spec.get("sash"):
        sa = skia.Path(); sa.moveTo(-122, W0 - 262); sa.lineTo(-80, W0 - 282); sa.lineTo(84, W0 - 10); sa.lineTo(40, W0); sa.close()
        shape(c, sa, spec["sash"])
    # necklace
    nk = skia.Path(); nk.moveTo(-58, W0 - 282); nk.quadTo(0, W0 - 200, 58, W0 - 282); c.drawPath(nk, stroke(GOLD, 10)); c.drawPath(nk, stroke(GOLD_D, 3))
    c.drawCircle(0, W0 - 238, 13, fill((200, 30, 50))); c.drawCircle(0, W0 - 238, 13, stroke(GOLD, 5))
    if spec.get("sacred_thread"):
        th = skia.Path(); th.moveTo(-100, W0 - 262); th.quadTo(10, W0 - 140, 74, W0 - 6); c.drawPath(th, stroke((246, 240, 228), 4))
    # belt
    c.drawRoundRect(skia.Rect.MakeLTRB(-90, W0 - 14, 90, W0 + 14), 8, 8, fill(GOLD))
    c.drawRoundRect(skia.Rect.MakeLTRB(-90, W0 - 14, 90, W0 + 14), 8, 8, stroke((42, 24, 20), 5))
    c.drawCircle(0, W0, 11, fill((40, 120, 200)))
    c.restore()
    # neck
    c.drawRect(skia.Rect.MakeLTRB(-24, W0 - 330, 24, W0 - 284), fill(sk))
    c.drawLine(-24, W0 - 330, -24, W0 - 290, stroke((42, 24, 20), 5)); c.drawLine(24, W0 - 330, 24, W0 - 290, stroke((42, 24, 20), 5))
    # heads (drawn before arms so raised arms / weapons sit in front)
    hy = W0 - 395 + br * 0.5
    n = spec.get("heads", 1)
    if n == "brahma":
        for sx in (-1, 1):
            head(c, sx * 104, hy + 14, 0.82, spec, dict(pose, tilt=sx * 8), small=True)
    elif isinstance(n, int) and n > 1:
        shown = pose.get("heads_shown", n)
        order = [-1, 1, -2, 2, -3, 3, -4, 4, 5]     # removal order from outside: reversed below
        slots = [-4, 4, -3, 3, -2, 2, -1, 1, 5][: max(0, shown - 1)]
        for k in sorted(slots, key=lambda v: -abs(v)):
            xx = k * 104 if abs(k) < 5 else 4.3 * 104
            yy = hy + abs(k) * 10 - (30 if abs(k) == 5 else 0)
            head(c, xx, yy - 10, 0.8, spec, dict(pose, tilt=(k / 5) * 6), small=True)
    head(c, 0, hy, 1.0, spec, pose)
    hl = arm(c, -112, shy, -1, la, le, 46, sk, hold=pose.get("hold_l"))
    hr = arm(c, 112, shy, 1, ra, re, 46, sk, hold=pose.get("hold_r"))
    c.restore()
    return hl, hr


def _band(x0, y0, x1, y1, cx, cy):
    p = skia.Path(); p.moveTo(x0, y0); p.quadTo(cx, cy, x1, y1); return p


# ───────────────────────── character specs ─────────────────────────
RAVANA = dict(skin=(150, 98, 70), hair=(22, 16, 16), dhoti=(168, 30, 42), sash=(92, 40, 110), crown="tall",
              mustache=True, mark="tripundra", heads=10)
BRAHMA = dict(skin=(232, 168, 96), hair=(240, 238, 230), dhoti=(232, 118, 40), sash=(190, 40, 50), crown="mukut",
              beard=(244, 242, 236), heads="brahma", four_arms=True, sacred_thread=True)
RAMA = dict(skin=(82, 128, 196), hair=(22, 16, 16), dhoti=(244, 196, 48), sash=(226, 110, 40), crown="mukut", mark="tilak")
LAKSHMANA = dict(skin=(228, 178, 132), hair=(22, 16, 16), dhoti=(232, 118, 40), sash=(60, 140, 90), crown="mukut", mark="tilak")
SITA = dict(skin=(222, 166, 126), hair=(22, 16, 16), dhoti=(192, 34, 52), blouse=(232, 150, 40), female=True, crown="mukut", mark="bindi")
