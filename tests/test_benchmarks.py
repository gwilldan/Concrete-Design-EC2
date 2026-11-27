"""Checks against published results. Run:  python -m pytest -q"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ec2 import columns, design, foundations, slabs  # noqa: E402
from ec2.analysis import UDL, ContinuousBeam, DeterminateBeam, Moment, Point, Span, UVL  # noqa: E402
from ec2.codes import EN, UK  # noqa: E402
from ec2.report import Sheet, convert  # noqa: E402


def sheet(fck=30, ndp=UK):
    s = Sheet("test")
    design.materials(s, fck, 500, ndp, show=False)
    return s


# ---- analysis : NPTEL (IIT Kharagpur) Structural Analysis II
def test_nptel_12_1():
    b = ContinuousBeam([Span(10, [UDL(1), Point(10, 5)]), Span(10, [UDL(1)])], right=-15)
    assert b.three_moment()[1] == pytest.approx(-18.125)
    b.diagrams()
    assert b.Vends[0] == pytest.approx((8.1875, -11.8125))
    # NPTEL prints R_C = 4.7125; 5.3125 + R_C must equal 10, so 4.6875 is the correct value
    assert b.Vends[1] == pytest.approx((5.3125, -4.6875))


def test_nptel_12_1_overhang_span():
    # NPTEL Fig. 12.4a: overhang CD = 3 m with 5 kN at D, so M_C = -5 x 3 = -15 and R_C gains the 5 kN
    oh = Span(3, [Point(5, 3)])
    b = ContinuousBeam([Span(10, [UDL(1), Point(10, 5)]), Span(10, [UDL(1)])], overhang_right=oh)
    assert b.three_moment() == pytest.approx([0, -18.125, -15])
    assert b.moment_distribution() == pytest.approx([0, -18.125, -15], abs=1e-3)
    b.diagrams()
    assert b.R == pytest.approx([8.1875, 17.125, 9.6875])
    assert sum(b.R) == pytest.approx(10 + 10 + 10 + 5)
    x, V, M = b.oh_diagrams[1]
    assert (x[0], x[-1]) == pytest.approx((20, 23))
    assert (V.min(), V.max()) == pytest.approx((5, 5))
    assert (M[0], M[-1]) == pytest.approx((-15, 0))
    # the mirror image, with the overhang on the left, gives the mirrored answer
    m = ContinuousBeam([Span(10, [UDL(1)]), Span(10, [UDL(1), Point(10, 5)])], overhang_left=Span(3, [Point(5, 0)]))
    assert m.three_moment() == pytest.approx([-15, -18.125, 0])
    m.diagrams()
    assert m.R == pytest.approx([9.6875, 17.125, 8.1875])
    assert m.oh_diagrams[0][2][-1] == pytest.approx(-15)
    with pytest.raises(ValueError):
        ContinuousBeam([Span(10, [UDL(1)])], right=-15, overhang_right=oh)


def test_overhang_udl_by_statics():
    # 2 m overhang with 10 kN/m: M = -w a^2 / 2 = -20, and the overhang adds w a = 20 kN to its support
    b = ContinuousBeam([Span(6, [UDL(10)]), Span(6, [UDL(10)])], overhang_right=Span(2, [UDL(10)]))
    ref = ContinuousBeam([Span(6, [UDL(10)]), Span(6, [UDL(10)])], right=-20, overhang_right=20)
    assert b.three_moment() == pytest.approx(ref.three_moment())
    assert b.right == pytest.approx(-20)
    b.diagrams(), ref.diagrams()
    assert b.R == pytest.approx(ref.R)
    assert sum(b.R) == pytest.approx(10 * 14)


def test_nptel_12_2_equations():
    # NPTEL equations (4),(5): 20 MA + 10 MB = -500 ; 5 MA + 20 MB = -312.5. The printed answer
    # (-37.5, -6.25) does not satisfy them; the solution is below and moment distribution agrees.
    exact = np.linalg.solve([[20, 10], [5, 20]], [-500, -312.5])
    b = ContinuousBeam([Span(10, [UDL(2)], 2), Span(5, [UDL(2)], 1)], left="fixed")
    assert b.three_moment()[:2] == pytest.approx(exact)
    assert b.moment_distribution()[:2] == pytest.approx(exact, abs=1e-3)


def test_nptel_18_2_and_18_3():
    b = ContinuousBeam([Span(3, [UDL(2)]), Span(4, [Point(10, 2)])], left="fixed")
    assert b.moment_distribution()[1] == pytest.approx(-5.34, abs=0.005)
    assert b.DF[1:3] == pytest.approx([0.64, 0.36])
    b = ContinuousBeam([Span(8, [UDL(3)]), Span(6, [Point(10, 3)], 2)], left="fixed", right=-15)
    assert -b.moment_distribution() == pytest.approx([18.04, 11.92, 15.0], abs=0.01)


@pytest.mark.parametrize("left", ["pin", "fixed", -12.0])
@pytest.mark.parametrize("right", ["pin", "fixed", -7.0])
@pytest.mark.parametrize("n", [1, 2, 3, 5])
def test_methods_agree(left, right, n):
    sp = [Span(4 + i, [UDL(10 + i, 0.5, 3), Point(20, 1.5 + 0.3 * i)], 1 + 0.4 * i) for i in range(n)]
    b = ContinuousBeam(sp, left, right)
    a = b.three_moment().copy()
    assert b.moment_distribution(tol=1e-9) == pytest.approx(a, abs=1e-6)
    b.diagrams()
    assert sum(b.R) == pytest.approx(sum((10 + i) * 2.5 + 20 for i in range(n)), rel=1e-6)


def test_determinate():
    b = DeterminateBeam(6, [UDL(10)], supports=(0, 6))
    assert b.M.max() == pytest.approx(45)
    b = DeterminateBeam(4, [UDL(5), Point(8, 4 - 1e-9)], fixed="left")
    assert b.MA == pytest.approx(-72, rel=1e-6) and abs(b.M[-1]) < 1e-6
    b = DeterminateBeam(6, [UVL(0, 12, 0, 6)], supports=(0, 6))
    assert b.RA == pytest.approx(12) and b.M.max() == pytest.approx(12 * 36 / (9 * math.sqrt(3)), rel=1e-4)
    b = DeterminateBeam(8, [UDL(10)], supports=(0, 6))
    assert b.M.min() == pytest.approx(-20, rel=1e-4) and abs(b.M[-1]) < 1e-6
    b = DeterminateBeam(4, [Moment(20, 2)], supports=(0, 4))
    assert b.RA == pytest.approx(-5) and b.M.max() == pytest.approx(10, rel=1e-3)


# ---- units
def test_stress_units():
    assert convert(17, "N/mm²", "MPa") == pytest.approx(17)
    assert convert(1, "N/mm²", "Pa") == pytest.approx(1e6)
    assert convert(200, "kN/m²", "Pa") == pytest.approx(200000)
    assert convert(200, "kN/m²", "MPa") == pytest.approx(0.2)
    assert convert(33, "kN/mm²", "MPa") == pytest.approx(33000)
    # force / area from first principles: 50 kN on 100 mm x 100 mm
    assert 50e3 / 100**2 == pytest.approx(convert(50 / 0.1**2, "kN/m²", "N/mm²"))


# ---- code tables
def test_table_3_1():
    for fck, fctm in [(20, 2.2), (25, 2.6), (30, 2.9), (35, 3.2), (40, 3.5), (50, 4.1)]:
        assert sheet(fck)["f_ctm"] == pytest.approx(fctm, abs=0.06)


@pytest.mark.parametrize("panel", list(slabs.EDGES))
def test_two_way_table_matches_its_equations(panel):
    n, p, ny, py = slabs.BETA_S[panel]
    for r, pos in zip(slabs.RATIO, p):
        d = slabs.derive(panel, r)
        assert pos == pytest.approx(d[1], abs=0.0016), (panel, r)
        assert py == pytest.approx(d[3], abs=0.0011)
        if ny:
            assert ny == pytest.approx(d[2], abs=0.0016), (panel, r)
        if n:
            assert n[slabs.RATIO.index(r)] == pytest.approx(d[0], abs=0.0021), (panel, r)


def test_simply_supported_equations():
    for r, ax, ay in zip(slabs.RATIO, slabs.ALPHA_SX, slabs.ALPHA_SY):
        assert ax == pytest.approx(r**4 / (8 * (1 + r**4)), abs=0.0011)
        assert ay == pytest.approx(r**2 / (8 * (1 + r**4)), abs=0.0011)


# ---- JRC EUR 26566 (2014) worked examples
def test_jrc_punching():
    s = sheet(25, EN)
    design.shear_resistance(s, 1000, 164, 0.0083 * 164000)
    assert s["V_Rd_c"] / 164 == pytest.approx(0.66, abs=0.005)
    assert s["v_min"] == pytest.approx(0.49, abs=0.01)
    u1 = 4 * 500 + 2 * math.pi * 2 * 164
    assert u1 == pytest.approx(4061, abs=1) and 1.15 * 705000 / (u1 * 164) == pytest.approx(1.22, abs=0.005)


def test_jrc_slenderness():
    s = sheet(30, EN)
    columns.slenderness(s, 4.0, 500, 4384, 500, k1=0.53, k2=0.53)
    # JRC prints lambda = 22.5, but its own expression 3.46*3.1/0.5 equals 21.45
    assert s["l0"] == pytest.approx(3.1, abs=0.05) and s["lam"] == pytest.approx(3.46 * 3.1 / 0.5, rel=0.01)
    assert s["n"] == pytest.approx(0.88, abs=0.005) and s["lam_lim"] == pytest.approx(11.5, abs=0.05)


def test_jrc_deflection():
    s = sheet(25, EN)
    design.deflection(s, 6000, 144, 1000, 0.0044 * 144000, 0.0044 * 144000, "end span")
    assert s["N_basic"] == pytest.approx(26.4, abs=0.15)


def test_jrc_anchorage():
    for phi, l in [(8, 226), (10, 283), (12, 339), (14, 408), (16, 500)]:
        assert design.anchorage(sheet(25, EN), phi, cd=40) == pytest.approx(l, rel=0.01)
    for phi, l in [(8, 323), (10, 404), (16, 646)]:
        assert design.anchorage(sheet(25, EN), phi, compression=True) == pytest.approx(l, rel=0.01)


def test_jrc_footing_tension():
    # sigma' = 1418 kPa, b = 2.0 m, a = 0.5 m, zi = 0.662 m -> Fs,max = 1457.9 kN
    b, a, zi = 2.0, 0.5, 0.662
    x = b / 2 - 0.35 * a
    assert 1418 * b * x * (b / 2 - 0.35 * a - x / 2) / zi == pytest.approx(1457.9, rel=0.002)


# ---- NA Table NA.5 basic ratios (C30)
@pytest.mark.parametrize("system,hi,lo", [("simply supported", 14, 20), ("end span", 18, 26), ("interior span", 20, 30), ("cantilever", 6, 8)])
def test_na5(system, hi, lo):
    for rho, n in ((0.015, hi), (0.005, lo)):
        s = sheet(30, UK)
        design.deflection(s, 6000, 500, 1000, rho * 5e5, rho * 5e5, system)
        assert s["N_basic"] == pytest.approx(n, abs=1.0)


# ---- mechanics: design then verify by independent equilibrium
@pytest.mark.parametrize("M", [60, 120, 200, 260, 330])
def test_flexure_equilibrium(M):
    s = sheet()
    b, d, d2 = 300, 440, 50
    As, A2 = design.flexure(s, M, b, d, d2=d2, limits=False)
    fcd, fyd = s["f_cd"], s["f_yd"]
    x = np.linspace(1, 0.6 * d, 400001)
    f2 = np.minimum(200000 * 0.0035 * (x - d2) / x, fyd)
    res = np.abs(fcd * b * 0.8 * x + A2 * f2 - As * fyd)
    x = x[res.argmin()]
    f2 = min(200000 * 0.0035 * (x - d2) / x, fyd) if A2 else 0
    MR = (fcd * b * 0.8 * x * (d - 0.4 * x) + A2 * f2 * (d - d2)) / 1e6
    assert MR >= M * 0.999 and MR <= M * 1.06


def test_K_limit_is_0167():
    for ndp in (UK,):
        s = sheet(30, ndp)
        design.k_limit(s)
        assert s["K_lim"] == pytest.approx(0.167, abs=0.001)


def test_interaction_end_points():
    L = columns.perimeter_layers(2, 2, 20, 300, 300, 50)
    c = columns.interaction(300, 300, L, 17.0, 434.8)
    As = 4 * math.pi * 100
    assert c[-1, 0] == pytest.approx((17 * (90000 - As) + 400 * As) / 1e3)
    assert c[-1, 1] == pytest.approx(0, abs=1e-6)
    assert c[0, 0] == pytest.approx(-As * 434.8 / 1e3)
    # N = 0 reproduces pure bending of the same section
    As2 = As / 2
    x = np.linspace(5, 150, 200001)
    f2 = np.clip(200000 * 0.0035 * (x - 50) / x, -434.8, 434.8) - 17.0 * (50 < 0.8 * x)
    i = np.abs(17 * 300 * 0.8 * x + As2 * f2 - As2 * 434.8).argmin()
    M = (17 * 300 * 0.8 * x[i] * (150 - 0.4 * x[i]) + As2 * f2[i] * 100 + As2 * 434.8 * 100) / 1e6
    assert columns.MRd(c, 0.0) == pytest.approx(M, rel=0.01)


def test_punching_scan_concentric():
    r = foundations.punching_scan(1400, 0, 2400, 2400, 350, 350, 580, 0.002, 30)
    a, u, V, v, vr, _ = r[0]
    assert u == pytest.approx(4 * 350 + 2 * math.pi * a)
    assert V == pytest.approx(1400 * (1 - (350**2 + 4 * a * 350 + math.pi * a**2) / 2400**2))


def test_W_matches_code_at_2d():
    d, c1, c2 = 500, 400, 300
    a = 2 * d
    assert c1**2 / 2 + c1 * c2 + 2 * c2 * a + 4 * a**2 + math.pi * a * c1 == pytest.approx(c1**2 / 2 + c1 * c2 + 4 * c2 * d + 16 * d**2 + 2 * math.pi * d * c1)
