"""EC2 design procedures. Each one prints its full working to a Sheet `s` and returns the key result.

Units inside a sheet: N, mm, N/mm² for resistance formulas; kN, kN·m, kN/m² for actions.
The sheet prints the MPa or Pa value beside every stress and pressure (report.py).
"""
import math

from .codes import (BARS, COVER_DUR, CRACK_SPACING, DEFL_K, FIRE_BEAM_CONT, FIRE_BEAM_SS,
                    FIRE_COL, FIRE_COL_B, FIRE_SLAB, UK)


def area(phi, n=1):
    return n * math.pi * phi**2 / 4


def need(ok, msg):
    if not ok:
        raise ValueError(msg)


# ---------------------------------------------------------------- materials, loads, cover
def materials(s, fck=30, fyk=500, ndp=UK, show=True):
    need(12 <= fck <= 50, "These procedures cover fck <= 50 N/mm² (50 MPa) (lambda = 0.8, eta = 1.0, eps_cu2 = 3.5 per mille).")
    need(400 <= fyk <= 600, "EC2 3.2.2(3)P: fyk = 400 to 600 N/mm² (MPa)")
    s.ndp = ndp
    s.let("f_ck", fck, "N/mm²", "Concrete cylinder strength (project input)", "EC2 Table 3.1")
    s.let("f_yk", fyk, "N/mm²", "Steel yield strength (project input)", "EC2 3.2.2(3)")
    s.let("gamma_c", ndp["gamma_c"], "", "Partial factor, concrete", "EC2 2.4.2.4, Table 2.1N")
    s.let("gamma_s", ndp["gamma_s"], "", "Partial factor, reinforcement", "EC2 2.4.2.4, Table 2.1N")
    s.let("alpha_cc", ndp["alpha_cc"], "", f"Flexure and axial load ({ndp['name']})", "EC2 3.1.6(1), NA")
    s.calc("f_cd", "alpha_cc*f_ck/gamma_c", "N/mm²", "EC2 Exp. (3.15)")
    s.calc("f_yd", "f_yk/gamma_s", "N/mm²", "EC2 3.2.7, Fig. 3.8")
    s.calc("f_ctm", "0.30*f_ck**(2/3)", "N/mm²", "EC2 Table 3.1")
    s.let("E_s", 200000, "N/mm²", "Steel modulus", "EC2 3.2.7(4)")
    if show:
        s.show("Materials")


def floor_actions(s, h, finishes, qk, partitions=0.0, cat="B"):
    """Area loads. finishes, qk, partitions in kN/m2."""
    s.let("h", h, "mm", "Slab thickness")
    s.let("gamma_rc", 25, "kN/m³", "Reinforced concrete, 24 + 1", "EN 1991-1-1 Table A.1")
    s.calc("g_k_self", "gamma_rc*h/1000", "kN/m²", "EN 1991-1-1 5.2")
    s.let("g_k_fin", finishes, "kN/m²", "Finishes and services (project input)")
    s.calc("g_k", "g_k_self + g_k_fin", "kN/m²")
    s.let("q_k_1", qk, "kN/m²", f"Imposed load, category {cat}", "EN 1991-1-1 Table 6.2")
    s.let("q_k_2", partitions, "kN/m²", "Movable partitions (1.0 to 2.0 kN/m wall)", "EN 1991-1-1 6.3.1.2(8)")
    s.calc("q_k", "q_k_1 + q_k_2", "kN/m²")
    s.let("gamma_G", s.ndp["gamma_G"], "", "", "EN 1990 Table A1.2(B)")
    s.let("gamma_Q", s.ndp["gamma_Q"], "", "", "EN 1990 Table A1.2(B)")
    s.calc("n_Ed", "gamma_G*g_k + gamma_Q*q_k", "kN/m²", "EN 1990 Exp. (6.10)")


def cover(s, exposure, phi, phi_link=0, ground=None, c_provided=None, show=True):
    """Nominal cover to the outermost bar considered. ground: None | 'blinding' | 'soil'."""
    s.let("phi", phi, "mm", "Main bar diameter")
    s.let("c_min_dur", COVER_DUR[exposure], "mm", f"Exposure {exposure}, class S4", "EC2 Table 4.1, 4.4N")
    s.let("Delta_c_dev", 10, "mm", "Allowance for deviation", "EC2 4.4.1.3(1)")
    if phi_link:
        s.let("phi_link", phi_link, "mm", "Link diameter")
        s.calc("c_nom_link", "max(phi_link, c_min_dur, 10) + Delta_c_dev", "mm", "EC2 Exp. (4.1), (4.2)", "To the link")
        s.calc("c_nom_bar", "max(phi, c_min_dur, 10) + Delta_c_dev - phi_link", "mm", "EC2 Exp. (4.1), (4.2)", "To the link, so that the main bar complies")
        s.calc("c_req", "max(c_nom_link, c_nom_bar)", "mm")
    else:
        s.calc("c_req", "max(phi, c_min_dur, 10) + Delta_c_dev", "mm", "EC2 Exp. (4.1), (4.2)")
    if ground:
        k = {"blinding": 40, "soil": 75}[ground]
        s.let("k_ground", k, "mm", f"Cast against {'prepared ground / blinding' if ground == 'blinding' else 'soil'}", "EC2 4.4.1.3(4)")
        s.calc("c_req", "max(c_req, k_ground)", "mm", "EC2 4.4.1.3(4)")
    c = c_provided if c_provided else math.ceil(s["c_req"] / 5) * 5
    s.let("c_nom", c, "mm", "Cover adopted")
    s.check("c_nom", ">=", "c_req", "nominal cover", "EC2 4.4.1")
    s.note("UK projects: confirm concrete quality and cover against BS 8500-1 Tables A.4/A.5 as the UK NA requires.", "NA to EC2, 4.4.1.2(5)")
    if show:
        s.show("Durability – nominal cover")
    return c


def fire_slab(s, R, h, a, two_way=False, ratio=1.0):
    hs, a1, a2, a3 = FIRE_SLAB[R]
    req = a1 if not two_way else (a2 if ratio <= 1.5 else a3)
    s.let("a_prov", a, "mm", "Axis distance to the lower bar")
    s.let("a_req", req, "mm", f"REI {R}", "EN 1992-1-2 Table 5.8")
    s.let("h_s_min", hs, "mm", f"REI {R}", "EN 1992-1-2 Table 5.8")
    s.check("h", ">=", "h_s_min", "fire – slab thickness", "EN 1992-1-2 5.7")
    s.check("a_prov", ">=", "a_req", "fire – axis distance", "EN 1992-1-2 5.7")
    s.show("Fire resistance")


def _fire_row(rows, b):
    ok = [r for r in rows if r[0] <= b]
    need(ok, "Member narrower than the minimum width tabulated for this fire rating")
    return ok[-1]


def fire_beam(s, R, b, a, a_side, continuous=True):
    rows = (FIRE_BEAM_CONT if continuous else FIRE_BEAM_SS)[R]
    bm, ar = _fire_row(rows, b)
    s.let("a_prov", a, "mm", "Axis distance, soffit")
    s.let("a_sd_prov", a_side, "mm", "Axis distance, side")
    tb = "5.6" if continuous else "5.5"
    s.let("a_req", ar, "mm", f"R {R}, tabulated width {bm} mm", f"EN 1992-1-2 Table {tb}")
    lim = rows[1][0] if continuous else rows[2][0]
    s.let("a_sd_req", ar + (0 if b > lim else 10), "mm", f"Corner bars ({'no' if b > lim else '+10 mm'} increase; width limit {lim} mm)", f"EN 1992-1-2 Table {tb}")
    s.check("a_prov", ">=", "a_req", "fire – axis distance", f"EN 1992-1-2 Table {tb}")
    s.check("a_sd_prov", ">=", "a_sd_req", "fire – side axis distance", f"EN 1992-1-2 Table {tb}")
    s.show("Fire resistance")


def fire_column(s, R, bmin, a, nbars, l0_fi, e, h, As_ratio):
    rows = [r for r in FIRE_COL[R] if r[0] <= bmin and (not r[2] or nbars >= 8)]
    need(rows, "Column too narrow for tabulated method A")
    s.let("a_prov", a, "mm", "Axis distance")
    s.let("a_req", rows[-1][1], "mm", f"R {R}, μ_fi = 0.7 (safe simplification), tabulated width {rows[-1][0]} mm", "EN 1992-1-2 Table 5.2a, 2.4.2(3) Note 2")
    s.check("a_prov", ">=", "a_req", "fire – axis distance", "EN 1992-1-2 5.3.2")
    s.let("l_0_fi", l0_fi, "m", "Effective length in fire", "EN 1992-1-2 5.3.2(2) Note 2")
    s.check("l_0_fi", "<=", 3.0, "fire – method A effective length limit (m)", "EN 1992-1-2 5.3.2(2)")
    s.let("e_fi", e, "mm", "First-order eccentricity", "EN 1992-1-2 5.3.2(2) Note 3")
    s.calc("e_max", "0.15*h", "mm", "EN 1992-1-2 5.3.2(2) Note 1")
    s.check("e_fi", "<=", "e_max", "fire – method A eccentricity limit", "EN 1992-1-2 5.3.2(2)")
    s.let("rho_s", As_ratio, "", "As / Ac")
    s.check("rho_s", "<=", 0.04, "fire – method A steel limit", "EN 1992-1-2 5.3.2(2)")
    s.show("Fire resistance (tabulated method A)")


def fire_column_b(s, R, b, a, N, As, Ac, l0_fi, i, e):
    """Method B. N in kN, e in mm."""
    s.let("N_Ed", N, "kN")
    s.calc("N_0_fi", "0.7*N_Ed", "kN", "EN 1992-1-2 5.3.3(3) Note 1")
    s.let("A_c", Ac, "mm²")
    s.let("A_s", As, "mm²")
    s.calc("n_fi", "N_0_fi*1000/(0.7*(A_c*f_cd + A_s*f_yd))", "", "EN 1992-1-2 Exp. (5.8a)")
    s.calc("omega", "A_s*f_yd/(A_c*f_cd)", "", "EN 1992-1-2 5.3.3(2)")
    s.check("omega", ">=", 0.1, "fire – tabulated row ω = 0.1 is conservative", "EN 1992-1-2 Table 5.2b")
    s.let("e_fi", e, "mm", "First-order eccentricity")
    s.let("e_max", min(0.25 * b, 100), "mm", "min(0.25b, 100)", "EN 1992-1-2 5.3.3(2)")
    s.check("e_fi", "<=", "e_max", "fire – method B eccentricity limit", "EN 1992-1-2 5.3.3(2)")
    s.let("l_0_fi", l0_fi, "m", "0.5 × storey height", "EN 1992-1-2 5.3.3(3) Note 2")
    s.let("i", i, "mm")
    s.calc("lam_fi", "l_0_fi*1000/i", "", "EN 1992-1-2 Exp. (5.8c)")
    s.check("lam_fi", "<=", 30.0, "fire – method B slenderness limit", "EN 1992-1-2 5.3.3(2)")
    col = next((k for k in FIRE_COL_B[R] if s["n_fi"] <= k + 1e-9), None)
    need(col, "n exceeds 0.7: outside Table 5.2b")
    rows = [r for r in FIRE_COL_B[R][col] if r[0] <= b]
    need(rows, "Column too narrow for tabulated method B")
    s.let("a_req", rows[-1][1], "mm", f"R {R}, column n = {col}, tabulated width {rows[-1][0]} mm", "EN 1992-1-2 Table 5.2b")
    s.let("a_prov", a, "mm", "Axis distance")
    s.check("a_prov", ">=", "a_req", "fire – axis distance", "EN 1992-1-2 5.3.3")
    s.show("Fire resistance (tabulated method B)")


def flange_shear(s, M, beff, beffi, hf, dx, z, As_trans, As_bend):
    """Web-flange longitudinal shear, compression flange (EC2 6.2.4). dx in mm, M kN.m = moment change over dx."""
    s.let("Delta_M", M, "kN·m", "Change of moment over Δx")
    s.let("Delta_x", dx, "mm", "Half the distance between M = 0 and M_max", "EC2 6.2.4(3)")
    s.let("z", z, "mm")
    s.let("b_eff", beff, "mm")
    s.let("b_eff_1", beffi, "mm", "One flange outstand")
    s.let("h_f", hf, "mm")
    s.calc("Delta_F_d", "Delta_M*1000/z*b_eff_1/b_eff", "kN", "EC2 6.2.4(3)", "Force change in one outstand")
    s.calc("v_Ed_f", "Delta_F_d*1000/(h_f*Delta_x)", "N/mm²", "EC2 Exp. (6.20)")
    s.calc("f_ctd", "0.7*f_ctm/gamma_c", "N/mm²", "EC2 Exp. (3.16)")
    s.calc("v_lim", "0.4*f_ctd", "N/mm²", "EC2 6.2.4(6), NA")
    if s["v_Ed_f"] <= s["v_lim"]:
        s.check("v_Ed_f", "<=", "v_lim", "flange shear: no extra transverse steel", "EC2 6.2.4(6)")
        return
    s.let("cot_theta", 2.0, "", "Compression flange", "EC2 6.2.4(4), NA")
    s.calc("nu", "0.6*(1 - f_ck/250)", "", "EC2 Exp. (6.6N)")
    s.calc("v_max", "nu*f_cd*cot_theta/(1 + cot_theta**2)", "N/mm²", "EC2 Exp. (6.22)", "ν f_cd sin θ cos θ (with α_cc = 0.85, conservative)")
    s.check("v_Ed_f", "<=", "v_max", "flange struts", "EC2 6.2.4(4)")
    s.calc("A_sf", "v_Ed_f*h_f/(cot_theta*f_yd)*1000", "mm²/m", "EC2 Exp. (6.21)")
    s.let("A_bend", As_bend, "mm²/m", "Slab bending steel at the beam")
    s.calc("A_comb", "max(A_sf, 0.5*A_sf + A_bend)", "mm²/m", "EC2 6.2.4(5)")
    s.let("A_trans", As_trans, "mm²/m", "Transverse slab steel crossing the junction (top + bottom)")
    s.check("A_trans", ">=", "A_comb", "flange transverse steel", "EC2 6.2.4(4), (5)")


# ---------------------------------------------------------------- flexure
def k_limit(s, delta=1.0):
    """K' from the neutral-axis limit. Uses the tighter of the NA redistribution limit and x/d = 0.45."""
    s.let("delta", delta, "", "Redistributed / elastic moment", "EC2 5.5(4)")
    s.let("k_1", s.ndp["k1"], "", s.ndp["name"], "EC2 5.5(4), NA")
    s.let("k_2", s.ndp["k2"], "", s.ndp["name"], "EC2 5.5(4), NA")
    s.let("lam", 0.8, "", "Stress-block depth factor, fck ≤ 50", "EC2 Exp. (3.19)")
    s.let("eta", 1.0, "", "Stress-block strength factor, fck ≤ 50", "EC2 Exp. (3.21)")
    s.calc("xi_lim", "min((delta - k_1)/k_2, 0.45)", "", "EC2 5.5(4), 5.6.3(2)", "x/d limit. The 0.45 ceiling is the EC2 5.6.3(2) ductility value, kept for every section")
    s.calc("K_lim", "eta*f_cd/f_ck*lam*xi_lim*(1 - lam*xi_lim/2)", "", "EC2 3.1.7(3) (Notebook 2.2)")


def flexure(s, M, b, d, d2=None, h=None, bt=None, delta=1.0, label="", limits=True):
    """Rectangular section. M in kN.m. Returns (As_req, As2_req)."""
    k_limit(s, delta)
    s.let("M_Ed", abs(M), "kN·m", f"Design moment {label}".strip())
    s.let("b", b, "mm")
    s.let("d", d, "mm", "Effective depth")
    s.calc("K", "M_Ed*1e6/(b*d**2*f_ck)", "", "EC2 3.1.7(3), 6.1 (Notebook 2.2)")
    A2 = 0.0
    if s["K"] <= s["K_lim"]:
        s.check("K", "<=", "K_lim", f"singly reinforced {label}".strip(), "EC2 5.5(4)")
        s.calc("z", "min(d/2*(1 + sqrt(1 - 2*K*f_ck/(eta*f_cd))), 0.95*d)", "mm", "EC2 3.1.7(3) (Notebook 2.2); 0.95d: BS 8110-1 3.4.4.4", "Lever arm")
        s.calc("x", "2*(d - z)/lam", "mm", "", "Neutral axis depth")
        s.calc("A_s_req", "M_Ed*1e6/(f_yd*z)", "mm²", "EC2 6.1")
    else:
        need(d2 is not None, "K > K': compression steel needed, supply d2 or a deeper section")
        s.note("K > K′ so compression reinforcement is required.", "EC2 6.1")
        s.let("d_2", d2, "mm", "Depth to compression steel")
        s.calc("x", "xi_lim*d", "mm")
        s.calc("z", "d - lam*x/2", "mm")
        s.calc("eps_s2", "0.0035*(x - d_2)/x", "", "EC2 6.1(2)P, Table 3.1", "Compression steel strain")
        s.calc("f_s2", "min(E_s*eps_s2, f_yd)", "N/mm²", "EC2 Fig. 3.8")
        s.calc("A_s2_req", "(K - K_lim)*f_ck*b*d**2/(f_s2*(d - d_2))", "mm²", "EC2 6.1 (Notebook 2.2)")
        s.calc("A_s_req", "K_lim*f_ck*b*d**2/(f_yd*z) + A_s2_req*f_s2/f_yd", "mm²", "EC2 6.1 (Notebook 2.2)")
        A2 = s["A_s2_req"]
    s["A_s_ult"] = s["A_s_req"]
    if limits:
        min_steel(s, bt or b, d)
    return s["A_s_ult"], A2


def flexure_flanged(s, M, beff, bw, hf, d, delta=1.0, label=""):
    """T/L section, flange in compression."""
    s.let("eta", 1.0, "", "", "EC2 Exp. (3.21)")
    s.let("M_Ed", abs(M), "kN·m", f"Design moment {label}".strip())
    s.let("b_eff", beff, "mm", "Effective flange width", "EC2 5.3.2.1")
    s.let("h_f", hf, "mm", "Flange thickness")
    s.let("d", d, "mm")
    s.calc("M_Rd_f", "eta*f_cd*b_eff*h_f*(d - h_f/2)/1e6", "kN·m", "EC2 3.1.7(3)", "Moment capacity with the stress block filling the flange")
    if s["M_Ed"] <= s["M_Rd_f"]:
        s.check("M_Ed", "<=", "M_Rd_f", f"stress block within flange {label}".strip(), "EC2 3.1.7(3)")
        return flexure(s, M, beff, d, delta=delta, label=label, bt=bw)
    s.note("Stress block extends into the web: split into flange outstands + web (equilibrium of the EC2 stress block).", "EC2 3.1.7(3)")
    k_limit(s, delta)
    s.let("b_w", bw, "mm")
    s.calc("F_f", "eta*f_cd*(b_eff - b_w)*h_f/1e3", "kN")
    s.calc("M_f", "F_f*(d - h_f/2)/1e3", "kN·m")
    s.calc("K", "(M_Ed - M_f)*1e6/(b_w*d**2*f_ck)")
    need(s["K"] <= s["K_lim"], "Flanged section needs compression steel: increase the depth")
    s.check("K", "<=", "K_lim", "web singly reinforced", "EC2 5.5(4)")
    s.calc("z", "min(d/2*(1 + sqrt(1 - 2*K*f_ck/(eta*f_cd))), 0.95*d)", "mm")
    s.calc("A_s_req", "F_f*1e3/f_yd + (M_Ed - M_f)*1e6/(f_yd*z)", "mm²")
    s["A_s_ult"] = s["A_s_req"]
    min_steel(s, bw, d)
    return s["A_s_ult"], 0.0


def min_steel(s, bt, d):
    s.let("b_t", bt, "mm", "Mean width of the tension zone")
    s.calc("A_s_min", "max(0.26*f_ctm/f_yk*b_t*d, 0.0013*b_t*d)", "mm²", "EC2 Exp. (9.1N)")
    s.calc("A_s_req", "max(A_s_req, A_s_min)", "mm²", "EC2 9.2.1.1(1)", "Area to provide")


def slab_bars(s, phi, spacing, h, main=True, peak=True, label=""):
    """Check a chosen bar/spacing per metre width."""
    s.let("phi", phi, "mm", "Bar diameter")
    s.let("s_prov", spacing, "mm", "Spacing")
    s.calc("A_s_prov", "pi*phi**2/4*1000/s_prov", "mm²/m")
    s.check("A_s_prov", ">=", "A_s_req", f"area provided {label}".strip(), "EC2 6.1, 9.3.1.1")
    if main:
        lim = min(2 * h, 250) if peak else min(3 * h, 400)
    else:
        lim = min(3 * h, 400) if peak else min(3.5 * h, 450)
    s.let("s_max", lim, "mm", ("Principal" if main else "Secondary") + (" bars, zone of maximum moment" if peak else " bars"), "EC2 9.3.1.1(3)")
    s.check("s_prov", "<=", "s_max", f"maximum spacing {label}".strip(), "EC2 9.3.1.1(3)")
    s.calc("A_s_max", "0.04*1000*h", "mm²/m", "EC2 9.2.1.1(3)") if "h" in s.v else None
    if "A_s_max" in s.v:
        s.check("A_s_prov", "<=", "A_s_max", f"maximum steel {label}".strip(), "EC2 9.2.1.1(3)")
    s.provide(f"H{phi} @ {spacing} mm {label} ({area(phi) * 1000 / spacing:.0f} mm²/m)".replace("  ", " "))
    return s["A_s_prov"]


def pick_slab(As, h, main=True, peak=True, phis=(10, 12, 16), step=25):
    """Suggest the lightest H-bar/spacing (spacings 100 to the code maximum) that satisfies As."""
    lim = (min(2 * h, 250) if peak else min(3 * h, 400)) if main else (min(3 * h, 400) if peak else min(3.5 * h, 450))
    best = None
    for p in phis:
        for sp in range(100, int(lim) + 1, step):
            a = area(p) * 1000 / sp
            if a >= As and (best is None or a < best[2]):
                best = (p, sp, a)
    need(best, "No bar/spacing combination found")
    return best[:2]


def beam_bars(s, n, phi, bw, cnom, link, dg=20, label="", need_area="A_s_req", layers=1):
    s.let("n_bars", n, "", "Number of bars")
    s.let("phi", phi, "mm")
    s.calc("A_s_prov", "n_bars*pi*phi**2/4", "mm²")
    s.check("A_s_prov", ">=", need_area, f"area provided {label}".strip(), "EC2 6.1, 9.2.1.1")
    s.let("b_w", bw, "mm")
    s.let("c_nom", cnom, "mm")
    s.let("phi_link", link, "mm")
    s.let("d_g", dg, "mm", "Maximum aggregate size (project input)")
    m = math.ceil(n / layers)
    if m > 1:
        s.let("n_layer", m, "", "Bars in one layer")
        s.calc("s_clear", "(b_w - 2*c_nom - 2*phi_link - n_layer*phi)/(n_layer - 1)", "mm")
        s.calc("s_min", "max(phi, d_g + 5, 20)", "mm", "EC2 8.2(2), k₁ = 1, k₂ = 5 mm")
        s.check("s_clear", ">=", "s_min", f"clear bar spacing {label}".strip(), "EC2 8.2(2)")
    s.calc("A_s_max", "0.04*b_w*h", "mm²", "EC2 9.2.1.1(3)")
    s.check("A_s_prov", "<=", "A_s_max", f"maximum steel {label}".strip(), "EC2 9.2.1.1(3)")
    s.provide(f"{n}H{phi} {label} ({area(phi, n):.0f} mm²)")
    return s["A_s_prov"]


# ---------------------------------------------------------------- shear
def shear_resistance(s, bw, d, Asl, show_label=""):
    """V_Rd,c (kN), no axial force."""
    s.let("b_w", bw, "mm")
    s.let("d", d, "mm")
    s.let("A_sl", Asl, "mm²", "Anchored tension steel", "EC2 Fig. 6.3")
    s.calc("C_Rd_c", "0.18/gamma_c", "", "EC2 6.2.2(1), NA")
    s.calc("k", "min(1 + sqrt(200/d), 2.0)", "", "EC2 6.2.2(1)")
    s.calc("rho_l", "min(A_sl/(b_w*d), 0.02)", "", "EC2 6.2.2(1)")
    s.calc("v_min", "0.035*k**1.5*sqrt(f_ck)", "N/mm²", "EC2 Exp. (6.3N)")
    s.calc("V_Rd_c", "max(C_Rd_c*k*(100*rho_l*f_ck)**(1/3), v_min)*b_w*d/1000", "kN", "EC2 Exp. (6.2a), (6.2b)")
    return s["V_Rd_c"]


def shear_slab(s, V, d, Asl, label=""):
    s.let("V_Ed", V, "kN/m", f"Design shear {label}".strip())
    shear_resistance(s, 1000, d, Asl)
    return s.check("V_Ed", "<=", "V_Rd_c", f"shear, no links needed {label}".strip(), "EC2 6.2.1(3), 6.2.1(4)")


def shear_beam(s, V_face, V_d, bw, d, Asl, link, legs, spacing, label=""):
    """Variable strut inclination method. V in kN."""
    s.let("V_Ed_face", V_face, "kN", "Shear at face of support")
    s.let("V_Ed_d", V_d, "kN", "Shear at d from face", "EC2 6.2.1(8)")
    shear_resistance(s, bw, d, Asl)
    need_links = V_d > s["V_Rd_c"]
    s.note("V<sub>Ed</sub> > V<sub>Rd,c</sub>: design shear links." if need_links else "V<sub>Ed</sub> ≤ V<sub>Rd,c</sub>: minimum links only.", "EC2 6.2.1(3)–(5)")
    s.let("alpha_cw", 1.0, "", "Non-prestressed", "EC2 6.2.3(3) Note 3")
    s.calc("nu_1", "0.6*(1 - f_ck/250)", "", "EC2 Exp. (6.6N); NA 6.2.3(3)")
    s.let("alpha_cc_v", s.ndp["alpha_cc_shear"], "", "α_cc for shear", "NA 3.1.6(1)")
    s.calc("f_cd_v", "alpha_cc_v*f_ck/gamma_c", "N/mm²", "EC2 Exp. (3.15)")
    s.calc("z_v", "0.9*d", "mm", "EC2 6.2.3(1)")
    s.calc("V_Rd_max_45", "alpha_cw*b_w*z_v*nu_1*f_cd_v/(1 + 1)/1000", "kN", "EC2 Exp. (6.9), cot θ = 1")
    s.check("V_Ed_face", "<=", "V_Rd_max_45", f"strut crushing at face {label}".strip(), "EC2 6.2.1(8), 6.2.3(3)")
    need(s["V_Ed_face"] <= s["V_Rd_max_45"], "Section too small for shear")
    s.calc("theta_min", "0.5*asin(min(V_Ed_face/V_Rd_max_45, 1))*180/pi", "°", "EC2 Exp. (6.9) rearranged (Notebook 2.3)", "Strut angle that just satisfies V_Rd,max")
    ct = 1 / math.tan(math.radians(s["theta_min"])) if s["theta_min"] > 0 else 2.5
    s.let("cot_theta", max(1.0, min(2.5, ct)), "", "Limited to 1 ≤ cot θ ≤ 2.5", "EC2 Exp. (6.7N), NA")
    s.calc("A_sw_s_req", "V_Ed_d*1000/(z_v*f_yd*cot_theta)", "mm²/mm", "EC2 Exp. (6.8)")
    s.calc("A_sw_s_min", "0.08*sqrt(f_ck)/f_yk*b_w", "mm²/mm", "EC2 Exp. (9.4), (9.5N)")
    s.let("phi_link", link, "mm")
    s.let("n_legs", legs, "", "Number of legs")
    s.let("s_link", spacing, "mm", "Link spacing")
    s.calc("A_sw_s", "n_legs*pi*phi_link**2/4/s_link", "mm²/mm")
    s.check("A_sw_s", ">=", "A_sw_s_min", f"minimum links {label}".strip(), "EC2 9.2.2(5)")
    if need_links:
        s.check("A_sw_s", ">=", "A_sw_s_req", f"design links {label}".strip(), "EC2 6.2.3(3)")
    s.calc("s_l_max", "0.75*d", "mm", "EC2 Exp. (9.6N)")
    s.check("s_link", "<=", "s_l_max", f"longitudinal link spacing {label}".strip(), "EC2 9.2.2(6)")
    s.let("s_t_max", min(0.75 * d, 600), "mm", "Maximum transverse leg spacing", "EC2 Exp. (9.8N)")
    s.calc("V_Rd_s", "A_sw_s*z_v*f_yd*cot_theta/1000", "kN", "EC2 Exp. (6.8)", "Resistance of the links provided")
    s.provide(f"H{link} – {legs} legs @ {spacing} mm {label}")
    return s["cot_theta"]


# ---------------------------------------------------------------- serviceability
def deflection(s, span, d, b, As_req, As_prov, system, As2_req=0.0, bf_bw=1.0, partitions=True, label=""):
    """Span/depth check, EC2 7.4.2 (span in mm)."""
    s.let("K_sys", DEFL_K[system], "", f"Structural system: {system}", "EC2 Table 7.4N / NA.5")
    s.let("l_eff", span, "mm", "Effective span")
    s.let("rho_0", 1e-3 * math.sqrt(s["f_ck"]), "", "10⁻³ √fck", "EC2 7.4.2(2)")
    s.let("A_s_ult", As_req, "mm²", "Steel required for ULS at mid-span")
    s.let("b", b, "mm")
    s.let("d", d, "mm")
    s.calc("rho", "A_s_ult/(b*d)", "", "EC2 7.4.2(2)")
    if s["rho"] <= s["rho_0"]:
        s.calc("N_basic", "K_sys*(11 + 1.5*sqrt(f_ck)*rho_0/rho + 3.2*sqrt(f_ck)*(rho_0/rho - 1)**1.5)", "", "EC2 Exp. (7.16a)", "Basic l/d")
    else:
        s.let("rho_prime", As2_req / (b * d), "", "Compression steel ratio", "EC2 7.4.2(2)")
        s.calc("N_basic", "K_sys*(11 + 1.5*sqrt(f_ck)*rho_0/(rho - rho_prime) + sqrt(f_ck)/12*sqrt(rho_prime/rho_0))", "", "EC2 Exp. (7.16b)", "Basic l/d")
    s.let("F_1", 0.8 if bf_bw > 3 else 1.0, "", f"Flanged section, b_f/b_w = {bf_bw:.2f}", "EC2 7.4.2(2)")
    s.let("F_2", 7000 / span if (partitions and span > 7000) else 1.0, "", "Span > 7 m with brittle partitions", "EC2 7.4.2(2)")
    s.let("A_s_prov", As_prov, "mm²")
    if s.ndp["defl_cap"]:
        s.let("F_cap", s.ndp["defl_cap"], "", "Cap on the steel-stress factor", "NA Table NA.5 Note 5")
        s.calc("F_3", "min(500/(f_yk*A_s_ult/A_s_prov), F_cap)", "", "EC2 Exp. (7.17), NA Note 5")
        s.let("N_abs", s.ndp["defl_abs"], "", "Absolute limit 40K", "NA Table NA.5 Note 6")
        s.calc("N_allow", "min(N_basic*F_1*F_2*F_3, N_abs*K_sys)", "", "EC2 7.4.2(2), NA")
    else:
        s.calc("F_3", "500/(f_yk*A_s_ult/A_s_prov)", "", "EC2 Exp. (7.17)")
        s.calc("N_allow", "N_basic*F_1*F_2*F_3", "", "EC2 7.4.2(2)")
    s.calc("N_actual", "l_eff/d")
    return s.check("N_actual", "<=", "N_allow", f"deflection (span/depth) {label}".strip(), "EC2 7.4.2")


def crack(s, g, q, psi2, As_req, As_prov, spacing, h, n_uls=None, delta=1.0, label=""):
    """Crack control without direct calculation. g, q in consistent load units."""
    if h <= 200 and n_uls == "slab":
        s.note("Slab ≤ 200 mm thick without axial tension and detailed to EC2 9.3: no specific crack-control measures needed.", "EC2 7.3.3(1)")
        s.verdict(True, f"crack control {label}".strip(), "EC2 7.3.3(1)")
        return True
    s.let("psi_2", psi2, "", "Quasi-permanent factor", "EN 1990 Table A1.1")
    s.let("G_k", g, "", "Permanent load on the member")
    s.let("Q_k", q, "", "Variable load on the member")
    s.let("delta", delta, "", "Moment redistribution ratio")
    s.let("A_s_ult", As_req, "mm²")
    s.let("A_s_prov", As_prov, "mm²")
    s.calc("sigma_s", "f_yd*(G_k + psi_2*Q_k)/(1.35*G_k + 1.5*Q_k)*A_s_ult/A_s_prov/delta", "N/mm²", "EN 1990 (6.16b); method as JRC EUR 26566 (2014) 3.3.1.3", "Steel stress, quasi-permanent load")
    lim = next((sp for st, sp in CRACK_SPACING if s["sigma_s"] <= st), None)
    need(lim, "Steel stress above EC2 Table 7.3N range")
    s.let("s_crack", lim, "mm", "Maximum bar spacing, w_k = 0.3 mm (next higher tabulated stress, no interpolation)", "EC2 Table 7.3N, NA.4")
    s.let("s_bars", spacing, "mm", "Bar spacing provided (centres)")
    return s.check("s_bars", "<=", "s_crack", f"crack control {label}".strip(), "EC2 7.3.3(2)")


def crack_min(s, b, h, As_prov, label=""):
    """Minimum steel for crack control, pure bending, EC2 7.3.2."""
    s.let("k_c", 0.4, "", "Bending, σ_c = 0", "EC2 Exp. (7.2)")
    kk = 1.0 if h <= 300 else 0.65 if h >= 800 else 1.0 - 0.35 * (h - 300) / 500
    s.let("k_h", kk, "", "Coefficient k, interpolated on depth", "EC2 7.3.2(2)")
    s.let("b", b, "mm")
    s.let("h", h, "mm")
    s.calc("A_ct", "b*h/2", "mm²", "EC2 7.3.2(2)", "Tension zone before cracking")
    s.calc("A_s_crack", "k_c*k_h*f_ctm*A_ct/f_yk", "mm²", "EC2 Exp. (7.1), σ_s = f_yk")
    s.let("A_s_prov", As_prov, "mm²")
    s.check("A_s_prov", ">=", "A_s_crack", f"minimum steel for cracking {label}".strip(), "EC2 7.3.2")


# ---------------------------------------------------------------- bond
def anchorage(s, phi, sigma=None, good=True, lap_pct=None, compression=False, label="", cd=None):
    """l_bd (mm), and l_0 when lap_pct is given. All alpha coefficients = 1.0 unless cd is given (straight bar, alpha_2)."""
    s.let("phi", phi, "mm", f"Bar {label}".strip())
    s.calc("f_ctk_005", "0.7*f_ctm", "N/mm²", "EC2 Table 3.1")
    s.let("alpha_ct", s.ndp["alpha_ct"], "", "", "EC2 3.1.6(2), NA")
    s.calc("f_ctd", "alpha_ct*f_ctk_005/gamma_c", "N/mm²", "EC2 Exp. (3.16)")
    s.let("eta_1", 1.0 if good else 0.7, "", "Good bond" if good else "Poor bond (top bars, h > 250 mm)", "EC2 8.4.2, Fig. 8.2")
    s.let("eta_2", 1.0, "", "φ ≤ 32 mm", "EC2 8.4.2")
    s.calc("f_bd", "2.25*eta_1*eta_2*f_ctd", "N/mm²", "EC2 Exp. (8.2)")
    s.let("sigma_sd", s["f_yd"] if sigma is None else sigma, "N/mm²", "Design bar stress", "EC2 8.4.3(2)")
    s.calc("l_b_rqd", "phi/4*sigma_sd/f_bd", "mm", "EC2 Exp. (8.3)")
    a2 = 1.0 if cd is None or compression else max(0.7, min(1.0, 1 - 0.15 * (cd - phi) / phi))
    s.let("alpha_2", a2, "", "Cover coefficient (others = 1.0, conservative)", "EC2 Table 8.2")
    s.let("f_lmin", 0.6 if compression else 0.3, "", "Compression" if compression else "Tension", "EC2 Exp. (8.6)/(8.7)")
    s.calc("l_b_min", "max(f_lmin*l_b_rqd, 10*phi, 100)", "mm", "EC2 8.4.4(1)")
    s.calc("l_bd", "max(alpha_2*l_b_rqd, l_b_min)", "mm", "EC2 Exp. (8.4)")
    if lap_pct:
        s.let("alpha_6", max(1.0, min(1.5, (lap_pct / 25) ** 0.5)), "", f"{lap_pct}% lapped", "EC2 8.7.3")
        s.calc("l_0_lap", "max(alpha_2*alpha_6*l_b_rqd, 0.3*alpha_6*l_b_rqd, 15*phi, 200)", "mm", "EC2 Exp. (8.10), (8.11)")
        return s["l_bd"], s["l_0_lap"]
    return s["l_bd"]


def bent_anchorage(s, W, c, phi, leg, label="", straight_len=None):
    """90 degree bend at an end support; length measured along the bar centre-line (EC2 8.4.3(3)). Expects l_bd."""
    s.let("W", W, "mm", "Support width")
    s.calc("l_straight", "W - c_nom", "mm", "", "Straight length available")
    if s["l_straight"] >= s["l_bd"]:
        s.check("l_straight", ">=", "l_bd", f"straight anchorage {label}".strip(), "EC2 9.2.1.4(3)")
        return
    s.note("A straight bar does not have enough length, so a 90° bend is provided.", "EC2 8.4.1(2), Fig. 8.1")
    m = 4 if phi <= 16 else 7
    s.let("k_m", m, "", "Minimum mandrel diameter / φ", "NA Table NA.6a")
    s.calc("r_c", "(k_m*phi + phi)/2", "mm", "", "Radius of the bar centre-line")
    s.let("l_leg", leg, "mm", "Vertical leg, from the centre of the horizontal bar")
    s.calc("l_bent", "W - c_nom - phi/2 + l_leg - (2 - pi/2)*r_c", "mm", "EC2 8.4.3(3)", "Length along the centre-line")
    s.check("l_bent", ">=", "l_bd", f"bent-bar anchorage {label}".strip(), "EC2 9.2.1.4(3), 8.4.3(3)")
    s.calc("l_past", "max(l_bd - (W - c_nom - phi/2 - r_c) - pi*r_c/2, 0)", "mm", "EC2 8.3(3)", "Length needed past the end of the bend")
    s.calc("l_5", "5*phi", "mm", "EC2 8.3(3)")
    s.check("l_past", "<=", "l_5", f"no mandrel check needed {label}".strip(), "EC2 8.3(3)")
    s.note("Provide a cross bar of diameter ≥ φ inside the bend.", "EC2 8.3(3)")
    s.provide(f"90° bend, {leg} mm leg {label}".strip())
