"""Project brief (edit here) and the load path slab -> beam -> column -> pad.

Every number in BRIEF is a project INPUT that must come from the client, architect, code or
ground investigation. Change it here, re-run the notebooks, and the whole chain updates.
"""
from .analysis import UDL, ContinuousBeam, Span, joint_moments
from .codes import PSI, UK
from .slabs import two_way_shear

BRIEF = dict(
    ndp=UK,                 # national parameters: UK or EN (ec2/codes.py)
    bays_x=3, lx_bay=6.0,   # m, grid 1-4 (three bays each way is built into the panel types; keep lx_bay >= ly_bay)
    bays_y=3, ly_bay=5.0,   # m, grid A-D
    levels=3,               # suspended levels carried by a ground-storey column (2 floors + accessible roof)
    storey=3.5,             # m, floor to floor
    h_slab=175,             # mm
    beam=(300, 500),        # mm, b x h (both directions)
    col=(350, 350),         # mm
    finishes=1.5,           # kN/m2, finishes + ceiling + services
    qk=3.0,                 # kN/m2, category B office, EN 1991-1-1 Table 6.2 (recommended value)
    partitions=0.8,         # kN/m2, EN 1991-1-1 6.3.1.2(8), partitions 1 to 2 kN/m
    category="B",
    facade=8.0,             # kN/m, external wall on every edge beam
    fck=30, fyk=500, dg=20,
    exposure="XC1", fire=60,
    bearing=200.0,          # kN/m2, presumed gross bearing pressure from the ground investigation
    overburden=9.0,         # kN/m2, backfill + ground slab over the pad
    exposure_ground="XC2",
    RH=50, t0=28,           # %, days: internal humidity and age at loading, for creep (EC2 Annex B)
)


def area_loads():
    b = BRIEF
    return 25 * b["h_slab"] / 1000 + b["finishes"], b["qk"] + b["partitions"]


def downstand():
    b, h = BRIEF["beam"]
    return 25 * b / 1000 * (h - BRIEF["h_slab"]) / 1000


def line_loads():
    """Characteristic slab line loads per span, acting on the middle 3/4 (kN/m): {line: [(g, q), ...]}."""
    g, q = area_loads()
    lx, r = BRIEF["ly_bay"], BRIEF["lx_bay"] / BRIEF["ly_bay"]      # short span = 5 m (y), long = 6 m (x)
    corner, edge_l = two_way_shear("two adjacent edges discontinuous", r), two_way_shear("one long edge discontinuous", r)
    edge_s, inner = two_way_shear("one short edge discontinuous", r), two_way_shear("interior", r)
    c = {"B": [(corner["vx_cont"], edge_s["vx_cont"]), (edge_l["vx_cont"], inner["vx_cont"]), (corner["vx_cont"], edge_s["vx_cont"])],
         "A": [(corner["vx_disc"], 0), (edge_l["vx_disc"], 0), (corner["vx_disc"], 0)],
         "2": [(corner["vy_cont"], edge_l["vy_cont"]), (edge_s["vy_cont"], inner["vy_cont"]), (corner["vy_cont"], edge_l["vy_cont"])],
         "1": [(corner["vy_disc"], 0), (edge_s["vy_disc"], 0), (corner["vy_disc"], 0)]}
    return c, {k: [(sum(t) * g * lx, sum(t) * q * lx) for t in v] for k, v in c.items()}


def spans(line, gG=1.0, gQ=0.0, loaded=(1, 1, 1)):
    """Spans of a beam line with factored loads. `loaded` switches the variable load per span."""
    L = BRIEF["lx_bay"] if line in "AB" else BRIEF["ly_bay"]
    _, w = line_loads()
    sw = downstand() + (BRIEF["facade"] if line in ("A", "1") else 0)
    out = []
    for (g, q), on in zip(w[line], loaded):
        out.append(Span(L, [UDL(gG * g + (gQ * q if on else 0), L / 8, 7 * L / 8), UDL(gG * sw)]))
    return out


def analyse(line, gG=1.0, gQ=0.0, loaded=(1, 1, 1)):
    cb = ContinuousBeam(spans(line, gG, gQ, loaded))
    cb.moment_distribution()
    cb.diagrams()
    return cb


CASES = {"All spans": (1, 1, 1), "Spans 1 and 3": (1, 0, 1), "Span 2": (0, 1, 0)}


def design_cases(line):
    n = BRIEF["ndp"]
    return {k: analyse(line, n["gamma_G"], n["gamma_Q"], v) for k, v in CASES.items()}


def reactions(line, j):
    """Characteristic reaction (G, Q) at support j, all spans loaded."""
    g = analyse(line, 1, 0).R[j]
    return g, analyse(line, 1, 1).R[j] - g


COLUMNS = {"B2": (("B", 1), ("2", 1)), "B1": (("B", 0), ("1", 1)), "A1": (("A", 0), ("1", 0))}


def takedown(col):
    """Characteristic axial loads at the foot of the ground-storey column."""
    (l1, j1), (l2, j2) = COLUMNS[col]
    g1, q1 = reactions(l1, j1)
    g2, q2 = reactions(l2, j2)
    b, h = BRIEF["col"]
    n = BRIEF["levels"]
    sw = 25 * b * h / 1e6 * BRIEF["storey"] * n
    return dict(g1=g1, q1=q1, g2=g2, q2=q2, sw=sw, G=n * (g1 + g2) + sw, Q=n * (q1 + q2))


def flange(line, span):
    """Effective flange of a beam line, span 0/1/2 (EC2 5.3.2.1). Returns dict in mm."""
    bw, h = BRIEF["beam"]
    L = (BRIEF["lx_bay"] if line in "AB" else BRIEF["ly_bay"]) * 1e3
    clear = ((BRIEF["ly_bay"] if line in "AB" else BRIEF["lx_bay"]) * 1e3 - bw) / 2
    l0 = (0.7 if span == 1 else 0.85) * L
    one = min(0.2 * clear + 0.1 * l0, 0.2 * l0, clear)
    n = 1 if line in "A1" else 2
    return dict(L=L, l0=l0, bi=clear, beffi=one, sides=n, beff=bw + n * one)


def flanged_I(beff, bw, h, hf):
    """Gross second moment of area of a T/L section (mm4)."""
    a1, a2 = (beff - bw) * hf, bw * h
    y = (a1 * hf / 2 + a2 * h / 2) / (a1 + a2)
    return (beff - bw) * hf**3 / 12 + a1 * (y - hf / 2) ** 2 + bw * h**3 / 12 + a2 * (h / 2 - y) ** 2, y


def column_joint(line, j, gG=None, gQ=None):
    """Column moments by one-joint moment distribution (BS 8110-1 3.2.1.2.5):
    remote ends fixed, beams at half stiffness; one span fully loaded, the other permanent load only.
    Beam stiffness: gross flanged section, span value of b_eff (EC2 5.3.2.1(4), 5.4(2))."""
    n = BRIEF["ndp"]
    gG, gQ = gG or n["gamma_G"], gQ or n["gamma_Q"]
    b, h = BRIEF["beam"]
    cb_, ch = BRIEF["col"]
    kc = cb_ * ch**3 / 12 / (BRIEF["storey"] * 1e3) / 1e3                                    # 10^3 mm3
    idx = [0] if j == 0 else [j - 1, j]
    kb = []
    for i in idx:
        f = flange(line, i)
        kb.append(flanged_I(f["beff"], b, h, BRIEF["h_slab"])[0] / f["L"] / 1e3)
    full, dead = spans(line, gG, gQ), spans(line, gG)
    if j == 0:
        f1, f2 = full[0].fem()[0], 0.0
    else:
        opts = [(full[j - 1].fem()[1], dead[j].fem()[0]), (dead[j - 1].fem()[1], full[j].fem()[0])]
        f1, f2 = max(opts, key=lambda o: abs(o[0] - o[1]))
    dM = abs(f1 - f2)
    m = joint_moments(dM, {"upper column": kc, "lower column": kc, **{f"beam {i + 1} (half)": k / 2 for i, k in enumerate(kb)}})
    return dict(kb=kb, kc=kc, f1=f1, f2=f2, dM=dM, M=m["lower column"], dist=m)
