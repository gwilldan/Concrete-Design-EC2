"""Pad foundations: punching scan (EC2 6.4.4(2)) and bar anchorage model (EC2 9.8.2.2)."""
import math

import numpy as np


def k_table61(r):
    """EC2 Table 6.1, k for c1/c2."""
    return float(np.interp(r, [0.5, 1, 2, 3], [0.45, 0.60, 0.70, 0.80]))


def punching_scan(N, M, B, L, c1, c2, d, rho, fck, gamma_c=1.5):
    """Control perimeters at a <= 2d. N kN, M kN.m (in the c1 / L direction), lengths mm.

    Net applied force uses the net upward pressure N/(B L), i.e. soil pressure minus base self-weight.
    Eccentric case: EC2 Exp. (6.51), W for a perimeter at distance a = Exp. (6.41) with 2d replaced by a.
    Returns rows (a, u, V_red, v_Ed, v_Rd, ratio).
    """
    k = min(1 + math.sqrt(200 / d), 2.0)
    vmin = 0.035 * k**1.5 * math.sqrt(fck)
    v0 = max(0.18 / gamma_c * k * (100 * min(rho, 0.02) * fck) ** (1 / 3), vmin)
    p = N * 1e3 / (B * L)
    rows = []
    for a in np.arange(0.25, 2.0001, 0.05) * d:
        if c1 + 2 * a > L or c2 + 2 * a > B:
            break
        u = 2 * (c1 + c2) + 2 * math.pi * a
        A = c1 * c2 + 2 * a * (c1 + c2) + math.pi * a**2
        V = N * 1e3 - p * A
        W = c1**2 / 2 + c1 * c2 + 2 * c2 * a + 4 * a**2 + math.pi * a * c1
        f = 1 + k_table61(c1 / c2) * abs(M) * 1e6 * u / (V * W) if V > 0 else 1.0
        v = max(V, 0) / (u * d) * f
        vr = v0 * 2 * d / a
        rows.append((a, u, V / 1e3, v, vr, v / vr))
    return rows
