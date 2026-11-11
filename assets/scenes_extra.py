"""#11–#16 kapak sahneleri / cover scenes for posts 11–16 (make_covers.py tarafından yüklenir / loaded by make_covers.py)."""
import itertools
import math
import sys

import numpy as np
from PIL import Image

from make_covers import (BG, ROOT, TAU, Sphere, ease, glow, glow_dot, hex2rgb, mix, rounded_rect, text_c)

MUTED = (0.55, 0.62, 0.8)


def scene_digits(post, lang):
    sys.path.insert(0, str(ROOT / "11-qml-digits"))
    import quantum_digits as Q

    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    Xtr, Xte, ytr, yte, Ite, pca = Q.load_data()
    params = Q.train(epochs=12)
    pick = [k for k in range(len(Ite)) if (k % 2 == 0)][:6]
    preds = np.array(Q.model(params, Xte[pick]))
    PER = 16
    n = PER * len(pick)

    def draw(ctx, arr, i):
        k, j = divmod(i, PER)
        idx = pick[k]
        img = Ite[idx] / 16.0
        u = ease(min(j / 6, 1))
        # piksel ızgarası / pixel grid
        x0, y0, cs = 672, 175, 29
        for r in range(8):
            for c in range(8):
                v = img[r, c]
                rounded_rect(ctx, x0 + c * cs, y0 + r * cs, cs - 3, cs - 3, 4)
                ctx.set_source_rgba(*mix((0.12, 0.15, 0.25), acc, v), 0.35 + 0.65 * v)
                ctx.fill()
        text_c(ctx, "8 × 8 = 64", x0 + 4 * cs, y0 + 8 * cs + 22, 15, MUTED, 0.9)
        # PCA → 4 kübit / 4 qubits
        feats = Xte[idx]
        for q in range(4):
            cy = 185 + q * 72
            cx = 1000
            ctx.move_to(x0 + 8 * cs + 8, y0 + 4 * cs)
            ctx.curve_to(930, y0 + 4 * cs, 930, cy, cx - 30, cy)
            ctx.set_source_rgba(*acc, 0.18 + 0.3 * u)
            ctx.set_line_width(1.4)
            ctx.stroke()
            ctx.arc(cx, cy, 24, 0, TAU)
            ctx.set_source_rgba(*acc, 0.1)
            ctx.fill()
            glow(ctx, lambda cx=cx, cy=cy: ctx.arc(cx, cy, 24, 0, TAU), acc, 1.3, 0.7, layers=((2.5, 0.1),))
            a = -math.pi / 2 + feats[q] * u
            glow(ctx, lambda cx=cx, cy=cy, a=a: (ctx.move_to(cx, cy), ctx.line_to(cx + 20 * math.sin(a + math.pi / 2), cy - 20 * math.cos(a + math.pi / 2))),
                 acc2, 2.2)
            text_c(ctx, f"q{q}", cx - 42, cy, 13, MUTED, 0.9)
        # çıktı / output
        lab = Q.DIGITS[0] if preds[k] > 0 else Q.DIGITS[1]
        show = ease((j - 7) / 4)
        text_c(ctx, "→", 1075, 293, 30, MUTED, 0.6 + 0.4 * show)
        if show > 0:
            text_c(ctx, str(lab), 1128, 293, 78, acc2, show, font="Inter", bold=True)
            ok = (preds[k] > 0) == (yte[idx] > 0)
            text_c(ctx, "✓" if ok else "✗", 1128, 360, 22, acc if ok else (1, 0.4, 0.4), show)
    return n, draw


def scene_barren(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    # gerçek ölçümler / measured variances (barren_plateaus.py çıktısı / output)
    QN = [2, 3, 4, 5, 6, 7, 8, 9, 10]
    VG = [8.39e-02, 4.27e-02, 2.21e-02, 9.98e-03, 4.45e-03, 1.67e-03, 9.05e-04, 4.43e-04, 4.09e-04]
    VL = [8.90e-02, 6.52e-02, 8.31e-02, 6.91e-02, 5.30e-02, 4.54e-02, 5.70e-02, 4.36e-02, 4.42e-02]
    PER, HOLD = 9, 14
    n = PER * len(QN) + HOLD
    rng = np.random.default_rng(3)
    xs = np.linspace(0, 1, 260)
    base = sum(rng.normal(0, 1) * np.sin(TAU * (f * xs + rng.uniform())) / f ** 0.6 for f in range(1, 9))
    base = base / np.abs(base).max()

    def draw(ctx, arr, i):
        k = min(i // PER, len(QN) - 1)
        v = min((i % PER) / PER, 1) if i < PER * len(QN) else 1
        k2 = min(k + 1, len(QN) - 1) if i < PER * len(QN) else k
        amp_v = math.exp(math.log(VG[k]) * (1 - ease(v)) + math.log(VG[k2]) * ease(v))
        amp = 140 * math.sqrt(amp_v / VG[0])
        nq = QN[k2] if v > 0.5 else QN[k]
        # manzara / landscape
        X0, X1, YB = 650, 1150, 255

        def land():
            for t, b in enumerate(base):
                x = X0 + (X1 - X0) * xs[t]
                y = YB - amp * b
                (ctx.move_to if t == 0 else ctx.line_to)(x, y)
        land()
        ctx.line_to(X1, 420)
        ctx.line_to(X0, 420)
        ctx.close_path()
        ctx.set_source_rgba(*acc, 0.07)
        ctx.fill()
        glow(ctx, land, acc, 2.2, 0.95)
        # top ve gradyan oku / ball and gradient arrow
        t0 = 95
        bx, by = X0 + (X1 - X0) * xs[t0], YB - amp * base[t0]
        slope = -amp * (base[t0 + 1] - base[t0 - 1]) / ((X1 - X0) * (xs[t0 + 1] - xs[t0 - 1]))
        glow_dot(ctx, bx, by - 9, 8, acc2)
        L = 70 * slope / (abs(slope) + 0.4) if abs(slope) > 1e-6 else 0
        if abs(L) > 2:
            glow(ctx, lambda: (ctx.move_to(bx, by - 30), ctx.line_to(bx + L, by - 30)), acc2, 2.4)
        text_c(ctx, "∇", bx, by - 52, 18, acc2, 0.9)
        text_c(ctx, f"n = {nq}", 1080, 120, 26, (0.92, 0.94, 1), 0.95, font="Inter", bold=True)
        # küçük log grafik / mini log chart
        cx0, cy0, w, h = 690, 450, 440, 120
        ctx.rectangle(cx0, cy0, w, h)
        ctx.set_source_rgba(1, 1, 1, 0.03)
        ctx.fill()
        ymap = lambda val: cy0 + h * (math.log10(VG[0] * 1.6) - math.log10(val)) / (math.log10(VG[0] * 1.6) - math.log10(2e-4))
        xmap = lambda q: cx0 + 14 + (w - 28) * (q - 2) / 8
        for series, col in ((VL, acc2), (VG, acc)):
            upto = k2 if v > 0.5 else k
            def path(series=series):
                for m in range(upto + 1):
                    (ctx.move_to if m == 0 else ctx.line_to)(xmap(QN[m]), ymap(series[m]))
            glow(ctx, path, col, 1.8, 0.95, layers=((2.5, 0.1),))
            for m in range(upto + 1):
                ctx.arc(xmap(QN[m]), ymap(series[m]), 3.2, 0, TAU)
                ctx.set_source_rgba(*col, 1)
                ctx.fill()
        lab_g = "küresel" if lang == "tr" else "global"
        lab_l = "yerel" if lang == "tr" else "local"
        text_c(ctx, f"● {lab_l}", cx0 + w - 60, cy0 + 16, 13, acc2, 0.95, font="Inter")
        text_c(ctx, f"● {lab_g}", cx0 + w - 60, cy0 + 36, 13, acc, 0.95, font="Inter")
        text_c(ctx, "Var[∂C]", cx0 - 2 + 40, cy0 - 12, 13, MUTED, 0.9)
    return n, draw


def scene_maxcut(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (0, 3), (1, 4), (2, 5)]
    final = [1, 0, 1, 0, 1, 0]
    rng = np.random.default_rng(5)
    flick = rng.integers(0, 2, (200, 6))
    n = 84
    cx, cy, R = 900, 300, 190
    pos = [(cx + R * math.cos(-math.pi / 2 + TAU * k / 6), cy + R * math.sin(-math.pi / 2 + TAU * k / 6)) for k in range(6)]

    def draw(ctx, arr, i):
        t = i / n
        settle = ease((t - 0.35) / 0.25) * (1 - ease((t - 0.9) / 0.1))
        bits = [final[k] if settle > 0.5 else int(flick[i // 3, k]) for k in range(6)]
        for a, b in EDGES:
            (x0, y0), (x1, y1) = pos[a], pos[b]
            cut = bits[a] != bits[b]
            if cut and settle > 0.5:
                ctx.set_dash([7, 6], -i * 1.5)
                glow(ctx, lambda: (ctx.move_to(x0, y0), ctx.line_to(x1, y1)), mix(MUTED, (1, 1, 1), 0.4), 1.6, settle,
                     layers=((3, 0.08),))
                ctx.set_dash([])
            else:
                ctx.move_to(x0, y0)
                ctx.line_to(x1, y1)
                ctx.set_source_rgba(*MUTED, 0.5)
                ctx.set_line_width(2)
                ctx.stroke()
        for k, (x, y) in enumerate(pos):
            col = acc if bits[k] else acc2
            if settle < 0.5:
                col = mix(acc, acc2, 0.5 + 0.5 * math.sin(i * 0.9 + k))
            ctx.arc(x, y, 26, 0, TAU)
            ctx.set_source_rgba(*[c / 255 for c in BG], 1)
            ctx.fill()
            glow_dot(ctx, x, y, 17, col, 0.95)
            text_c(ctx, str(k), x, y, 15, (0.05, 0.07, 0.12), 1, font="Inter", bold=True)
        cut = sum(bits[a] != bits[b] for a, b in EDGES)
        lab = "kesim" if lang == "tr" else "cut"
        text_c(ctx, f"{lab} = {cut} / 9", cx, 545, 22, acc if settle > 0.5 else MUTED, 0.95, font="Inter", bold=True)
        text_c(ctx, "".join(map(str, bits)), cx, cy, 20, (0.85, 0.9, 1), 0.85, font="DejaVu Sans Mono", bold=True)
    return n, draw


def scene_landscape(post, lang):
    sys.path.insert(0, str(ROOT / "14-qaoa-landscape"))
    import networkx as nx
    import qaoa_landscape as Q

    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    G = nx.random_regular_graph(3, 8, seed=4)
    f1 = Q.make_qaoa(G, 1)
    gs, bs = np.linspace(0, np.pi, 33), np.linspace(0, np.pi / 2, 33)
    L = np.array([[-float(f1([[g], [b]])) for g in gs] for b in bs])
    # gradyan yükselişi yolu / gradient ascent path on the map
    import pennylane as qml
    from pennylane import numpy as pnp
    p = pnp.array([[0.35], [1.35]], requires_grad=True)
    opt = qml.AdamOptimizer(0.08)
    path = [np.array(p).ravel()]
    for _ in range(60):
        p = opt.step(f1, p)
        path.append(np.array(p).ravel())
    ratios = [0.801, 0.878, 0.936, 0.963]                      # qaoa_landscape.py çıktısı / output
    lo, hi = L.min(), L.max()
    stops = [np.array(BG, float), np.array(acc) * 255 * 0.55, np.array(acc) * 255, np.array([255, 240, 200.0])]
    v = (L - lo) / (hi - lo)
    v3 = np.clip(v, 0, 1) * 3
    i0 = np.clip(v3.astype(int), 0, 2)
    S = np.array(stops)
    img = S[i0] * (1 - (v3 - i0)[..., None]) + S[i0 + 1] * (v3 - i0)[..., None]
    img = np.flipud(img)
    size, x0, y0 = 360, 655, 110
    hm = np.asarray(Image.fromarray(img.astype(np.uint8)).resize((size, size), Image.BICUBIC))
    n = 84

    def draw(ctx, arr, i):
        region = arr[y0 : y0 + size, x0 : x0 + size]
        region[..., 0], region[..., 1], region[..., 2] = hm[..., 2], hm[..., 1], hm[..., 0]
        ctx.rectangle(x0, y0, size, size)
        ctx.set_source_rgba(*acc, 0.5)
        ctx.set_line_width(1.2)
        ctx.stroke()
        text_c(ctx, "γ", x0 + size / 2, y0 + size + 20, 17, MUTED, 0.95)
        text_c(ctx, "β", x0 - 18, y0 + size / 2, 17, MUTED, 0.95)
        to_px = lambda g, b: (x0 + g / np.pi * size, y0 + size - b / (np.pi / 2) * size)
        m = min(int(len(path) * ease(i / (n * 0.6))), len(path) - 1)
        def trail():
            for q in range(m + 1):
                (ctx.move_to if q == 0 else ctx.line_to)(*to_px(*path[q]))
        if m > 0:
            glow(ctx, trail, acc2, 2.0, 0.95, layers=((3, 0.12),))
        glow_dot(ctx, *to_px(*path[m]), 5, acc2)
        # p çubukları / bars for p
        bx, base, H = 1045, 470, 300
        for k, r in enumerate(ratios):
            grow = ease((i / n - 0.15 * k) / 0.35)
            h = H * (r - 0.6) / 0.4 * grow
            rounded_rect(ctx, bx + k * 30, base - h, 22, max(h, 1), 4)
            ctx.set_source_rgba(*mix(acc2, acc, k / 3), 0.95)
            ctx.fill()
            text_c(ctx, f"{k + 1}", bx + k * 30 + 11, base + 16, 13, MUTED, 0.9, font="Inter")
            if grow > 0.95:
                text_c(ctx, f"{r:.2f}", bx + k * 30 + 11, base - h - 12, 11, (0.9, 0.92, 1), 0.9, font="Inter")
        text_c(ctx, "p", bx + 56, base + 36, 15, MUTED, 0.9)
        ctx.move_to(bx - 6, base - H)
        ctx.line_to(bx + 120, base - H)
        ctx.set_dash([4, 4])
        ctx.set_source_rgba(1, 1, 1, 0.35)
        ctx.set_line_width(1)
        ctx.stroke()
        ctx.set_dash([])
        text_c(ctx, "r = 1", bx + 58, base - H - 14, 12, MUTED, 0.9, font="Inter")
    return n, draw


def scene_portfolio(post, lang):
    sys.path.insert(0, str(ROOT / "15-qaoa-portfolio"))
    import qaoa_portfolio as Q

    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    feasible = [b for b in itertools.product([0, 1], repeat=Q.N) if sum(b) == Q.K]
    ranked = sorted(feasible, key=Q.objective)
    pr = Q.run("xy")
    final = np.array([pr[int("".join(map(str, b)), 2)] for b in ranked])
    uni = np.full(len(ranked), 1 / len(ranked))
    best = ranked[0]
    n = 80

    def draw(ctx, arr, i):
        t = i / n
        u = ease((t - 0.1) / 0.5) * (1 - ease((t - 0.92) / 0.08))
        probs = uni + (final - uni) * u
        # hisse kartları / stock cards
        for k, name in enumerate(Q.NAMES):
            x = 690 + k * 76
            on = best[k] and u > 0.6
            rounded_rect(ctx, x, 110, 60, 74, 10)
            ctx.set_source_rgba(*(acc if on else (0.3, 0.35, 0.5)), 0.25 if on else 0.15)
            ctx.fill_preserve()
            ctx.set_source_rgba(*(acc if on else MUTED), 0.9 if on else 0.4)
            ctx.set_line_width(1.6)
            ctx.stroke()
            text_c(ctx, name, x + 30, 136, 22, acc if on else (0.85, 0.88, 0.96), 1, font="Inter", bold=True)
            text_c(ctx, f"{Q.MU[k] * 100:.0f}%", x + 30, 166, 12, MUTED, 0.9, font="Inter")
        # olasılık çubukları / probability bars
        base, H, bw = 520, 280, 20
        for m, p in enumerate(probs):
            x = 660 + m * 24.5
            h = H * p / 0.26
            isb = ranked[m] == best
            rounded_rect(ctx, x, base - h, bw, max(h, 2), 3)
            ctx.set_source_rgba(*(acc if isb else mix(acc2, MUTED, m / len(ranked))), 0.95 if isb else 0.75)
            ctx.fill()
        lab = "en iyi → en kötü" if lang == "tr" else "best → worst"
        text_c(ctx, lab, 900, base + 24, 14, MUTED, 0.9, font="Inter")
        text_c(ctx, f"P(BCE) = {probs[0]:.0%}" if lang == "en" else f"P(BCE) = %{probs[0] * 100:.0f}",
               760, base - H * probs[0] / 0.26 - 18, 15, acc, 0.95, font="Inter", bold=True)
    return n, draw


def scene_vqe(post, lang):
    acc, acc2 = hex2rgb(post["accent"]), hex2rgb(post["accent2"])
    # vqe_h2.py çıktısı / output
    D = [0.5, 0.6, 0.7, 0.74, 0.8, 0.9, 1.0, 1.2, 1.5, 1.8, 2.1]
    HF = [-1.04300, -1.10113, -1.11735, -1.11676, -1.11085, -1.09191, -1.06611, -1.00511, -0.91087, -0.82885, -0.76418]
    EX = [-1.05516, -1.11629, -1.13619, -1.13728, -1.13415, -1.12056, -1.10115, -1.05674, -0.99815, -0.96182, -0.94437]
    n = 88
    X0, X1, Y0, Y1 = 670, 1140, 230, 540
    xm = lambda d: X0 + (d - 0.45) / (2.15 - 0.45) * (X1 - X0)
    ym = lambda e: Y1 - (e + 1.16) / (-0.74 + 1.16) * (Y1 - Y0)

    def draw(ctx, arr, i):
        t = i / n
        # molekül / molecule: bağ uzunluğu ileri geri / bond length sweeps back and forth
        s = 0.5 - 0.5 * math.cos(TAU * t)
        d = 0.5 + s * 1.6
        e = float(np.interp(d, D, EX))
        sep = 50 + s * 120
        cx = 905
        glow(ctx, lambda: (ctx.move_to(cx - sep / 2, 140), ctx.line_to(cx + sep / 2, 140)), acc, 2.0,
             max(0.15, 1 - s * 0.9), layers=((3, 0.1),))
        for sgn in (-1, 1):
            glow_dot(ctx, cx + sgn * sep / 2, 140, 18, acc2)
            text_c(ctx, "H", cx + sgn * sep / 2, 140, 16, (0.05, 0.06, 0.12), 1, font="Inter", bold=True)
        text_c(ctx, f"{d:.2f} Å", cx, 182, 14, MUTED, 0.95, font="Inter")
        # eksenler / axes
        ctx.move_to(X0, Y0 - 10)
        ctx.line_to(X0, Y1)
        ctx.line_to(X1 + 10, Y1)
        ctx.set_source_rgba(*MUTED, 0.4)
        ctx.set_line_width(1)
        ctx.stroke()
        def curve(vals, dense=True):
            ds = np.linspace(D[0], D[-1], 120)
            ys = np.interp(ds, D, vals)
            for q, (a, b) in enumerate(zip(ds, ys)):
                (ctx.move_to if q == 0 else ctx.line_to)(xm(a), ym(b))
        ctx.set_dash([6, 5])
        curve(HF)
        ctx.set_source_rgba(*MUTED, 0.6)
        ctx.set_line_width(1.6)
        ctx.stroke()
        ctx.set_dash([])
        glow(ctx, lambda: curve(EX), acc, 2.2, 0.85)
        shown = int(len(D) * min(1, t / 0.7)) + (1 if t >= 0.7 else 0)
        for q in range(min(shown, len(D))):
            glow_dot(ctx, xm(D[q]), ym(EX[q]), 4.2, acc2)
        glow_dot(ctx, xm(d), ym(e), 6, (1, 1, 1))
        text_c(ctx, "HF", X1 - 10, ym(HF[-1]) - 16, 13, MUTED, 0.95, font="Inter")
        text_c(ctx, "VQE", X1 - 10, ym(EX[-1]) + 20, 13, acc2, 0.95, font="Inter", bold=True)
        lab = "Enerji" if lang == "tr" else "Energy"
        text_c(ctx, f"{lab}: {e:.4f} Ha", 1040, 255, 15, (0.9, 0.93, 1), 0.95, font="Inter")
        text_c(ctx, "0.74 Å", xm(0.74), Y1 + 18, 12, acc, 0.9, font="Inter")
    return n, draw


SCENES_EXTRA = {11: scene_digits, 12: scene_barren, 13: scene_maxcut, 14: scene_landscape,
                15: scene_portfolio, 16: scene_vqe}
HERO_EXTRA = {11: 0.8, 12: 0.4, 13: 0.7, 14: 0.75, 15: 0.75, 16: 0.35}
