"""Nationally Determined Parameters (NDPs) and code tables.

UK  = NA to BS EN 1992-1-1:2004 incl. National Amendment No.1 (Dec 2009)
EN  = values recommended in EN 1992-1-1:2004 itself
"""
UK = dict(name="UK National Annex", alpha_cc=0.85, alpha_cc_shear=1.0, alpha_ct=1.0, gamma_c=1.5, gamma_s=1.15,
          k1=0.40, k2=1.00, vmax=0.5, beta1=0.25, phi_col_min=12, defl_cap=1.5, defl_abs=40,
          gamma_G=1.35, gamma_Q=1.50)
EN = dict(name="EN recommended values", alpha_cc=1.0, alpha_cc_shear=1.0, alpha_ct=1.0, gamma_c=1.5, gamma_s=1.15,
          k1=0.44, k2=1.25, vmax=0.4, beta1=0.15, phi_col_min=8, defl_cap=None, defl_abs=None,
          gamma_G=1.35, gamma_Q=1.50)

# EN 1992-1-1 Table 4.4N, structural class S4 (50-year design life)
COVER_DUR = {"X0": 10, "XC1": 15, "XC2": 25, "XC3": 25, "XC4": 30, "XD1": 35, "XS1": 35,
             "XD2": 40, "XS2": 40, "XD3": 45, "XS3": 45}

# EN 1990 Table A1.1 / NA.A1.1 : psi0, psi1, psi2
PSI = {"A": (0.7, 0.5, 0.3), "B": (0.7, 0.5, 0.3), "C": (0.7, 0.7, 0.6), "D": (0.7, 0.7, 0.6), "E": (1.0, 0.9, 0.8)}

# EN 1992-1-1 Table 7.4N / NA Table NA.5 : K
DEFL_K = {"simply supported": 1.0, "end span": 1.3, "interior span": 1.5, "flat slab": 1.2, "cantilever": 0.4}

# EN 1992-1-1 Table 7.3N, wk = 0.3 mm : steel stress -> max bar spacing
CRACK_SPACING = [(160, 300), (200, 250), (240, 200), (280, 150), (320, 100), (360, 50)]

# EN 1992-1-2 Table 5.8 : REI -> (hs, a one-way, a two-way ly/lx<=1.5, a two-way 1.5<ly/lx<=2)
FIRE_SLAB = {30: (60, 10, 10, 10), 60: (80, 20, 10, 15), 90: (100, 30, 15, 20), 120: (120, 40, 20, 25),
             180: (150, 55, 30, 40), 240: (175, 65, 40, 50)}
# EN 1992-1-2 Table 5.5 (simply supported) / 5.6 (continuous) : R -> [(bmin, a), ...]
FIRE_BEAM_SS = {30: [(80, 25), (120, 20), (160, 15), (200, 15)], 60: [(120, 40), (160, 35), (200, 30), (300, 25)],
                90: [(150, 55), (200, 45), (300, 40), (400, 35)], 120: [(200, 65), (240, 60), (300, 55), (500, 50)]}
FIRE_BEAM_CONT = {30: [(80, 15), (160, 12)], 60: [(120, 25), (200, 12)], 90: [(150, 35), (250, 25)],
                  120: [(200, 45), (300, 35), (450, 35), (500, 30)]}
# EN 1992-1-2 Table 5.2a, mu_fi = 0.7, exposed on more than one side : R -> [(bmin, a, min 8 bars?)]
FIRE_COL = {30: [(200, 32, False), (300, 27, False)], 60: [(250, 46, False), (350, 40, False)],
            90: [(350, 53, False), (450, 40, True)], 120: [(350, 57, True), (450, 51, True)]}

# EN 1992-1-2 Table 5.2b (method B), row omega = 0.1 (conservative for larger omega) : R -> {n: [(bmin, a), ...]}
FIRE_COL_B = {30: {0.15: [(150, 25)], 0.3: [(150, 25)], 0.5: [(200, 30), (250, 25)], 0.7: [(300, 30), (350, 25)]},
              60: {0.15: [(150, 30), (200, 25)], 0.3: [(200, 40), (300, 25)], 0.5: [(300, 40), (500, 25)], 0.7: [(500, 25)]},
              90: {0.15: [(200, 40), (250, 25)], 0.3: [(300, 40), (400, 25)], 0.5: [(500, 50), (550, 25)], 0.7: [(550, 40), (600, 25)]}}

BARS = (8, 10, 12, 16, 20, 25, 32)
