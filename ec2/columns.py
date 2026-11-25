"""Columns: slenderness, imperfections, nominal curvature, N-M interaction, biaxial check."""
import math

import numpy as np


def interaction(b, h, layers, fcd, fyd, Es=200000.0, n=500):
    """N (kN), M (kN.m) pairs. layers = [(area mm2, depth mm from compression face)].

    EC2 Fig. 6.1 strain limits; 3.1.7(3) rectangular block (fck <= 50): depth 0.8x, stress fcd.
    Concrete displaced by compression bars is deducted.
    """
    e2, eu = 0.002, 0.0035
    xs = np.concatenate([np.linspace(0.02 * h, h, n), h * np.geomspace(1.0001, 400, n)])
    out = []
    for x in xs:
        if x <= h:
            strain = lambda y: eu * (x - y) / x
        else:
            strain = lambda y: e2 * (x - y) / (x - 3 * h / 7)
        a = min(0.8 * x, h)
        N, M = fcd * b * a, fcd * b * a * (h / 2 - a / 2)
        for As, y in layers:
            f = max(-fyd, min(fyd, Es * strain(y)))
            if y < a:
                f -= fcd
            N, M = N + As * f, M + As * f * (h / 2 - y)
        out.append((N / 1e3, M / 1e6))
    As = sum(l[0] for l in layers)
    out.insert(0, (-As * fyd / 1e3, sum(-A * fyd * (h / 2 - y) for A, y in layers) / 1e6))
    f = min(fyd, Es * e2)
    out.append(((fcd * (b * h - As) + f * As) / 1e3, sum(A * (f - fcd) * (h / 2 - y) for A, y in layers) / 1e6))
    return np.array(out)


def MRd(curve, N):
    """Moment resistance at axial load N (kN)."""
    Ns, Ms = curve[:, 0], curve[:, 1]
    if not Ns.min() <= N <= Ns.max():
        return 0.0
    return max(float(Ms[i] + (N - Ns[i]) / (Ns[i + 1] - Ns[i]) * (Ms[i + 1] - Ms[i]))
               for i in range(len(Ns) - 1) if min(Ns[i], Ns[i + 1]) <= N <= max(Ns[i], Ns[i + 1]) and Ns[i] != Ns[i + 1])


def perimeter_layers(nb, nh, phi, b, h, dc):
    """nb bars along each face parallel to the bending axis, nh bars along each side (corners in both)."""
    A = math.pi * phi**2 / 4
    ys = np.linspace(dc, h - dc, nh)
    return [(A * (nb if i in (0, nh - 1) else 2), float(y)) for i, y in enumerate(ys)]


def slenderness(s, l, h, N, b, M01=None, M02=None, k1=None, k2=None, l0=None, As=None, tag=""):
    """l, l0 in m; b, h in mm (h in the plane of bending). Returns True when slender."""
    s.let("h", h, "mm", "Depth in the plane of bending")
    s.let("b", b, "mm")
    s.let("l", l, "m", "Clear height")
    s.let("N_Ed", N, "kN")
    if l0 is None:
        s.let("k1", k1, "", "Relative flexibility, end 1 (≥ 0.1)", "EC2 5.8.3.2(3)")
        s.let("k2", k2, "", "Relative flexibility, end 2 (≥ 0.1)", "EC2 5.8.3.2(3)")
        s.calc("l0", "0.5*l*sqrt((1 + k1/(0.45 + k1))*(1 + k2/(0.45 + k2)))", "m", "EC2 Exp. (5.15) – braced")
    else:
        s.let("l0", l0, "m", "Effective length")
    s.calc("i", "h/sqrt(12)", "mm", "EC2 5.8.3.2(1)", "Radius of gyration, rectangle")
    s.calc("lam", "l0*1000/i", "", "EC2 Exp. (5.14)")
    s.calc("n", "N_Ed*1000/(b*h*f_cd)", "", "EC2 5.8.3.1")
    s.let("A", 0.7, "", "Creep ratio not used: default", "EC2 5.8.3.1(1)")
    if As is None:
        s.let("B", 1.1, "", "Steel ratio not used: default", "EC2 5.8.3.1(1)")
    else:
        s.let("A_s", As, "mm²")
        s.calc("omega", "A_s*f_yd/(b*h*f_cd)", "", "EC2 5.8.3.1(1)")
        s.calc("B", "sqrt(1 + 2*omega)", "", "EC2 5.8.3.1(1)")
    if M02 is None or M02 == 0:
        s.let("C", 0.7, "", "r_m = 1.0 (moments mainly from imperfections)", "EC2 5.8.3.1(1)")
    else:
        s.let("M_01", M01, "kN·m", "Smaller end moment (same sign = tension on same side)")
        s.let("M_02", M02, "kN·m", "Larger end moment")
        s.calc("r_m", "M_01/M_02", "", "EC2 5.8.3.1(1)")
        s.calc("C", "1.7 - r_m", "", "EC2 5.8.3.1(1)")
    s.calc("lam_lim", "20*A*B*C/sqrt(n)", "", "EC2 Exp. (5.13N), NA")
    slender = s["lam"] > s["lam_lim"]
    s.note(f"λ {'>' if slender else '≤'} λ<sub>lim</sub> → the column is **{'SLENDER' if slender else 'STOCKY (short)'}** {tag}: second-order effects "
           + ("must be included." if slender else "may be ignored."), "EC2 5.8.3.1")
    return slender


def imperfection(s):
    """Expects l0 (m), N_Ed, h in the sheet. Returns minimum-eccentricity moment."""
    s.calc("e_i", "l0*1000/400", "mm", "EC2 5.2(7), 5.2(9) – braced", "Imperfection eccentricity")
    s.calc("e_0", "max(h/30, 20)", "mm", "EC2 6.1(4)", "Minimum eccentricity")
    s.calc("M_min", "N_Ed*e_0/1000", "kN·m", "EC2 6.1(4)")


def creep(s, b, h, RH, t0):
    """Final creep coefficient, EC2 Annex B (beta_c = 1 as t -> infinity; cement class N)."""
    s.let("RH", RH, "%", "Relative humidity (project input)")
    s.let("t_0", t0, "days", "Age at loading (project input)")
    s.calc("f_cm", "f_ck + 8", "N/mm²", "EC2 Table 3.1")
    s.let("h_0", 2 * b * h / (2 * (b + h)), "mm", "Notional size 2Ac/u", "EC2 Exp. (B.6)")
    if s["f_cm"] > 35:
        s.calc("alpha_1", "(35/f_cm)**0.7", "", "EC2 Exp. (B.8c)")
        s.calc("alpha_2c", "(35/f_cm)**0.2", "", "EC2 Exp. (B.8c)")
    else:
        s["alpha_1"] = s["alpha_2c"] = 1.0
    s.calc("phi_RH", "(1 + (1 - RH/100)/(0.1*h_0**(1/3))*alpha_1)*alpha_2c", "", "EC2 Exp. (B.3)")
    s.calc("beta_fcm", "16.8/sqrt(f_cm)", "", "EC2 Exp. (B.4)")
    s.calc("beta_t0", "1/(0.1 + t_0**0.2)", "", "EC2 Exp. (B.5)")
    s.calc("phi_inf", "phi_RH*beta_fcm*beta_t0", "", "EC2 Exp. (B.1), (B.2)", "Final creep coefficient φ(∞,t₀)")


def second_order(s, d, ratio):
    """Nominal curvature method, EC2 5.8.8. Call creep() first. Expects slenderness() + A_s, M_01, M_02 (with imperfection) in the sheet."""
    s.let("d", d, "mm", "Effective depth")
    s.calc("eps_yd", "f_yd/E_s", "", "EC2 5.8.8.3(1)")
    s.calc("curv0", "eps_yd/(0.45*d)", "1/mm", "EC2 5.8.8.3(1)")
    s.calc("omega", "A_s*f_yd/(b*h*f_cd)", "", "EC2 5.8.8.3(3)")
    s.calc("n_u", "1 + omega", "", "EC2 5.8.8.3(3)")
    s.let("n_bal", 0.4, "", "", "EC2 5.8.8.3(3)")
    s.calc("K_r", "min((n_u - n)/(n_u - n_bal), 1)", "", "EC2 Exp. (5.36)")
    s.calc("beta", "0.35 + f_ck/200 - lam/150", "", "EC2 Exp. (5.37)")
    s.let("r_qp", ratio, "", "M₀Eqp / M₀Ed, taken as the quasi-permanent / ULS load ratio", "EC2 5.8.4(2)")
    s.calc("phi_ef", "phi_inf*r_qp", "", "EC2 Exp. (5.19)")
    s.calc("K_phi", "max(1 + beta*phi_ef, 1)", "", "EC2 Exp. (5.37)")
    s.calc("curv", "K_r*K_phi*curv0", "1/mm", "EC2 Exp. (5.34)")
    s.let("c", 10, "", "Constant cross-section", "EC2 5.8.8.2(4)")
    s.calc("e_2", "curv*(l0*1000)**2/c", "mm", "EC2 5.8.8.2(3)")
    s.calc("M_2", "N_Ed*e_2/1000", "kN·m", "EC2 Exp. (5.33)")
    s.calc("M_0e", "max(0.6*M_02 + 0.4*M_01, 0.4*M_02)", "kN·m", "EC2 Exp. (5.32)")


def links(s, phi_min, phi_max, b, h, link, spacing, n_face_b, n_face_h, c_nom, ties=False):
    s.let("phi_link", link, "mm")
    s.calc("phi_link_min", f"max(6, {phi_max}/4)", "mm", "EC2 9.5.3(1)")
    s.check("phi_link", ">=", "phi_link_min", "link diameter", "EC2 9.5.3(1)")
    s.let("s_cl_max", min(20 * phi_min, min(b, h), 400), "mm", "min(20 φ_min, smaller side, 400)", "EC2 9.5.3(3), NA")
    s.let("s_link", spacing, "mm", "Link spacing")
    s.check("s_link", "<=", "s_cl_max", "link spacing", "EC2 9.5.3(3)")
    s.calc("s_cl_red", "0.6*s_cl_max", "mm", "EC2 9.5.3(4)", f"Within {max(b, h):.0f} mm above/below a beam or slab, and at laps of bars > 14 mm")
    red = int(s["s_cl_red"] // 25 * 25)
    s.provide(f"H{link} links @ {spacing} mm; @ {red} mm near beams, slabs and laps")
    gaps = [(side - 2 * (c_nom + link) - phi_max) / (k - 1) for side, k in ((b, n_face_b), (h, n_face_h)) if k > 2]
    if gaps:
        s.let("s_face", max(gaps), "mm", "Distance from an intermediate bar to the restrained corner bar (centres)")
        if ties and s["s_face"] > 150:
            s.note(f"{s['s_face']:.0f} mm > 150 mm, so the middle bars are themselves restrained by cross-ties.", "EC2 9.5.3(6)")
            s.provide(f"H{link} cross-ties to the middle bars, both directions, at every link")
            s.verdict(True, "every bar restrained (cross-ties provided)", "EC2 9.5.3(6)")
            return
        s.check("s_face", "<=", 150, "bar within 150 mm of a restrained bar, else add cross-ties", "EC2 9.5.3(6)")


def biaxial_exponent(ratio):
    return float(np.interp(ratio, [0.1, 0.7, 1.0], [1.0, 1.5, 2.0]))
