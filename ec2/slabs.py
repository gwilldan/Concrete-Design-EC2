"""Slab moment/shear coefficients.

EC2 gives no coefficients; it allows any elastic / redistributed / plastic analysis (5.1.1, 5.4-5.6).
Values below: BS 8110-1:1997 Tables 3.12, 3.13, 3.14 and 3.15, checked value by value.
BS 8110-1 is withdrawn; it supplies only the analysis coefficients. Loads come from EN 1990.
Table 3.14 is also re-derived from its equations in tests/ as a cross-check.
Table 3.15 captions its two "three edges discontinuous" panels "(one long/short edge discontinuous)";
they are read here as "continuous", the wording of Table 3.14.
"""
import math

import numpy as np

RATIO = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0]
# panel type: (neg short-span, pos short-span, neg long-span, pos long-span)
BETA_S = {
    "interior": ([.031, .037, .042, .046, .050, .053, .059, .063], [.024, .028, .032, .035, .037, .040, .044, .048], .032, .024),
    "one short edge discontinuous": ([.039, .044, .048, .052, .055, .058, .063, .067], [.029, .033, .036, .039, .041, .043, .047, .050], .037, .028),
    "one long edge discontinuous": ([.039, .049, .056, .062, .068, .073, .082, .089], [.030, .036, .042, .047, .051, .055, .062, .067], .037, .028),
    "two adjacent edges discontinuous": ([.047, .056, .063, .069, .074, .078, .087, .093], [.036, .042, .047, .051, .055, .059, .065, .070], .045, .034),
    "two short edges discontinuous": ([.046, .050, .054, .057, .060, .062, .067, .070], [.034, .038, .040, .043, .045, .047, .050, .053], None, .034),
    "two long edges discontinuous": (None, [.034, .046, .056, .065, .072, .078, .091, .100], .045, .034),
    "three edges discontinuous (one long edge continuous)": ([.057, .065, .071, .076, .081, .084, .092, .098], [.043, .048, .053, .057, .060, .063, .069, .074], None, .044),
    "three edges discontinuous (one short edge continuous)": (None, [.042, .054, .063, .071, .078, .084, .096, .105], .058, .044),
    "four edges discontinuous": (None, [.055, .065, .074, .081, .087, .092, .103, .111], None, .056),
}
# panel type: (short-span continuous edge, short-span discontinuous edge, long-span cont., long-span discont.)
BETA_V = {
    "interior": ([.33, .36, .39, .41, .43, .45, .48, .50], None, .33, None),
    "one short edge discontinuous": ([.36, .39, .42, .44, .45, .47, .50, .52], None, .36, .24),
    "one long edge discontinuous": ([.36, .40, .44, .47, .49, .51, .55, .59], [.24, .27, .29, .31, .32, .34, .36, .38], .36, None),
    "two adjacent edges discontinuous": ([.40, .44, .47, .50, .52, .54, .57, .60], [.26, .29, .31, .33, .34, .35, .38, .40], .40, .26),
    "two short edges discontinuous": ([.40, .43, .45, .47, .48, .49, .52, .54], None, None, .26),
    "two long edges discontinuous": (None, [.26, .30, .33, .36, .38, .40, .44, .47], .40, None),
    "three edges discontinuous (one long edge continuous)": ([.45, .48, .51, .53, .55, .57, .60, .63], [.30, .32, .34, .35, .36, .37, .39, .41], None, .29),
    "three edges discontinuous (one short edge continuous)": (None, [.29, .33, .36, .38, .40, .42, .45, .48], .45, .30),
    "four edges discontinuous": (None, [.33, .36, .39, .41, .43, .45, .48, .50], None, .33),
}
# number of continuous short edges, long edges (short-span moments act over the LONG edges)
EDGES = {"interior": (2, 2), "one short edge discontinuous": (1, 2), "one long edge discontinuous": (2, 1),
         "two adjacent edges discontinuous": (1, 1), "two short edges discontinuous": (0, 2), "two long edges discontinuous": (2, 0),
         "three edges discontinuous (one long edge continuous)": (0, 1), "three edges discontinuous (one short edge continuous)": (1, 0),
         "four edges discontinuous": (0, 0)}
ALPHA_SX = [.062, .074, .084, .093, .099, .104, .113, .118]
ALPHA_SY = [.062, .061, .059, .055, .051, .046, .037, .029]
ONE_WAY = {"M outer support": 0.0, "M end span": .086, "M first interior support": -.086, "M interior span": .063,
           "M interior support": -.063, "V outer support": .40, "V first interior support": .60, "V interior support": .50}


def _interp(row, r):
    if row is None or not isinstance(row, list):
        return row
    if not 1.0 <= r <= 2.0:
        raise ValueError("Table covers 1.0 <= ly/lx <= 2.0")
    return float(np.interp(r, RATIO, row))


def two_way(panel, r):
    n, p, ny, py = BETA_S[panel]
    return {"sx_neg": _interp(n, r), "sx_pos": _interp(p, r), "sy_neg": ny, "sy_pos": py}


def two_way_shear(panel, r):
    c, d, cy, dy = BETA_V[panel]
    return {"vx_cont": _interp(c, r), "vx_disc": _interp(d, r), "vy_cont": cy, "vy_disc": dy}


def simply_supported(r):
    return _interp(ALPHA_SX, r), _interp(ALPHA_SY, r)


def derive(panel, r):
    """Table 3.14 from its equations (BS 8110-1 Eqs 16-18): (bx_neg, bx_pos, by_neg, by_pos)."""
    cs, cl = EDGES[panel]
    nd = 4 - cs - cl
    by = (24 + 2 * nd + 1.5 * nd**2) / 1000
    b1, b2 = [(4 / 3 * by if i < cs else 0) for i in range(2)]
    g = 2 / 9 * (3 - math.sqrt(18) / r * (math.sqrt(by + b1) + math.sqrt(by + b2)))
    f = sum(math.sqrt(1 + (4 / 3 if i < cl else 0)) for i in range(2))
    bx = g / f**2
    return (4 / 3 * bx if cl else None, bx, 4 / 3 * by if cs else None, by)
