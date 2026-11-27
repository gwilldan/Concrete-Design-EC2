"""Figures: analysis diagrams, reinforcement drawings, design charts, explanatory sketches."""
import math

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, FancyArrowPatch, Polygon, Rectangle

from .analysis import UDL, UVL, Moment, Point

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, CONC, STEEL = "#0b0b0b", "#52514e", "#e4e3df", "#e9e7e1", "#8a1c1c"
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 140, "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": .7,
                     "xtick.color": MUTED, "ytick.color": MUTED, "legend.frameon": False, "figure.constrained_layout.use": True})


def _bare(ax, equal=True):
    ax.axis("off")
    if equal:
        ax.set_aspect("equal")


def _arrow(ax, p, q, c=INK, lw=1.1, style="-|>", ms=9):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=ms, color=c, lw=lw, shrinkA=0, shrinkB=0))


def _dim(ax, p, q, text, off=0.0, fs=8, vertical=False, ha="center", va="center"):
    _arrow(ax, p, q, MUTED, .8, "<|-|>", 7)
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    ax.text(mx + (off if vertical else 0), my + (0 if vertical else off), text, ha=ha, va=va, fontsize=fs, color=INK, rotation=90 if vertical else 0)


def _loads(ax, loads, L, x0=0.0):
    wmax = max([abs(q.w) if isinstance(q, UDL) else max(q.w1, q.w2) if isinstance(q, UVL) else 0 for q in loads] + [1e-9])
    level = 0.0
    for q in loads:
        if isinstance(q, UDL):
            b = L if q.b is None else q.b
            h = .35 + .35 * q.w / wmax
            ax.add_patch(Rectangle((x0 + q.a, level + .08), b - q.a, h, fc="#dbe8f8", ec=BLUE, lw=.8))
            ax.text(x0 + (q.a + b) / 2, level + .08 + h / 2, f"{q.w:.4g} kN/m", ha="center", va="center", fontsize=8)
            level += h + .1
        elif isinstance(q, UVL):
            k = .7 / max(q.w1, q.w2)
            ax.add_patch(Polygon([(x0 + q.a, .08), (x0 + q.b, .08), (x0 + q.b, .08 + q.w2 * k), (x0 + q.a, .08 + q.w1 * k)], fc="#dbe8f8", ec=BLUE, lw=.8))
            ax.text(x0 + (q.a + q.b) / 2, .25, f"{q.w1:.4g} to {q.w2:.4g} kN/m", ha="center", fontsize=8)
            level = max(level, .85)
    for q in loads:
        if isinstance(q, Point):
            _arrow(ax, (x0 + q.a, level + .95), (x0 + q.a, level + .05), ORANGE, 1.6)
            ax.text(x0 + q.a, level + 1.0, f"{q.P:.4g} kN", ha="center", va="bottom", fontsize=8)
        elif isinstance(q, Moment):
            ax.add_patch(Arc((x0 + q.a, 0), L * .06, .9, theta1=30, theta2=330, color=ORANGE, lw=1.6))
            ax.text(x0 + q.a, .6, f"{q.M:.4g} kN·m", ha="center", fontsize=8)
    return level


def _support(ax, x, kind="pin", w=.12):
    if kind == "fixed":
        ax.plot([x, x], [-.5, .5], color=INK, lw=3)
    else:
        ax.add_patch(Polygon([(x, -.04), (x - w, -.42), (x + w, -.42)], fc="white", ec=INK, lw=1))


def _shade(ax, x, y, c, unit):
    ax.fill_between(x, y, 0, color=c, alpha=.13, lw=0)
    ax.plot(x, y, color=c, lw=2)
    ax.axhline(0, color=MUTED, lw=.9)
    ax.set_ylabel(unit)


def _tag(ax, x, y, c, inv=False):
    up = (y < 0) if inv else (y > 0)
    ax.plot([x], [y], "o", ms=5, color=c, mec="white", mew=1)
    ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 7 if up else -7), ha="center", va="bottom" if up else "top",
                fontsize=8, color=INK, bbox=dict(fc="white", ec="none", pad=.6, alpha=.85))


def determinate(bm, title=""):
    f, (a0, a1, a2) = plt.subplots(3, 1, figsize=(7.6, 6.6), sharex=True, height_ratios=[1.1, 1.2, 1.3])
    a0.plot([0, bm.L], [0, 0], color=INK, lw=4, solid_capstyle="butt")
    lv = _loads(a0, bm.loads, bm.L)
    if bm.fixed:
        _support(a0, 0, "fixed")
    else:
        for s in bm.supports:
            _support(a0, s, w=bm.L * .018)
    for s, R in bm.reactions.items():
        a0.text(s, -.6, f"R = {R:.2f} kN", ha="left" if s == 0 else "center", va="top", fontsize=8)
    a0.set_ylim(-1.1, max(1.5, lv + 1.5))
    a0.set_title(title or "Loading")
    a0.axis("off")
    _shade(a1, bm.x, bm.V, BLUE, "V (kN)")
    a1.set_title("Shear force")
    for i in {int(bm.V.argmax()), int(bm.V.argmin())}:
        if abs(bm.V[i]) > 1e-6:
            _tag(a1, bm.x[i], bm.V[i], BLUE)
    _shade(a2, bm.x, bm.M, ORANGE, "M (kN·m)")
    a2.invert_yaxis()
    a2.set_title("Bending moment (sagging plotted below, on the tension side)")
    for i in {int(bm.M.argmax()), int(bm.M.argmin())}:
        if abs(bm.M[i]) > 1e-6:
            _tag(a2, bm.x[i], bm.M[i], ORANGE, True)
    a2.set_xlabel("x (m)")
    for a in (a1, a2):
        a.margins(y=.22)
    plt.show()


def continuous(cb, title="", unit=""):
    f, (a0, a1, a2) = plt.subplots(3, 1, figsize=(8.2, 6.6), sharex=True, height_ratios=[1.1, 1.2, 1.3])
    off, lv, tot = 0, 0, sum(s.L for s in cb.spans)
    a0.plot([0, tot], [0, 0], color=INK, lw=4, solid_capstyle="butt")
    ohs = [(k, o, -o.L if k == 0 else tot) for k, o in enumerate(getattr(cb, "overhangs", (None, None))) if o is not None]
    for k, o, x0 in ohs:
        a0.plot([x0, x0 + o.L], [0, 0], color=INK, lw=4, solid_capstyle="butt")
        lv = max(lv, _loads(a0, o.loads, o.L, x0))
        a0.text(x0 + o.L / 2, -.35, f"L = {o.L:g} m", ha="center", va="top", fontsize=8, color=MUTED)
        a0.text(x0 + (o.L if k else 0), -.75, (chr(65 + len(cb.spans) + 1) + "\n" if k else "") + "free end", ha="center", va="top", fontsize=8)
    for i, s in enumerate(cb.spans):
        lv = max(lv, _loads(a0, s.loads, s.L, off))
        _support(a0, off, "fixed" if i == 0 and cb.left == "fixed" else "pin", w=tot * .012)
        a0.text(off + s.L / 2, -.35, f"L = {s.L:g} m" + (f",  I = {s.I:g}" if s.I != 1 else ""), ha="center", va="top", fontsize=8, color=MUTED)
        off += s.L
    _support(a0, off, "fixed" if cb.right == "fixed" else "pin", w=tot * .012)
    off = 0
    for j, n in enumerate(cb.names):
        a0.text(off, -.75, f"{n}\n{cb.R[j]:.1f} kN", ha="center", va="top", fontsize=8)
        off += cb.spans[j].L if j < len(cb.spans) else 0
    a0.set_ylim(-1.7, max(1.5, lv + 1.4))
    a0.axis("off")
    a0.set_title(title or "Loading and reactions")
    od = getattr(cb, "oh_diagrams", (None, None))
    segs = [d for d in (od[0], *zip(cb.X, cb.V, cb.M), od[1]) if d is not None]
    x, V, M = (np.concatenate(c) for c in zip(*segs))
    _shade(a1, x, V, BLUE, "V (kN)")
    a1.set_title("Shear force")
    _shade(a2, x, M, ORANGE, "M (kN·m)")
    a2.invert_yaxis()
    a2.set_title("Bending moment (sagging plotted below)")
    for X, v, m in segs:
        for i in (0, -1):
            if abs(v[i]) > 1e-6:
                _tag(a1, X[i], v[i], BLUE)
        i = int(m.argmax())
        if m[i] > 1e-6:
            _tag(a2, X[i], m[i], ORANGE, True)
    off = 0
    for j, m in enumerate(cb.M_sup):
        if abs(m) > 1e-3:
            _tag(a2, off, m, ORANGE, True)
        off += cb.spans[j].L if j < len(cb.spans) else 0
    a2.set_xlabel("x (m)")
    for a in (a1, a2):
        a.margins(y=.25)
    plt.show()


def envelope(cases, title="Design envelope"):
    """cases: {name: ContinuousBeam (diagrams run)}. Returns x, Vmax, Vmin, Mmax, Mmin."""
    f, (a1, a2) = plt.subplots(2, 1, figsize=(8.2, 5.6), sharex=True)
    x = np.concatenate(next(iter(cases.values())).X)
    Vs = np.array([np.concatenate(c.V) for c in cases.values()])
    Ms = np.array([np.concatenate(c.M) for c in cases.values()])
    for (n, c), col, ls in zip(cases.items(), (BLUE, ORANGE, AQUA), ("-", "--", "-.")):
        a1.plot(x, np.concatenate(c.V), color=col, lw=1.6, ls=ls, label=n)
        a2.plot(x, np.concatenate(c.M), color=col, lw=1.6, ls=ls, label=n)
    a1.fill_between(x, Vs.max(0), Vs.min(0), color=MUTED, alpha=.10, lw=0)
    a2.fill_between(x, np.maximum(Ms.max(0), 0), np.minimum(Ms.min(0), 0), color=MUTED, alpha=.10, lw=0)
    for a in (a1, a2):
        a.axhline(0, color=MUTED, lw=.9)
        a.margins(y=.15)
    a1.set_ylabel("V (kN)")
    a2.set_ylabel("M (kN·m)")
    a2.invert_yaxis()
    a1.set_title(title + " – shear")
    a2.set_title("Bending moment (sagging below)")
    a1.legend(loc="upper center", bbox_to_anchor=(.5, -.02), ncol=3, fontsize=8)
    a2.set_xlabel("x (m)")
    plt.show()
    return x, Vs.max(0), Vs.min(0), Ms.max(0), Ms.min(0)


# ---------------------------------------------------------------- reinforcement drawings
def beam_section(b, h, cnom, link, top, bot, title="", hf=0, beff=0):
    """top/bot = (n, phi)."""
    f, ax = plt.subplots(figsize=(4.6, 4.4))
    if beff:
        w = min(beff, 3 * b)
        ax.add_patch(Polygon([(-(w - b) / 2, h - hf), (-(w - b) / 2, h), (b + (w - b) / 2, h), (b + (w - b) / 2, h - hf), (b, h - hf), (b, 0), (0, 0), (0, h - hf)], fc=CONC, ec=INK, lw=1.2))
    else:
        ax.add_patch(Rectangle((0, 0), b, h, fc=CONC, ec=INK, lw=1.2))
    ax.add_patch(Rectangle((cnom + link / 2, cnom + link / 2), b - 2 * cnom - link, h - 2 * cnom - link, fc="none", ec=STEEL, lw=1.8))
    for (n, p), y in ((bot, cnom + link + bot[1] / 2), (top, h - cnom - link - top[1] / 2)):
        x0 = cnom + link + p / 2
        for x in np.linspace(x0, b - x0, n):
            ax.add_patch(Circle((x, y), p / 2, fc=STEEL, ec="none"))
    ax.annotate(f"{top[0]}H{top[1]}", (b - 60, h - cnom - link - top[1] / 2), (b / 2, h + 45), fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED), va="center")
    ax.annotate(f"{bot[0]}H{bot[1]}", (b - 60, cnom + link + bot[1] / 2), (b + 60, 70), fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED), va="center")
    ax.annotate(f"H{link} links\ncover {cnom}", (b - cnom, h * .45), (b + 60, h * .45), fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED), va="center")
    _dim(ax, (0, -40), (b, -40), f"{b}", -25)
    xl = -(min(beff, 3 * b) - b) / 2 - 35 if beff else -45
    _dim(ax, (xl, 0), (xl, h), f"{h}", -28, vertical=True)
    ax.set_xlim(xl - 70, b + max(240, (min(beff, 3 * b) - b) / 2 + 40 if beff else 0))
    ax.set_ylim(-95, h + 75)
    ax.set_title(title)
    _bare(ax)
    plt.show()


def slab_section(h, cnom, bot, top=None, dist=None, title=""):
    """bot/top/dist = (phi, spacing); section cut across the bars."""
    f, ax = plt.subplots(figsize=(7.8, 2.4))
    W = 1000
    ax.add_patch(Rectangle((0, 0), W, h, fc=CONC, ec=INK, lw=1.2))
    for x in np.arange(bot[1] / 2, W, bot[1]):
        ax.add_patch(Circle((x, cnom + bot[0] / 2), max(bot[0] / 2, 6), fc=STEEL, ec="none"))
    txt = [f"Bottom: H{bot[0]} @ {bot[1]}"]
    if dist:
        y = cnom + bot[0] + dist[0] / 2
        ax.plot([0, W], [y, y], color=BLUE, lw=2)
        txt.append(f"Transverse (blue): H{dist[0]} @ {dist[1]}")
    if top:
        for x in np.arange(top[1] / 2, W, top[1]):
            ax.add_patch(Circle((x, h - cnom - top[0] / 2), max(top[0] / 2, 6), fc=STEEL, ec="none"))
        txt.append(f"Top: H{top[0]} @ {top[1]}")
    _dim(ax, (-25, 0), (-25, h), f"{h}", -22, vertical=True)
    _dim(ax, (0, -28), (W, -28), "1000 mm strip", -26)
    ax.text(W / 2, h + 14, "   |   ".join(txt) + f"   |   cover {cnom}", ha="center", fontsize=8.5)
    ax.set_xlim(-85, W + 20)
    ax.set_ylim(-80, h + 50)
    ax.set_title(title)
    _bare(ax)
    plt.show()


def column_section(b, h, c, link, layers_n, phi, title=""):
    """layers_n = bars along faces (n_b, n_h)."""
    f, ax = plt.subplots(figsize=(3.9, 3.9))
    ax.add_patch(Rectangle((0, 0), b, h, fc=CONC, ec=INK, lw=1.2))
    ax.add_patch(Rectangle((c + link / 2, c + link / 2), b - 2 * c - link, h - 2 * c - link, fc="none", ec=STEEL, lw=1.8))
    o = c + link + phi / 2
    nb, nh = layers_n
    pts = {(round(x, 3), y) for x in np.linspace(o, b - o, nb) for y in (o, h - o)} | {(x, round(y, 3)) for y in np.linspace(o, h - o, nh) for x in (o, b - o)}
    for x, y in pts:
        ax.add_patch(Circle((x, y), phi / 2, fc=STEEL, ec="none"))
    _dim(ax, (0, -30), (b, -30), f"{b}", -22)
    _dim(ax, (-30, 0), (-30, h), f"{h}", -22, vertical=True)
    ax.text(b / 2, h + 12, f"{2 * nb + 2 * (nh - 2)}H{phi}, H{link} links, cover {c}", ha="center", fontsize=9)
    ax.set_xlim(-80, b + 25)
    ax.set_ylim(-75, h + 45)
    ax.set_title(title)
    _bare(ax)
    plt.show()


def interaction_plot(curve, points, title="Axial force – moment interaction (EC2 6.1)"):
    f, ax = plt.subplots(figsize=(6.4, 4.8))
    ax.plot(curve[:, 1], curve[:, 0], color=BLUE, lw=2)
    ax.fill_betweenx(curve[:, 0], 0, curve[:, 1], color=BLUE, alpha=.08, lw=0)
    for k, (lab, N, M) in enumerate(points):
        ax.plot(M, N, "osD^"[k % 4], color=(ORANGE, AQUA, INK, MUTED)[k % 4], ms=8, mec="white", mew=1.2, ls="none", label=f"{lab}: N = {N:.0f} kN, M = {M:.1f} kN·m")
    ax.legend(fontsize=8, loc="upper right")
    ax.axhline(0, color=MUTED, lw=.9)
    ax.set_xlim(left=0)
    ax.set_xlabel("M (kN·m)")
    ax.set_ylabel("N (kN), compression positive")
    ax.set_title(title)
    plt.show()


def pad(B, L, h, c1, c2, d, phi, spacing, cover, title="Pad footing"):
    f, (a, p) = plt.subplots(1, 2, figsize=(9.2, 4.2))
    a.add_patch(Rectangle((0, 0), L, h, fc=CONC, ec=INK, lw=1.2))
    a.add_patch(Rectangle((L / 2 - c1 / 2, h), c1, h * .9, fc=CONC, ec=INK, lw=1.2))
    a.plot([cover, L - cover], [cover + phi / 2] * 2, color=STEEL, lw=2.2)
    for x in np.arange(cover + phi, L - cover, spacing):
        a.add_patch(Circle((x, cover + 1.5 * phi), 12, fc=STEEL, ec="none"))
    for sx in (L / 2 - c1 / 2 + 50, L / 2 + c1 / 2 - 50):
        e = -180 if sx < L / 2 else 180
        a.plot([sx, sx, sx + e], [h * 1.85, cover + 2.5 * phi, cover + 2.5 * phi], color=BLUE, lw=2)
    _dim(a, (0, -90), (L, -90), f"{L}", -90)
    _dim(a, (-90, 0), (-90, h), f"{h}", -100, vertical=True)
    a.text(L * .98, h * 1.35, f"H{phi} @ {spacing} both ways\ncover {cover}\nstarter bars (blue)", ha="right", fontsize=8.5)
    a.set_xlim(-330, L + 60)
    a.set_ylim(-300, h * 2)
    a.set_title(title + " – section")
    _bare(a)
    p.add_patch(Rectangle((0, 0), L, B, fc=CONC, ec=INK, lw=1.2))
    cx, cy = L / 2, B / 2
    p.add_patch(Rectangle((cx - c1 / 2, cy - c2 / 2), c1, c2, fc="#b9b6ad", ec=INK))
    p.plot([cx + c1 / 2] * 2, [0, B], color=ORANGE, lw=1.6, label="Bending: column face")
    p.plot([cx + c1 / 2 + d] * 2, [0, B], color=BLUE, lw=1.6, ls="--", label="Shear: d from face")
    t = np.linspace(0, 2 * np.pi, 400)
    for k, ls in ((1.0, "-."),):
        r = k * d
        X = cx + np.sign(np.cos(t)) * c1 / 2 + r * np.cos(t)
        Y = cy + np.sign(np.sin(t)) * c2 / 2 + r * np.sin(t)
        p.plot(X, Y, color=AQUA, lw=1.6, ls=ls, label="Punching perimeter (a = d shown)")
    p.set_xlim(-60, L + 60)
    p.set_ylim(-60, B + 60)
    p.set_title("Plan – critical sections")
    p.legend(loc="upper center", bbox_to_anchor=(.5, -.01), fontsize=8)
    _bare(p)
    plt.show()


def punching_plot(rows, d):
    a = np.array([r[0] for r in rows]) / d
    f, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.plot(a, [r[3] for r in rows], color=ORANGE, lw=2, label="$v_{Ed}$")
    ax.plot(a, [r[4] for r in rows], color=BLUE, lw=2, ls="--", label="$v_{Rd}$")
    ax.set_xlabel("a / d  (distance of control perimeter from the column face)")
    ax.set_ylabel("Shear stress (N/mm² = MPa)")
    ax.set_ylim(0, max(r[3] for r in rows) * 2.5 + .5)
    ax.set_title("Punching shear: every perimeter within 2d (EC2 6.4.4(2))")
    ax.legend()
    plt.show()


def ld_chart(fcks=(25, 30, 40), K=1.0):
    r = np.linspace(.0025, .02, 300)
    f, ax = plt.subplots(figsize=(6.6, 3.8))
    for fck, c, ls in zip(fcks, (BLUE, ORANGE, AQUA), ("-", "--", "-.")):
        r0, q = 1e-3 * math.sqrt(fck), math.sqrt(fck)
        y = np.where(r <= r0, K * (11 + 1.5 * q * r0 / r + 3.2 * q * np.maximum(r0 / r - 1, 0)**1.5), K * (11 + 1.5 * q * r0 / r))
        ax.plot(100 * r, np.minimum(y, 40 * K), color=c, ls=ls, lw=2, label=f"fck = {fck} N/mm²")
    ax.set_xlabel("Required tension steel ratio ρ (%)")
    ax.set_ylabel("Basic l/d (simply supported, K = 1)")
    ax.set_title("EC2 Exp. (7.16), capped at 40K (UK NA)")
    ax.legend()
    plt.show()


def shear_chart(fck=30):
    r = np.linspace(.001, .02, 200)
    f, ax = plt.subplots(figsize=(6.6, 3.8))
    for d, c, ls in zip((150, 300, 600), (BLUE, ORANGE, AQUA), ("-", "--", "-.")):
        k = min(1 + math.sqrt(200 / d), 2)
        ax.plot(100 * r, np.maximum(.12 * k * (100 * r * fck)**(1 / 3), .035 * k**1.5 * math.sqrt(fck)), color=c, ls=ls, lw=2, label=f"d = {d} mm")
    ax.set_xlabel("ρl (%)")
    ax.set_ylabel("vRd,c (N/mm² = MPa)")
    ax.set_title(f"Concrete shear resistance, fck = {fck} N/mm² (EC2 Exp. 6.2)")
    ax.legend()
    plt.show()


def k_z_chart():
    K = np.linspace(0, .207, 200)
    z = np.minimum(.5 * (1 + np.sqrt(1 - 2 * K / .56667)), .95)
    f, ax = plt.subplots(figsize=(6.6, 3.4))
    ax.plot(K, z, color=BLUE, lw=2)
    ax.axvline(.167, color=ORANGE, ls="--", lw=1.4)
    ax.text(.1655, .93, "K′ = 0.167 (x/d = 0.45)", ha="right", fontsize=8.5)
    ax.set_xlabel("K = M / (b d² fck)")
    ax.set_ylabel("z / d")
    ax.set_title("Lever-arm curve, fck ≤ 50 N/mm², αcc = 0.85")
    plt.show()


def stress_strain():
    f, (a, b) = plt.subplots(1, 2, figsize=(8.4, 3.2))
    e = np.linspace(0, 3.5, 200)
    s = np.where(e < 2, 1 - (1 - e / 2)**2, 1)
    a.plot(e, s, color=BLUE, lw=2, label="parabola-rectangle (Fig. 3.3)")
    a.plot([.7, .7, 3.5], [0, 1, 1], color=ORANGE, ls="--", lw=2, label="rectangular block (Fig. 3.5)")
    a.set_xlabel("strain (‰)")
    a.set_ylabel("stress / fcd")
    a.set_ylim(0, 1.45)
    a.legend(fontsize=8, loc="upper left")
    a.set_title("Concrete, fck ≤ 50 N/mm²")
    fyd = 500 / 1.15
    b.plot([0, fyd / 200, 12], [0, fyd, fyd], color=BLUE, lw=2)
    b.annotate(f"fyd = {fyd:.0f} N/mm² at {fyd / 200:.2f} ‰", (fyd / 200, fyd), (4, 300), arrowprops=dict(arrowstyle="-", color=MUTED), fontsize=8.5)
    b.set_xlabel("strain (‰)")
    b.set_ylabel("stress (N/mm² = MPa)")
    b.set_title("B500 steel, horizontal branch (Fig. 3.8)")
    plt.show()


# ---------------------------------------------------------------- explanatory sketches
def sketch_block():
    f, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.add_patch(Rectangle((0, 0), 2, 4, fc=CONC, ec=INK))
    ax.add_patch(Rectangle((0, 2.72), 2, 1.28, fc="#cfe0f5", ec=BLUE))
    for x in (.45, 1, 1.55):
        ax.add_patch(Circle((x, .5), .12, fc=STEEL))
    ax.text(1, -.35, "Section", ha="center")
    ax.plot([3.6, 3.6], [.5, 4], color=MUTED, lw=.8)
    ax.plot([3.6, 4.5, 3.6], [4, 4, 2.4], color=INK)
    ax.plot([3.6, 2.6, 2.6, 3.6], [2.4, .5, .5, .5], color=INK)
    ax.text(4.55, 4, r"$\varepsilon_{cu}$ = 3.5‰", va="center", fontsize=9)
    ax.text(2.55, .25, r"$\varepsilon_s$", ha="center")
    ax.text(3.6, -.35, "Strain", ha="center")
    ax.plot([6.2, 6.2], [.5, 4], color=MUTED, lw=.8)
    ax.add_patch(Rectangle((6.2, 2.72), 1.1, 1.28, fc="#cfe0f5", ec=BLUE))
    ax.text(6.75, 4.1, r"$\eta f_{cd}$", ha="center", va="bottom")
    _arrow(ax, (9.0, 3.36), (7.4, 3.36), BLUE, 1.6)
    ax.text(9.05, 3.36, r"$F_c=\eta f_{cd}\,b\,\lambda x$", va="center")
    _arrow(ax, (6.2, .5), (8.0, .5), STEEL, 1.6)
    ax.text(8.1, .5, r"$F_s=A_s f_{yd}$", va="center")
    _arrow(ax, (5.8, 2.4), (5.8, 4), MUTED, .8, "<|-|>", 7)
    ax.text(5.55, 3.2, "x")
    _dim(ax, (7.75, 2.72), (7.75, 4), "", 0)
    _arrow(ax, (8.6, .6), (8.6, 3.3), MUTED, .8, "<|-|>", 7)
    ax.text(8.75, 1.9, "z")
    _arrow(ax, (-.35, .5), (-.35, 4), MUTED, .8, "<|-|>", 7)
    ax.text(-.65, 2.2, "d")
    ax.text(7.65, 2.4, r"$\lambda x$", fontsize=9)
    ax.text(6.9, -.35, "Stress block (EC2 Fig. 3.5)", ha="center")
    ax.set_xlim(-1, 11.4)
    ax.set_ylim(-.7, 4.7)
    _bare(ax)
    plt.show()


def sketch_truss():
    f, ax = plt.subplots(figsize=(8.2, 2.9))
    ax.add_patch(Rectangle((0, 0), 8, 1.8, fc=CONC, ec=INK))
    ax.plot([0, 8], [1.55, 1.55], color=BLUE, lw=4, alpha=.6)
    ax.plot([0, 8], [.25, .25], color=STEEL, lw=3)
    for x in np.arange(.4, 7, 1.3):
        ax.plot([x, x + 2.2 if x + 2.2 < 8 else 8], [.25, 1.55], color=BLUE, lw=5, alpha=.25)
    for x in np.arange(.5, 8, .5):
        ax.plot([x, x], [.25, 1.55], color=STEEL, lw=1.2)
    ax.text(8.15, 1.55, "compression chord", va="center")
    ax.text(8.15, .25, "tension chord (main bars)", va="center")
    ax.text(8.15, .9, "struts at θ, links as ties", va="center")
    ax.set_xlim(-.2, 11)
    ax.set_ylim(-.2, 2)
    ax.set_title("Variable strut inclination truss (EC2 Fig. 6.5)")
    _bare(ax)
    plt.show()


def sketch_slab_load(lx=5, ly=6):
    f, (a, b) = plt.subplots(1, 2, figsize=(8.8, 3.6))
    a.add_patch(Rectangle((0, 0), 3.2, 6.6 * 1.05, fc=CONC, ec=INK, lw=1.5))
    for y in np.arange(.8, 6.6, 1):
        _arrow(a, (1.6, y), (.1, y), BLUE)
        _arrow(a, (1.6, y), (3.1, y), BLUE)
    a.set_title("One-way: ly/lx > 2 (EC2 5.3.1(5))")
    a.text(1.6, -.5, "load to the two long beams: w = n·lx / 2", ha="center", fontsize=8.5)
    a.set_ylim(-1, 7.4)
    a.set_xlim(-1.5, 4.7)
    _bare(a)
    h = lx / 2
    b.add_patch(Polygon([(0, 0), (ly, 0), (ly - h, h), (h, h)], fc="#cfe0f5", ec=INK))
    b.add_patch(Polygon([(0, lx), (ly, lx), (ly - h, h), (h, h)], fc="#cfe0f5", ec=INK))
    b.add_patch(Polygon([(0, 0), (0, lx), (h, h)], fc="#fbdccd", ec=INK))
    b.add_patch(Polygon([(ly, 0), (ly, lx), (ly - h, h)], fc="#fbdccd", ec=INK))
    b.text(ly / 2, h / 2.4, "trapezium to long beam", ha="center", fontsize=8)
    b.text(ly / 2, lx - h / 2.4, "trapezium to long beam", ha="center", fontsize=8)
    b.text(.12, h, "triangle to\nshort beam", va="center", fontsize=7.5)
    b.text(ly - .12, h, "triangle to\nshort beam", va="center", ha="right", fontsize=7.5)
    _dim(b, (0, -.35), (ly, -.35), f"ly = {ly} m", -.3)
    _dim(b, (-.35, 0), (-.35, lx), f"lx = {lx} m", -.3, vertical=True)
    b.set_title("Two-way: ly/lx ≤ 2, 45° tributary areas")
    b.set_xlim(-1, ly + .3)
    b.set_ylim(-1, lx + .3)
    _bare(b)
    plt.show()


def sketch_plan(bx=None, by=None):
    from .project import BRIEF
    bx, by = bx or (BRIEF["lx_bay"],) * 3, by or (BRIEF["ly_bay"],) * 3
    f, ax = plt.subplots(figsize=(7.4, 5.0))
    X, Y = np.concatenate([[0], np.cumsum(bx)]), np.concatenate([[0], np.cumsum(by)])
    for x in X:
        ax.plot([x, x], [0, Y[-1]], color=MUTED, lw=2.4)
    for y in Y:
        ax.plot([0, X[-1]], [y, y], color=MUTED, lw=2.4)
    for i, x in enumerate(X):
        ax.add_patch(Circle((x, Y[-1] + 1.1), .45, fc="white", ec=INK))
        ax.text(x, Y[-1] + 1.1, str(i + 1), ha="center", va="center")
        for y in Y:
            ax.add_patch(Rectangle((x - .2, y - .2), .4, .4, fc=INK))
    for y, n in zip(Y, "ABCD"):
        ax.add_patch(Circle((-1.1, y), .45, fc="white", ec=INK))
        ax.text(-1.1, y, n, ha="center", va="center")
    ax.add_patch(Rectangle((X[0], Y[0]), bx[0], by[0], fc="#cfe0f5", ec="none", zorder=0))
    ax.text(bx[0] / 2, by[0] / 2, "Panel P1\n(corner)", ha="center", va="center", fontsize=8.5)
    ax.plot([0, X[-1]], [Y[1]] * 2, color=BLUE, lw=4)
    ax.text(X[-1] + .4, Y[1], "Beam B", color=INK, va="center", fontsize=8.5)
    ax.plot([X[1]] * 2, [0, Y[-1]], color=AQUA, lw=4, zorder=1)
    ax.text(X[1] + .15, Y[-1] + .3, "Beam 2", fontsize=8.5)
    ax.add_patch(Circle((X[1], Y[1]), .55, fc="none", ec=ORANGE, lw=2.4))
    ax.text(X[1] + .6, Y[1] + .55, "Column B2", fontsize=8.5, weight="bold")
    ax.add_patch(Circle((X[0], Y[0]), .55, fc="none", ec=ORANGE, lw=1.6))
    ax.text(X[0] + .6, Y[0] + .5, "Column A1", fontsize=8.5)
    _dim(ax, (X[0], -1), (X[1], -1), f"{bx[0]} m", -.45)
    _dim(ax, (X[1], -1), (X[2], -1), f"{bx[1]} m", -.45)
    _dim(ax, (X[2], -1), (X[3], -1), f"{bx[2]} m", -.45)
    for i in range(3):
        _dim(ax, (X[-1] + 2.6, Y[i]), (X[-1] + 2.6, Y[i + 1]), f"{by[i]} m", .45, vertical=True)
    ax.set_xlim(-2, X[-1] + 3.6)
    ax.set_ylim(-2, Y[-1] + 1.9)
    ax.set_title("Typical floor plan of the example building")
    _bare(ax)
    plt.show()


def sketch_load_path():
    f, ax = plt.subplots(figsize=(8.4, 1.5))
    for i, t in enumerate(["Area load\nn (kN/m²)", "Slab", "Beams", "Columns", "Pad footing", "Soil\n(bearing)"]):
        ax.add_patch(Rectangle((i * 2, 0), 1.5, 1, fc=CONC if 0 < i < 5 else "#dbe8f8", ec=INK))
        ax.text(i * 2 + .75, .5, t, ha="center", va="center", fontsize=8.5)
        if i < 5:
            _arrow(ax, (i * 2 + 1.52, .5), (i * 2 + 1.98, .5), ORANGE, 1.6)
    ax.set_xlim(-.1, 11.7)
    ax.set_ylim(-.1, 1.2)
    _bare(ax)
    plt.show()


def sketch_columns():
    f, axs = plt.subplots(1, 4, figsize=(8.8, 3.0))
    y = np.linspace(0, 3, 60)
    shapes = [("pinned–pinned\nl0 = l", .35 * np.sin(np.pi * y / 3)), ("fixed–free\nl0 = 2l", .45 * (1 - np.cos(np.pi * y / 6))),
              ("braced frame\n0.5l < l0 < l", .22 * (np.sin(np.pi * y / 3) - .35 * np.sin(np.pi * y / 3)**3)), ("unbraced frame\nl0 > l", .3 * (1 - np.cos(np.pi * y / 3)))]
    for ax, (t, s) in zip(axs, shapes):
        ax.plot([0, 0], [0, 3], color=MUTED, lw=1, ls=":")
        ax.plot(s, y, color=BLUE, lw=2.4)
        ax.plot([-.35, .35], [0, 0], color=INK, lw=2)
        _arrow(ax, (s[-1], 3.75), (s[-1], 3.05), ORANGE, 1.6)
        ax.set_title(t, fontsize=9, loc="center", fontweight="normal")
        ax.set_xlim(-.9, 1.2)
        ax.set_ylim(-.2, 3.9)
        _bare(ax)
    plt.show()


def sketch_flange():
    f, ax = plt.subplots(figsize=(7, 2.5))
    ax.add_patch(Polygon([(0, 1.2), (0, 1.7), (8, 1.7), (8, 1.2), (4.6, 1.2), (4.6, 0), (3.4, 0), (3.4, 1.2)], fc=CONC, ec=INK))
    _dim(ax, (1.2, 2.0), (6.8, 2.0), "beff = beff,1 + bw + beff,2", .2)
    _dim(ax, (1.2, .95), (3.4, .95), "beff,1", -.2)
    _dim(ax, (4.6, .95), (6.8, .95), "beff,2", -.2)
    _dim(ax, (3.4, -.25), (4.6, -.25), "bw", -.2)
    ax.text(.1, 1.45, "hf", va="center")
    ax.set_xlim(-.3, 8.3)
    ax.set_ylim(-.65, 2.45)
    ax.set_title("Effective flange width (EC2 5.3.2.1)")
    _bare(ax)
    plt.show()


def curtail(x, Mmax, Mmin, al, caps, title="Moment envelope, shift rule a_l and bar capacity (EC2 9.2.1.3)"):
    """caps = [(label, value kNm, x1, x2)] resistance lines (sagging +, hogging -)."""
    f, ax = plt.subplots(figsize=(8.2, 3.9))
    ax.plot(x, np.maximum(Mmax, 0), color=ORANGE, lw=1.8, label="Envelope")
    ax.plot(x, np.minimum(Mmin, 0), color=ORANGE, lw=1.8)
    up = [max(np.maximum(Mmax, 0)[(x >= q - al) & (x <= q + al)]) for q in x]
    lo = [min(np.minimum(Mmin, 0)[(x >= q - al) & (x <= q + al)]) for q in x]
    ax.plot(x, up, color=MUTED, lw=1.3, ls="--", label=f"Envelope shifted by a_l = {al * 1000:.0f} mm")
    ax.plot(x, lo, color=MUTED, lw=1.3, ls="--")
    for i, (lab, v, p, q) in enumerate(caps):
        ax.plot([p, q], [v, v], color=BLUE, lw=2)
        ax.text((p + q) / 2, v, lab, ha="center", va="bottom" if v < 0 else "top", fontsize=8)
    ax.axhline(0, color=MUTED, lw=.9)
    ax.invert_yaxis()
    ax.margins(y=.15)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("M (kN·m)")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.16), ncol=2)
    plt.show()
