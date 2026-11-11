"""
QBlog kapak GIF üreticisi / cover GIF generator.

Gereksinimler / Requires: pycairo, pillow, numpy, scikit-image, ffmpeg (+ #09/#10 için pennylane, scikit-learn)
Kullanım / Usage:
    python make_covers.py            # hepsi / all
    python make_covers.py 3 6        # sadece #03 ve #06 / only #03 and #06
Çıktı / Output: assets/covers/<slug>-<tr|en>.gif  +  .png (statik paylaşım görseli / static og:image)
"""
from __future__ import annotations

import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from covers_meta import LEVEL, POSTS, SERIES

HERE = Path(__file__).parent
ROOT = HERE.parent
OUTDIR = HERE / "covers"
W, H = 1200, 630
CX, CY = 900, 315                      # animasyon merkezi / animation centre
BG = (7, 11, 22)
FPS = 20
TAU = 2 * math.pi

FONT_DIR = Path("/usr/share/fonts/opentype/inter")
F_TITLE = FONT_DIR / "InterDisplay-Bold.otf"
F_SEMI = FONT_DIR / "Inter-SemiBold.otf"
F_REG = FONT_DIR / "Inter-Regular.otf"
F_MED = FONT_DIR / "Inter-Medium.otf"
KET_FONT = "DejaVu Sans"


# ------------------------------------------------------------------ helpers
def hex2rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def mix(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def ease(t):  # smoothstep
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def glow(ctx, draw_path, rgb, width, alpha=1.0, layers=((5.0, 0.05), (2.8, 0.10), (1.7, 0.22))):
    for mult, a in layers:
        draw_path()
        ctx.set_source_rgba(*rgb, a * alpha)
        ctx.set_line_width(width * mult)
        ctx.stroke()
    draw_path()
    ctx.set_source_rgba(*rgb, alpha)
    ctx.set_line_width(width)
    ctx.stroke()


def glow_dot(ctx, x, y, r, rgb, alpha=1.0):
    for mult, a in ((4.5, 0.06), (2.8, 0.12), (1.7, 0.28)):
        ctx.arc(x, y, r * mult, 0, TAU)
        ctx.set_source_rgba(*rgb, a * alpha)
        ctx.fill()
    ctx.arc(x, y, r, 0, TAU)
    ctx.set_source_rgba(*mix(rgb, (1, 1, 1), 0.55), alpha)
    ctx.fill()


def text_c(ctx, s, x, y, size, rgb, alpha=1.0, font=KET_FONT, bold=False):
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    ctx.move_to(x - e.width / 2 - e.x_bearing, y - e.height / 2 - e.y_bearing)
    ctx.set_source_rgba(*rgb, alpha)
    ctx.show_text(s)


def rounded_rect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


class Sphere:
    """Basit 3B izdüşüm / simple 3-D projection for Bloch spheres."""

    def __init__(self, cx, cy, R, az=-0.5, el=0.32):
        self.cx, self.cy, self.R, self.az, self.el = cx, cy, R, az, el

    def p(self, v):
        x, y, z = v
        ca, sa = math.cos(self.az), math.sin(self.az)
        x1, y1 = x * ca - y * sa, x * sa + y * ca
        ce, se = math.cos(self.el), math.sin(self.el)
        up = y1 * se + z * ce
        depth = -y1 * ce + z * se
        return self.cx + self.R * x1, self.cy - self.R * up, depth

    def curve(self, ctx, pts, rgb, w=1.4, a_front=0.55, a_back=0.13):
        proj = [self.p(v) for v in pts]
        for (x0, y0, d0), (x1, y1, d1) in zip(proj, proj[1:]):
            a = a_front if (d0 + d1) / 2 >= 0 else a_back
            ctx.move_to(x0, y0)
            ctx.line_to(x1, y1)
            ctx.set_source_rgba(*rgb, a)
            ctx.set_line_width(w)
            ctx.stroke()

    def frame(self, ctx, rgb, labels=True, ket_rgb=(0.85, 0.9, 1)):
        # gövde / body
        g = cairo.RadialGradient(self.cx - self.R * 0.35, self.cy - self.R * 0.4, self.R * 0.1,
                                 self.cx, self.cy, self.R * 1.05)
        g.add_color_stop_rgba(0, *rgb, 0.16)
        g.add_color_stop_rgba(1, *rgb, 0.02)
        ctx.arc(self.cx, self.cy, self.R, 0, TAU)
        ctx.set_source(g)
        ctx.fill()
        glow(ctx, lambda: ctx.arc(self.cx, self.cy, self.R, 0, TAU), rgb, 1.6, 0.55,
             layers=((3.0, 0.06), (1.8, 0.12)))
        n = 90
        circ = lambda f: [f(TAU * i / n) for i in range(n + 1)]
        self.curve(ctx, circ(lambda t: (math.cos(t), math.sin(t), 0)), rgb)          # ekvator
        self.curve(ctx, circ(lambda t: (math.cos(t), 0, math.sin(t))), rgb, 1.0, 0.3, 0.08)
        self.curve(ctx, circ(lambda t: (0, math.cos(t), math.sin(t))), rgb, 1.0, 0.3, 0.08)
        for ax in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            a, b = self.p([-c for c in ax]), self.p(ax)
            ctx.set_dash([4, 5])
            ctx.move_to(a[0], a[1])
            ctx.line_to(b[0], b[1])
            ctx.set_source_rgba(*rgb, 0.28)
            ctx.set_line_width(1)
            ctx.stroke()
            ctx.set_dash([])
        if labels:
            x, y, _ = self.p((0, 0, 1.18))
            text_c(ctx, "|0⟩", x, y, self.R * 0.16, ket_rgb, 0.9)
            x, y, _ = self.p((0, 0, -1.2))
            text_c(ctx, "|1⟩", x, y, self.R * 0.16, ket_rgb, 0.9)

    def arrow(self, ctx, v, rgb, w=3.2, alpha=1.0):
        x0, y0, _ = self.p((0, 0, 0))
        x1, y1, _ = self.p(v)
        glow(ctx, lambda: (ctx.move_to(x0, y0), ctx.line_to(x1, y1)), rgb, w, alpha)
        glow_dot(ctx, x1, y1, w * 1.9, rgb, alpha)


# ------------------------------------------------------------------ static layer
def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        test = (cur + " " + wd).strip()
        if draw.textlength(test, font=font) <= maxw:
            cur = test
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines


def static_layer(post, lang) -> np.ndarray:
    acc = hex2rgb(post["accent"])
    acc2 = hex2rgb(post["accent2"])
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*[c / 255 for c in BG])
    ctx.paint()
    for (gx, gy, r, c, a) in ((CX, CY, 420, acc, 0.20), (CX + 160, CY + 220, 300, acc2, 0.10),
                             (90, 40, 380, acc2, 0.07)):
        g = cairo.RadialGradient(gx, gy, 0, gx, gy, r)
        g.add_color_stop_rgba(0, *c, a)
        g.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(g)
        ctx.paint()
    # nokta ızgarası / dot grid
    for x in range(30, 620, 28):
        for y in range(30, H, 28):
            ctx.arc(x, y, 0.9, 0, TAU)
            ctx.set_source_rgba(0.6, 0.7, 0.9, 0.07)
            ctx.fill()
    # ince çerçeve / hairline frame
    rounded_rect(ctx, 14, 14, W - 28, H - 28, 22)
    ctx.set_source_rgba(*acc, 0.18)
    ctx.set_line_width(1)
    ctx.stroke()

    buf = np.ndarray((H, W, 4), np.uint8, surf.get_data()).copy()
    img = Image.fromarray(buf[..., [2, 1, 0]], "RGB")
    d = ImageDraw.Draw(img)
    A = tuple(int(c * 255) for c in acc)
    WHITE, MUTED, DIM = (240, 244, 252), (170, 179, 197), (110, 120, 145)
    X0, MAXW = 64, 560

    # rozet / badge
    fb = ImageFont.truetype(str(F_SEMI), 17)
    badge = f"QBLOG  ·  #{post['n']:02d}"
    bw = d.textlength(badge, font=fb) + 34
    d.rounded_rectangle((X0, 58, X0 + bw, 92), radius=17, outline=A, width=2)
    d.text((X0 + 17, 75), badge, font=fb, fill=A, anchor="lm")
    lvl = LEVEL[post["level"]][lang]
    lw = d.textlength(lvl, font=fb) + 30
    d.rounded_rectangle((X0 + bw + 10, 58, X0 + bw + 10 + lw, 92), radius=17, fill=(18, 23, 38),
                        outline=(60, 70, 95), width=2)
    d.text((X0 + bw + 25, 75), lvl, font=fb, fill=MUTED, anchor="lm")

    # başlık / title (otomatik boyut / auto-size)
    title, sub = post[lang]
    lines = title.split("\n")
    size = 66
    while size > 34:
        ft = ImageFont.truetype(str(F_TITLE), size)
        widest = max(d.textlength(l.replace("*", ""), font=ft) for l in lines)
        if widest <= MAXW and len(lines) * size * 1.08 <= 250:
            break
        size -= 2
    y = 130
    for line in lines:
        x = X0
        for i, part in enumerate(line.split("*")):
            if not part:
                continue
            d.text((x, y), part, font=ft, fill=A if i % 2 else WHITE)
            x += d.textlength(part, font=ft)
        y += int(size * 1.1)

    # alt başlık / subtitle
    fs = ImageFont.truetype(str(F_REG), 23)
    y += 14
    for l in wrap(d, sub, fs, MAXW - 20):
        d.text((X0, y), l, font=fs, fill=MUTED)
        y += 33

    # etiketler / tags
    ftag = ImageFont.truetype(str(F_MED), 16)
    x, ty = X0, H - 104
    for tag in ["Python"] + post["tags"]:
        tw = d.textlength(tag, font=ftag) + 26
        d.rounded_rectangle((x, ty, x + tw, ty + 30), radius=8, fill=(22, 28, 46), outline=(44, 54, 80))
        d.text((x + 13, ty + 15), tag, font=ftag, fill=(200, 208, 225), anchor="lm")
        x += tw + 8
    d.line((X0, H - 58, X0 + 36, H - 58), fill=A, width=3)
    d.text((X0 + 48, H - 58), SERIES[lang], font=ImageFont.truetype(str(F_MED), 17), fill=DIM, anchor="lm")

    rgb = np.asarray(img)
    out = np.empty((H, W, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2], out[..., 3] = rgb[..., 2], rgb[..., 1], rgb[..., 0], 255
    return out


# ------------------------------------------------------------------ scenes
# Her sahne: (kare sayısı, setup(post, lang) -> state, draw(ctx, arr, i, n, state))
def scene_qubit(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    S = Sphere(850, 318, 190)
    n = 72

    def state(t):
        th = math.pi / 2 + 1.15 * math.sin(TAU * t)
        ph = TAU * 2 * t
        return th, ph

    def draw(ctx, arr, i):
        t = i / n
        S.az = -0.5 + 0.25 * math.sin(TAU * t)
        S.frame(ctx, acc)
        trail = []
        for k in range(28):
            th, ph = state(t - k * 0.006)
            trail.append((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
        for k, (a, b) in enumerate(zip(trail, trail[1:])):
            pa, pb = S.p(a), S.p(b)
            ctx.move_to(pa[0], pa[1])
            ctx.line_to(pb[0], pb[1])
            ctx.set_source_rgba(*acc2, 0.75 * (1 - k / 28))
            ctx.set_line_width(3.2 * (1 - k / 28) + 0.6)
            ctx.stroke()
        th, _ = state(t)
        S.arrow(ctx, trail[0], acc)
        # olasılık çubukları / probability bars
        p0 = math.cos(th / 2) ** 2
        for j, (p, lab) in enumerate(((p0, "0"), (1 - p0, "1"))):
            x = 1100 + j * 46
            ctx.rectangle(x, 190, 26, 250)
            ctx.set_source_rgba(1, 1, 1, 0.05)
            ctx.fill()
            h = 250 * p
            ctx.rectangle(x, 440 - h, 26, h)
            ctx.set_source_rgba(*(acc if j == 0 else acc2), 0.9)
            ctx.fill()
            text_c(ctx, lab, x + 13, 462, 18, (0.8, 0.85, 0.95), 0.9)
            text_c(ctx, f"%{p * 100:.0f}" if lang == "tr" else f"{p:.0%}", x + 13, 172, 13,
                   (0.7, 0.75, 0.88), 0.9)
    return n, draw


def scene_entangle(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    A, B = Sphere(760, 245, 105, el=0.3), Sphere(1040, 395, 105, el=0.3)
    n = 72

    def draw(ctx, arr, i):
        t = i / n
        # dolanık "ip" — iki iç içe dalga / entangled string — two braided waves
        (ax, ay, _), (bx, by, _) = A.p((0, 0, 0)), B.p((0, 0, 0))
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = -uy, ux
        for s, col in ((0, acc), (math.pi, acc2)):
            def path(s=s):
                for k in range(121):
                    u = k / 120
                    env = math.sin(math.pi * u) ** 0.8
                    off = 26 * env * math.sin(TAU * (3 * u - 2 * t) + s)
                    x, y = ax + ux * L * u + nx * off, ay + uy * L * u + ny * off
                    (ctx.move_to if k == 0 else ctx.line_to)(x, y)
            glow(ctx, path, col, 2.0, 0.85)
        # ölçüm anı / measurement flash (twice per loop, simultaneous)
        flash = max(0.0, 1 - abs(((t * 2) % 1) - 0.5) / 0.12)
        ang = TAU * t * 2
        for S, col, sgn in ((A, acc, 1), (B, acc2, -1)):
            S.frame(ctx, col, labels=False)
            if flash > 0:
                (sx, sy, _) = S.p((0, 0, 0))
                r = S.R * (1.0 + 0.5 * (1 - flash))
                ctx.arc(sx, sy, r, 0, TAU)
                ctx.set_source_rgba(*col, 0.5 * flash)
                ctx.set_line_width(3)
                ctx.stroke()
            th = math.pi / 2 + 1.2 * math.sin(ang)
            snap = ease(flash * 1.5)
            th = th * (1 - snap) + (0.0 if math.cos(ang / 2) > 0 else math.pi) * snap
            v = (math.sin(th) * math.cos(ang), math.sin(th) * math.sin(ang), math.cos(th))
            S.arrow(ctx, v if sgn > 0 else v, col, 3.0)
        (ax2, ay2, _) = A.p((0, 0, -1.35))
        text_c(ctx, "A", A.cx - A.R - 26, A.cy, 22, acc, 0.9, bold=True)
        text_c(ctx, "B", B.cx + B.R + 26, B.cy, 22, acc2, 0.9, bold=True)
        text_c(ctx, "(|00⟩ + |11⟩) / √2", 1040, 205, 22, (0.88, 0.92, 1), 0.9)
    return n, draw


def scene_teleport(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    n = 80
    ys = [205, 315, 425]
    X0, X1 = 712, 1112
    gates = [  # (x, wires, label)
        (745, [1], "H"), (805, [1, 2], "cx"), (868, [0, 1], "cx"), (925, [0], "H"),
        (980, [0], "M"), (1015, [1], "M"), (1052, [2], "X"), (1094, [2], "Z"),
    ]
    muted = (0.55, 0.62, 0.8)

    def psi_icon(ctx, x, y, alpha, col):
        ctx.arc(x, y, 26, 0, TAU)
        ctx.set_source_rgba(*col, 0.12 * alpha)
        ctx.fill()
        glow(ctx, lambda: ctx.arc(x, y, 26, 0, TAU), col, 1.6, alpha, layers=((2.5, 0.1),))
        a = -0.9
        glow(ctx, lambda: (ctx.move_to(x, y), ctx.line_to(x + 22 * math.cos(a), y + 22 * math.sin(a))),
             col, 2.4, alpha)
        text_c(ctx, "ψ", x, y + 46, 20, col, alpha, bold=True)

    def draw(ctx, arr, i):
        t = i / n
        pos = X0 - 40 + (X1 - X0 + 80) * ease(min(t / 0.75, 1))   # darbe konumu / pulse position
        fade = 1 - ease((t - 0.85) / 0.15)
        # teller / wires
        for k, y in enumerate(ys):
            ctx.move_to(X0 - 20, y)
            ctx.line_to(X1 + 10, y)
            ctx.set_source_rgba(*muted, 0.45)
            ctx.set_line_width(1.6)
            ctx.stroke()
            lab = ["q₀", "q₁", "q₂"][k]
            text_c(ctx, lab, X0 - 36, y, 17, muted, 0.9)
            if pos > X0 - 20:
                xe = min(pos, X1 + 10)
                glow(ctx, lambda y=y, xe=xe: (ctx.move_to(X0 - 20, y), ctx.line_to(xe, y)),
                     acc if k < 2 else acc2, 1.6, 0.55 * fade, layers=((2.5, 0.08),))
        # klasik bitler / classical wires (double lines from M to X)
        for off in (-2, 2):
            ctx.move_to(1015 + off, ys[1] + 20)                     # q1 → X
            ctx.line_to(1015 + off, ys[2] - 34 + off)
            ctx.line_to(1052 + off, ys[2] - 34 + off)
            ctx.line_to(1052 + off, ys[2] - 20)
            ctx.move_to(980 + off, ys[0] + 20)                      # q0 → Z
            ctx.line_to(980 + off, ys[2] + 40 + off)
            ctx.line_to(1094 + off, ys[2] + 40 + off)
            ctx.line_to(1094 + off, ys[2] + 20)
        ctx.set_source_rgba(*muted, 0.4)
        ctx.set_line_width(1.2)
        ctx.stroke()
        # kapılar / gates
        for gx, ws, lab in gates:
            lit = max(0.0, 1 - abs(pos - gx) / 45) * fade
            col = mix(muted, acc if 2 not in ws or lab == "cx" else acc2, 0.35 + 0.65 * lit)
            if lab == "cx":
                c, tg = ys[ws[0]], ys[ws[1]]
                ctx.move_to(gx, c)
                ctx.line_to(gx, tg + 15)
                ctx.set_source_rgba(*col, 0.95)
                ctx.set_line_width(2)
                ctx.stroke()
                ctx.arc(gx, c, 6, 0, TAU)
                ctx.fill()
                ctx.arc(gx, tg, 15, 0, TAU)
                ctx.stroke()
                ctx.move_to(gx - 15, tg)
                ctx.line_to(gx + 15, tg)
                ctx.stroke()
                if lit > 0:
                    glow_dot(ctx, gx, c, 5, col, lit)
            else:
                y = ys[ws[0]]
                rounded_rect(ctx, gx - 20, y - 20, 40, 40, 7)
                ctx.set_source_rgba(*[c / 255 for c in BG], 1)
                ctx.fill_preserve()
                ctx.set_source_rgba(*col, 0.25 + 0.3 * lit)
                ctx.fill_preserve()
                ctx.set_source_rgba(*col, 1)
                ctx.set_line_width(1.8)
                ctx.stroke()
                if lab == "M":
                    ctx.arc(gx, y + 8, 11, math.pi, TAU)
                    ctx.stroke()
                    ctx.move_to(gx, y + 8)
                    ctx.line_to(gx + 9, y - 9)
                    ctx.stroke()
                else:
                    text_c(ctx, lab, gx, y, 19, (1, 1, 1), 0.95, font="Inter", bold=True)
        # darbeler / pulses
        if fade > 0.01:
            for k, y in enumerate(ys):
                if X0 - 20 < pos < X1 + 10:
                    glow_dot(ctx, pos, y, 5, acc if k < 2 else acc2, fade)
        # ψ: Alice'ten kaybolur, Bob'da belirir / leaves Alice, appears at Bob
        arrive = ease((t - 0.62) / 0.15) * fade
        leave = 1 - ease((t - 0.35) / 0.2)
        psi_icon(ctx, 636, ys[0], max(leave, 0.15) if t < 0.95 else 1, acc)
        psi_icon(ctx, 1150, ys[2], max(arrive, 0.12), acc2)
    return n, draw


def scene_dice(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    n = 78
    rng = np.random.default_rng(4)
    landed = [5, 2, 6]          # 3 atış / 3 rolls per loop
    flicker = rng.integers(1, 7, n)
    bits_fl = rng.integers(0, 2, (n, 3))
    PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)],
            4: [(-1, -1), (1, -1), (-1, 1), (1, 1)], 5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
            6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}
    base = np.array([31, 29, 33, 30, 32, 30], float)

    def draw(ctx, arr, i):
        seg = n // 3
        r, j = divmod(i, seg)
        rolling = j < seg * 0.55
        face = int(flicker[i]) if rolling else landed[r]
        wob = (1 - j / (seg * 0.55)) if rolling else 0
        settle = 0 if rolling else ease((j - seg * 0.55) / 6)
        # zar / die
        ctx.save()
        ctx.translate(900, 265)
        ctx.rotate(0.35 * wob * math.sin(j * 1.9))
        s = 170
        rounded_rect(ctx, -s / 2, -s / 2, s, s, 30)
        ctx.set_source_rgba(*acc, 0.10 + 0.08 * settle)
        ctx.fill_preserve()
        glow(ctx, lambda: rounded_rect(ctx, -s / 2, -s / 2, s, s, 30), acc, 2.2, 0.6 + 0.4 * settle)
        for (px, py) in PIPS[face]:
            glow_dot(ctx, px * 44, py * 44, 12, acc if not rolling else mix(acc, acc2, 0.5), 0.95)
        ctx.restore()
        # kübit bitleri / qubit bits
        val = face - 1
        bits = bits_fl[i] if rolling else [(val >> 2) & 1, (val >> 1) & 1, val & 1]
        for k, b in enumerate(bits):
            x = 830 + k * 70
            rounded_rect(ctx, x - 24, 88, 48, 48, 10)
            ctx.set_source_rgba(*(acc2 if b else (0.4, 0.45, 0.6)), 0.18 if rolling else 0.3)
            ctx.fill()
            text_c(ctx, str(int(b)), x, 112, 26, acc2 if b else (0.75, 0.8, 0.92), 1, font="DejaVu Sans Mono", bold=True)
            text_c(ctx, f"q{2 - k}", x, 150, 12, (0.55, 0.6, 0.75), 0.9)
        # histogram
        h = base.copy()
        for rr in range(r + (0 if rolling else 1)):
            h[landed[rr] - 1] += 2.2
        for f in range(6):
            x = 742 + f * 56
            hh = h[f] * 3.2
            hl = (not rolling) and f == face - 1
            rounded_rect(ctx, x, 560 - hh, 36, hh, 5)
            ctx.set_source_rgba(*(acc if hl else (0.45, 0.5, 0.68)), 0.95 if hl else 0.45)
            ctx.fill()
            if hl:
                glow_dot(ctx, x + 18, 560 - hh - 10, 3, acc, settle)
            text_c(ctx, str(f + 1), x + 18, 580, 14, (0.7, 0.75, 0.88), 0.9)
    return n, draw


def scene_interference(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    n = 30
    G = 470
    box = (650, 85, 470, 460)                      # x, y, w, h
    xs = np.linspace(-1, 1, G)
    ys = np.linspace(-0.98, 0.98, int(G * box[3] / box[2]))
    X, Y = np.meshgrid(xs, ys)
    srcs = [(-0.82, -0.22), (-0.82, 0.22)]
    R = [np.hypot(X - sx, Y - sy) for sx, sy in srcs]
    k = 36.0
    bgc = np.array(BG, float)
    ca, cb = np.array(acc) * 255, np.array(acc2) * 255
    # kenar maskesi / soft mask
    mx = np.clip((1 - np.abs(X)) * 14, 0, 1) * np.clip((0.98 - np.abs(Y)) * 14, 0, 1)
    mx *= np.clip((X + 0.82) * 6, 0, 1)
    # ekran yoğunluğu / screen intensity (time-averaged)
    yy = np.linspace(-0.98, 0.98, 120)
    r1 = np.hypot(0.92 + 0.82, yy + 0.22)
    r2 = np.hypot(0.92 + 0.82, yy - 0.22)
    I = np.cos(k * (r1 - r2) / 2) ** 2

    def draw(ctx, arr, i):
        t = i / n
        A = sum(np.cos(k * r - TAU * t) / np.sqrt(r + 0.12) for r in R)
        A = np.round(np.clip(A / 2.2, -1, 1) * 7) / 7 * mx   # kademeli renk: küçük GIF / posterised: smaller GIF
        pos, neg = np.clip(A, 0, 1)[..., None], np.clip(-A, 0, 1)[..., None]
        img = bgc + (ca - bgc) * pos ** 1.1 + (cb - bgc) * neg ** 1.1 * 0.85
        im = Image.fromarray(img.astype(np.uint8)).resize((box[2], box[3]), Image.NEAREST)
        a = np.asarray(im)
        x, y, w, h = box
        region = arr[y : y + h, x : x + w]
        m = (np.asarray(Image.fromarray((mx * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)) / 255)[..., None]
        blended = region[..., [2, 1, 0]] * (1 - m) + a * m
        region[..., 0], region[..., 1], region[..., 2] = blended[..., 2], blended[..., 1], blended[..., 0]
        # kaynaklar / sources
        for sx, sy in srcs:
            px = x + (sx + 1) / 2 * w
            py = y + (sy + 0.98) / 1.96 * h
            glow_dot(ctx, px, py, 5, (1, 1, 1), 1)
        # ekran / screen with fringes
        sx = x + w + 22
        for j, v in enumerate(I):
            py = y + j / (len(I) - 1) * h
            ctx.rectangle(sx, py - 2.2, 8 + 26 * v, 4.4)
            ctx.set_source_rgba(*acc, 0.15 + 0.85 * v)
            ctx.fill()
    return n, draw


def scene_grover(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    N, TGT = 16, 11
    th = math.asin(1 / 4)
    s = [math.sin((2 * k + 1) * th) for k in range(4)]
    c = [math.cos((2 * k + 1) * th) / math.sqrt(15) for k in range(4)]
    PER, HOLD, RESET = 22, 16, 10
    n = 3 * PER + HOLD + RESET
    base, Hm, X0, BW = 395, 215, 662, 26

    def amps(i):
        mean = None
        if i < 3 * PER:
            k, j = divmod(i, PER)
            u = j / PER
            a = np.full(N, c[k])
            a[TGT] = s[k]
            if u < 0.4:                                  # kâhin / oracle flip
                a[TGT] = s[k] * (1 - 2 * ease(u / 0.35))
                return a, None, k
            a[TGT] = -s[k]
            m = a.mean()
            r = 2 * m - a
            v = ease((u - 0.45) / 0.5)
            return a + (r - a) * v, m, k
        j = i - 3 * PER
        a = np.full(N, c[3])
        a[TGT] = s[3]
        if j >= HOLD:
            v = ease((j - HOLD) / RESET)
            a = a + (np.full(N, 0.25) - a) * v
        return a, mean, 3

    def draw(ctx, arr, i):
        a, m, k = amps(i)
        ctx.move_to(X0 - 10, base)
        ctx.line_to(X0 + N * 30, base)
        ctx.set_source_rgba(0.6, 0.66, 0.85, 0.5)
        ctx.set_line_width(1.2)
        ctx.stroke()
        for q in range(N):
            x = X0 + q * 30
            h = a[q] * Hm
            y0, hh = (base - h, h) if h >= 0 else (base, -h)
            rounded_rect(ctx, x, y0, BW, max(hh, 2), 4)
            if q == TGT:
                ctx.set_source_rgba(*acc, 1)
                ctx.fill()
                if hh > 8:
                    glow(ctx, lambda x=x, y0=y0, hh=hh: rounded_rect(ctx, x, y0, BW, hh, 4), acc, 1.2, 0.7,
                         layers=((6, 0.05), (3, 0.1)))
            else:
                ctx.set_source_rgba(0.45, 0.52, 0.72, 0.65)
                ctx.fill()
        # hedef etiketi / target label
        text_c(ctx, "1011", X0 + TGT * 30 + BW / 2, base + 22 if a[TGT] >= 0 else base - 16, 12, acc, 0.95,
               font="DejaVu Sans Mono", bold=True)
        if m is not None:
            ym = base - m * Hm
            ctx.set_dash([6, 5])
            ctx.move_to(X0 - 10, ym)
            ctx.line_to(X0 + N * 30, ym)
            ctx.set_source_rgba(*acc2, 0.9)
            ctx.set_line_width(1.6)
            ctx.stroke()
            ctx.set_dash([])
            text_c(ctx, "⟨α⟩", X0 + N * 30 + 22, ym, 15, acc2, 0.95)
        # adım göstergesi / step indicator
        done = k + (1 if i >= 3 * PER else 0)
        lab = "adım" if lang == "tr" else "step"
        text_c(ctx, f"{lab} {min(done if i >= 3 * PER else k + 1, 3)} / 3", 900, 95, 18, (0.82, 0.86, 0.95), 0.9,
               font="Inter")
        for d in range(3):
            ctx.arc(870 + d * 30, 125, 6, 0, TAU)
            ctx.set_source_rgba(*(acc if d < done or (d == k and i < 3 * PER) else (0.35, 0.4, 0.55)), 0.95)
            ctx.fill()
        p = a[TGT] ** 2
        text_c(ctx, f"P = %{p * 100:.0f}" if lang == "tr" else f"P = {p:.0%}", X0 + TGT * 30 + BW / 2, max(base - a[TGT] * Hm - 22, 150), 15,
               (1, 1, 1), 0.9 if a[TGT] > 0.3 else 0, font="Inter", bold=True)
    return n, draw


def scene_qft(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    n = 96
    cols, rows, R = 4, 2, 52

    def draw(ctx, arr, i):
        t = i / n
        tips = []
        for k in range(8):
            cx = 690 + (k % cols) * 138
            cy = 230 + (k // cols) * 165
            ang = -math.pi / 2 + TAU * k * t      # k. dalga / k-th frequency
            ctx.arc(cx, cy, R, 0, TAU)
            ctx.set_source_rgba(*acc, 0.06)
            ctx.fill()
            # dolgu yayı / phase wedge
            ph = (TAU * k * t) % TAU
            ctx.move_to(cx, cy)
            ctx.arc(cx, cy, R - 4, -math.pi / 2, -math.pi / 2 + ph)
            ctx.close_path()
            ctx.set_source_rgba(*mix(acc, acc2, k / 7), 0.22)
            ctx.fill()
            glow(ctx, lambda cx=cx, cy=cy: ctx.arc(cx, cy, R, 0, TAU), acc, 1.3, 0.5, layers=((2.5, 0.08),))
            for tick in range(8):
                a = TAU * tick / 8
                ctx.move_to(cx + (R - 6) * math.cos(a), cy + (R - 6) * math.sin(a))
                ctx.line_to(cx + R * math.cos(a), cy + R * math.sin(a))
                ctx.set_source_rgba(*acc, 0.35)
                ctx.set_line_width(1)
                ctx.stroke()
            ex, ey = cx + (R - 8) * math.cos(ang), cy + (R - 8) * math.sin(ang)
            col = mix(acc, acc2, k / 7)
            glow(ctx, lambda cx=cx, cy=cy, ex=ex, ey=ey: (ctx.move_to(cx, cy), ctx.line_to(ex, ey)), col, 2.6)
            glow_dot(ctx, ex, ey, 3.5, col)
            text_c(ctx, f"|{k}⟩", cx, cy + R + 20, 15, (0.75, 0.8, 0.92), 0.9)
            tips.append(math.sin(ang + math.pi / 2))
        # alt dalga: fazların toplamı / bottom wave: interference of all phases
        def wave():
            for j in range(201):
                u = j / 200
                yv = sum(math.cos(TAU * k * (t - u * 0.25)) for k in range(8)) / 8
                x, y = 650 + 500 * u, 552 - 48 * yv
                (ctx.move_to if j == 0 else ctx.line_to)(x, y)
        glow(ctx, wave, acc2, 2.0, 0.85)
    return n, draw


def scene_encoding(post, lang):
    from sklearn.datasets import make_moons
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    X, y = make_moons(70, noise=0.08, random_state=0)
    Xs = (X - X.min(0)) / (X.max(0) - X.min(0))
    ang = Xs * np.array([math.pi, TAU])
    bloch = np.c_[np.sin(ang[:, 0]) * np.cos(ang[:, 1]), np.sin(ang[:, 0]) * np.sin(ang[:, 1]), np.cos(ang[:, 0])]
    panel = (650, 200, 170, 170)
    S = Sphere(1020, 315, 150, el=0.35)
    n = 80
    offs = np.random.default_rng(2).permutation(len(X)) / len(X)

    def draw(ctx, arr, i):
        t = i / n
        S.az = -0.5 + TAU * t * 0.25 * 0 + 0.35 * math.sin(TAU * t)
        px, py, pw, ph = panel
        rounded_rect(ctx, px, py, pw, ph, 14)
        ctx.set_source_rgba(*acc, 0.07)
        ctx.fill_preserve()
        ctx.set_source_rgba(*acc, 0.45)
        ctx.set_line_width(1.4)
        ctx.stroke()
        text_c(ctx, "x = (x₁, x₂)", px + pw / 2, py + ph + 24, 15, (0.75, 0.8, 0.92), 0.9)
        text_c(ctx, "RY(x₁) · RZ(x₂)", 905, 140, 15, acc, 0.95)
        ctx.move_to(845, 158)
        ctx.curve_to(880, 150, 930, 150, 965, 170)
        ctx.set_source_rgba(*acc, 0.4)
        ctx.set_line_width(1.2)
        ctx.stroke()
        S.frame(ctx, acc, labels=True)
        for j in range(len(X)):
            u = (t + offs[j]) % 1
            col = acc if y[j] == 0 else acc2
            a2 = px + 12 + Xs[j, 0] * (pw - 24), py + ph - 12 - Xs[j, 1] * (ph - 24)
            bx, by, depth = S.p(bloch[j])
            if u < 0.2:
                al = ease(u / 0.08)
                glow_dot(ctx, *a2, 2.6, col, al)
            elif u < 0.5:
                v = ease((u - 0.2) / 0.3)
                # eğri yol / curved path
                mx, my = (a2[0] + bx) / 2, min(a2[1], by) - 90
                xx = (1 - v) ** 2 * a2[0] + 2 * (1 - v) * v * mx + v * v * bx
                yy = (1 - v) ** 2 * a2[1] + 2 * (1 - v) * v * my + v * v * by
                glow_dot(ctx, xx, yy, 2.8, col, 1)
            else:
                al = 1 - ease((u - 0.88) / 0.12)
                glow_dot(ctx, bx, by, 2.8 if depth >= 0 else 2.0, col, al * (1 if depth >= 0 else 0.4))
            # panelde soluk iz / faint ghost on panel
            ctx.arc(*a2, 2, 0, TAU)
            ctx.set_source_rgba(*col, 0.25)
            ctx.fill()
    return n, draw


def scene_vqc(post, lang):
    sys.path.insert(0, str(ROOT / "09-variational-classifier"))
    import vqc_moons as V
    from skimage import measure

    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    G = 64
    gx, gy = np.meshgrid(np.linspace(-2.4, 2.4, G), np.linspace(2.4, -2.4, G))
    grid = np.c_[gx.ravel(), gy.ravel()]
    snaps = []

    def keep(epoch, p):
        if epoch in (1, 2, 3, 4, 5, 6, 8, 10, 13, 16, 20, 25, 30, 35, 40):
            Z = np.array(V.model(p, grid)).reshape(G, G)
            snaps.append((epoch, Z, V.accuracy(p, Xte, yte)))

    Xtr, Xte, ytr, yte = V.load_data()
    rng = np.random.default_rng(0)
    w0 = rng.normal(0, 0.6, (V.N_LAYERS, V.N_QUBITS, 3))
    Z0 = np.array(V.model([w0, 0.0], grid)).reshape(G, G)
    snaps.append((0, Z0, V.accuracy([w0, 0.0], Xte, yte)))
    V.train(on_epoch=keep)
    print("    VQC snapshots:", [(e, round(a, 2)) for e, _, a in snaps])

    PER, HOLD = 4, 18
    n = (len(snaps) - 1) * PER + HOLD
    box = (680, 95, 430, 430)
    bgc = np.array(BG, float)
    ca, cb = np.array(acc) * 255, np.array(acc2) * 255
    to_px = lambda x, yv: (box[0] + (x + 2.4) / 4.8 * box[2], box[1] + (2.4 - yv) / 4.8 * box[3])

    def draw(ctx, arr, i):
        if i < (len(snaps) - 1) * PER:
            k, j = divmod(i, PER)
            v = j / PER
            e0, Za, _ = snaps[k]
            e1, Zb, acc_b = snaps[k + 1]
            Z = Za * (1 - v) + Zb * v
            ep, accv = (e0 if v < 0.5 else e1), snaps[k if v < 0.5 else k + 1][2]
        else:
            ep, Z, accv = snaps[-1]
        Zb = np.asarray(Image.fromarray(np.clip(Z, -1, 1).astype(np.float32)).resize((box[2], box[3]), Image.BILINEAR))
        Zc = (np.round(Zb * 6) / 6)[..., None]          # kontur bantları / contour bands
        im = (bgc + (ca - bgc) * np.clip(Zc, 0, 1) * 0.55 + (cb - bgc) * np.clip(-Zc, 0, 1) * 0.55).astype(np.uint8)
        x, y, w, h = box
        region = arr[y : y + h, x : x + w]
        region[..., 0], region[..., 1], region[..., 2] = im[..., 2], im[..., 1], im[..., 0]
        # karar sınırı / decision boundary
        for cont in measure.find_contours(Z, 0.0):
            def path(cont=cont):
                for q, (r, c) in enumerate(cont):
                    px, py = x + c / (G - 1) * w, y + r / (G - 1) * h
                    (ctx.move_to if q == 0 else ctx.line_to)(px, py)
            glow(ctx, path, (1, 1, 1), 2.0, 0.9, layers=((3, 0.12),))
        for (xx, yv), lab in zip(Xtr, ytr):
            px, py = to_px(xx, yv)
            ctx.arc(px, py, 3.6, 0, TAU)
            ctx.set_source_rgba(*(acc if lab > 0 else acc2), 1)
            ctx.fill_preserve()
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.set_line_width(1)
            ctx.stroke()
        ctx.rectangle(x, y, w, h)
        ctx.set_source_rgba(*acc, 0.5)
        ctx.set_line_width(1.5)
        ctx.stroke()
        # çerçeve dışını kırp görünümü / clean the outside corners
        lab = "doğruluk" if lang == "tr" else "accuracy"
        text_c(ctx, f"epoch {ep:>2}", x + 70, y + h + 30, 17, (0.85, 0.88, 0.96), 0.95, font="DejaVu Sans Mono")
        text_c(ctx, f"{lab} %{accv * 100:.0f}" if lang == "tr" else f"{lab} {accv:.0%}", x + w - 95, y + h + 30, 17, acc, 0.95, font="Inter", bold=True)
        bar = min(ep / 40, 1)
        rounded_rect(ctx, x, y - 26, w, 6, 3)
        ctx.set_source_rgba(1, 1, 1, 0.08)
        ctx.fill()
        rounded_rect(ctx, x, y - 26, max(w * bar, 6), 6, 3)
        ctx.set_source_rgba(*acc, 0.95)
        ctx.fill()
    return n, draw


def scene_kernel(post, lang):
    sys.path.insert(0, str(ROOT / "10-quantum-kernels"))
    import quantum_kernel_svm as Q

    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    Xtr, Xte, ytr, yte = Q.load_data()
    order = np.lexsort((np.hypot(*Xtr.T), ytr))
    K = Q.kernel_matrix(Xtr, Xtr)[np.ix_(order, order)]
    M = len(K)
    SWEEP, HOLD, FADE = 44, 24, 10
    n = SWEEP + HOLD + FADE
    size = 400
    x0, y0 = 735, 315 - size // 2 - 10
    stops = [np.array(BG, float), np.array(acc2) * 0 + np.array(acc) * 255 * 0.6, np.array(acc) * 255,
             np.array([255, 240, 220.0])]

    def cmap(v):
        v = np.clip(v, 0, 1) ** 0.7 * 3
        i0 = np.clip(v.astype(int), 0, 2)
        f = (v - i0)[..., None]
        S = np.array(stops)
        return S[i0] * (1 - f) + S[i0 + 1] * f

    base_img = cmap(K)
    ii, jj = np.meshgrid(np.arange(M), np.arange(M), indexing="ij")
    diag = (ii + jj) / (2 * M - 2)
    # küçük halka verisi / small ring dataset preview
    def draw(ctx, arr, i):
        if i < SWEEP:
            front = ease(i / SWEEP) * 1.15
            vis = np.clip((front - diag) / 0.12, 0, 1)
        elif i < SWEEP + HOLD:
            vis = np.ones_like(diag)
        else:
            vis = np.ones_like(diag) * (1 - ease((i - SWEEP - HOLD) / FADE))
        img = np.array(BG, float) + (base_img - np.array(BG, float)) * vis[..., None]
        if i < SWEEP:
            band = np.exp(-((diag - front) / 0.03) ** 2)[..., None]
            img = img + (np.array([255, 255, 255.0]) - img) * band * 0.6
        im = np.asarray(Image.fromarray(img.astype(np.uint8)).resize((size, size), Image.NEAREST))
        region = arr[y0 : y0 + size, x0 : x0 + size]
        region[..., 0], region[..., 1], region[..., 2] = im[..., 2], im[..., 1], im[..., 0]
        ctx.rectangle(x0 - 0.5, y0 - 0.5, size + 1, size + 1)
        ctx.set_source_rgba(*acc, 0.6)
        ctx.set_line_width(1.2)
        ctx.stroke()
        # sınıf şeritleri / class strips
        nA = int((ytr == 0).sum())
        for (a, b, col) in ((0, nA, acc2), (nA, M, acc)):
            ctx.rectangle(x0 + a / M * size, y0 - 14, (b - a) / M * size - 2, 6)
            ctx.set_source_rgba(*col, 0.9)
            ctx.fill()
            ctx.rectangle(x0 - 14, y0 + a / M * size, 6, (b - a) / M * size - 2)
            ctx.fill()
        text_c(ctx, "K(x, x′) = |⟨φ(x)|φ(x′)⟩|²", x0 + size / 2, y0 + size + 34, 18, (0.88, 0.9, 0.98), 0.95)
    return n, draw


SCENES = {1: scene_qubit, 2: scene_entangle, 3: scene_teleport, 4: scene_dice, 5: scene_interference,
          6: scene_grover, 7: scene_qft, 8: scene_encoding, 9: scene_vqc, 10: scene_kernel}
GIF_OPTS = {5: "dither=none:diff_mode=rectangle", 9: "dither=none:diff_mode=rectangle"}
HERO = {1: 0.12, 2: 0.25, 3: 0.8, 4: 0.3, 5: 0.3, 6: 0.6, 7: 0.33, 8: 0.6, 9: 0.95, 10: 0.7}


def render(post, lang):
    n, draw = SCENES[post["n"]](post, lang)
    bg = static_layer(post, lang)
    tmp = Path(tempfile.mkdtemp())
    hero = int(HERO[post["n"]] * n)
    for i in range(n):
        arr = bg.copy()
        surf = cairo.ImageSurface.create_for_data(memoryview(arr), cairo.FORMAT_ARGB32, W, H)
        ctx = cairo.Context(surf)
        draw(ctx, arr, i)
        surf.flush()
        img = Image.fromarray(arr[..., [2, 1, 0]].copy(), "RGB")
        img.save(tmp / f"f{i:03d}.png")
        if i == hero:
            img.save(OUTDIR / f"{post['slug']}-{lang}.png", optimize=True)
    out = OUTDIR / f"{post['slug']}-{lang}.gif"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "f%03d.png"),
         "-vf", "split[a][b];[a]palettegen=max_colors=200:stats_mode=diff[p];"
                "[b][p]paletteuse=" + GIF_OPTS.get(post["n"], "dither=bayer:bayer_scale=4:diff_mode=rectangle"),
         "-loop", "0", str(out)], check=True)
    shutil.rmtree(tmp)
    print(f"  {out.name}: {n} kare/frames, {out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    OUTDIR.mkdir(exist_ok=True)
    want = {int(a) for a in sys.argv[1:]} or set(SCENES)
    for post in POSTS:
        if post["n"] in want:
            for lang in ("tr", "en"):
                render(post, lang)
