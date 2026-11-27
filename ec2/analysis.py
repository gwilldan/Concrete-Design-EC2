"""Structural analysis: determinate beams, three-moment equation, moment distribution.

Units kN, m.  Bending moment: sagging positive.  Loads act downward.
Moment distribution uses the NPTEL (IIT Kharagpur) convention:
counter-clockwise member-end moments positive.
"""
from dataclasses import dataclass, field

import numpy as np


# ---------------------------------------------------------------- loads
@dataclass
class Point:
    P: float
    a: float


@dataclass
class UDL:
    w: float
    a: float = 0.0
    b: float = None      # None = to the end of the span


@dataclass
class UVL:
    """Linearly varying load, w1 at x=a to w2 at x=b."""
    w1: float
    w2: float
    a: float
    b: float


@dataclass
class Moment:
    """Applied couple, clockwise positive."""
    M: float
    a: float


def _resultant(q, L):
    if isinstance(q, Point):
        return q.P, q.a
    if isinstance(q, UDL):
        b = L if q.b is None else q.b
        return q.w * (b - q.a), (q.a + b) / 2
    if isinstance(q, UVL):
        n = q.b - q.a
        W = (q.w1 + q.w2) / 2 * n
        return W, q.a + n * (q.w1 + 2 * q.w2) / (3 * (q.w1 + q.w2))
    raise TypeError(q)


def _left_VM(q, x, L):
    """Downward load, and its moment about x, for the part of q to the left of x."""
    if isinstance(q, Point):
        on = x > q.a
        return q.P * on, q.P * (x - q.a) * on
    if isinstance(q, UDL):
        b = L if q.b is None else q.b
        n = np.clip(x, q.a, b) - q.a
        W = q.w * n
        return W, W * (x - q.a - n / 2)
    if isinstance(q, UVL):
        n = np.clip(x, q.a, q.b) - q.a
        s = (q.w2 - q.w1) / (q.b - q.a)
        W = q.w1 * n + s * n**2 / 2
        # moment of trapezoid about x
        return W, q.w1 * n * (x - q.a - n / 2) + s * n**2 / 2 * (x - q.a - 2 * n / 3)
    raise TypeError(q)


def grid(L, loads, n=601):
    pts = [0, L]
    for q in loads:
        for k in ("a", "b"):
            v = getattr(q, k, None)
            if v is not None:
                pts += [max(0, v - 1e-9), min(L, v + 1e-9)]
    return np.unique(np.concatenate([np.linspace(0, L, n), pts]))


# ---------------------------------------------------------------- determinate beams
class DeterminateBeam:
    """supports=(xA, xB) for a two-support beam (overhangs allowed); fixed='left' for a cantilever."""

    def __init__(self, L, loads, supports=None, fixed=None):
        self.L, self.loads, self.supports, self.fixed = L, loads, supports, fixed
        W = M0 = 0.0
        for q in loads:
            if isinstance(q, Moment):
                M0 += q.M
            else:
                w, xb = _resultant(q, L)
                W, M0 = W + w, M0 + w * xb
        self.W = W
        if fixed:
            self.RA, self.MA = W, -M0          # fixed at x = 0
            self.reactions = {0.0: W}
        else:
            a, b = supports
            RB = (M0 - W * a) / (b - a)
            self.RA, self.RB, self.MA = W - RB, RB, 0.0
            self.reactions = {a: self.RA, b: RB}
        pts = grid(L, loads)
        sup = [s for s in self.reactions]
        self.x = np.unique(np.concatenate([pts] + [[max(0, s - 1e-9), min(L, s + 1e-9)] for s in sup]))
        self.V, self.M = self._VM(self.x)

    def _VM(self, x):
        V = np.zeros_like(x)
        M = np.full_like(x, self.MA)
        for s, R in self.reactions.items():
            on = x > s if s > 0 else x >= s
            V, M = V + R * on, M + R * (x - s) * on
        for q in self.loads:
            if isinstance(q, Moment):
                M = M + q.M * (x > q.a)
            else:
                w, m = _left_VM(q, x, self.L)
                V, M = V - w, M - m
        return V, M


# ---------------------------------------------------------------- continuous beams
@dataclass
class Span:
    L: float
    loads: list = field(default_factory=list)
    I: float = 1.0

    def _poly(self, q, f_point, f_int):
        if isinstance(q, Point):
            return q.P * f_point(q.a)
        b = self.L if q.b is None else q.b
        return q.w * (f_int(b) - f_int(q.a))

    def three_moment_terms(self):
        """(6*A*xbar_from_left/L, 6*A*xbar_from_right/L) of the simply supported BMD."""
        L = self.L
        l = sum(self._poly(q, lambda a: a * (L - a) * (L + a) / L, lambda x: (L**2 * x**2 / 2 - x**4 / 4) / L) for q in self.loads)
        r = sum(self._poly(q, lambda a: a * (L - a) * (2 * L - a) / L, lambda x: (L**2 * x**2 - L * x**3 + x**4 / 4) / L) for q in self.loads)
        return l, r

    def fem(self):
        """Magnitudes of the fixed-end moments (left, right)."""
        L = self.L
        l = sum(self._poly(q, lambda a: a * (L - a)**2 / L**2, lambda x: (L**2 * x**2 / 2 - 2 * L * x**3 / 3 + x**4 / 4) / L**2) for q in self.loads)
        r = sum(self._poly(q, lambda a: a**2 * (L - a) / L**2, lambda x: (L * x**3 / 3 - x**4 / 4) / L**2) for q in self.loads)
        return l, r


def _overhang_VM(o, free):
    """Shear and moment along an overhang Span whose free end is on side `free` ('left' or 'right')."""
    x = grid(o.L, o.loads)
    V, M = np.zeros_like(x), np.zeros_like(x)
    if free == "right":                      # the support at x = 0 carries the whole overhang load
        for q in o.loads:
            w, xb = _resultant(q, o.L)
            V, M = V + w, M + w * (x - xb)
    for q in o.loads:
        w, m = _left_VM(q, x, o.L)
        V, M = V - w, M - m
    return x, V, M


class ContinuousBeam:
    """left/right end: 'pin', 'fixed' or a number = known end moment (sagging +, e.g. overhang -15).

    overhang_left/right: a number = load the overhang adds to the end reaction, or a Span(length, loads)
    for the overhang itself (Point, UDL or UVL, positions from its left end). A Span sets the end moment
    and the reaction by statics, and its shear and moment are drawn with the beam.
    """

    def __init__(self, spans, left="pin", right="pin", overhang_left=0.0, overhang_right=0.0):
        ends, oh, self.overhangs = [left, right], [overhang_left, overhang_right], [None, None]
        for k, o in enumerate(oh):
            if isinstance(o, Span):
                if ends[k] != "pin":
                    raise ValueError("give the overhang as a Span or its end moment as a number, not both")
                W = M = 0.0
                for q in o.loads:
                    w, xb = _resultant(q, o.L)
                    W, M = W + w, M - w * (xb if k else o.L - xb)     # hogging at the support
                ends[k], oh[k], self.overhangs[k] = M, W, o
        self.spans, (self.left, self.right) = spans, ends
        self.oh = tuple(oh)
        self.names = [chr(65 + i) for i in range(len(spans) + 1)]

    # --- Clapeyron
    def three_moment(self):
        sp, n = self.spans, len(self.spans)
        A, b = np.zeros((n + 1, n + 1)), np.zeros(n + 1)
        self.equations = []
        for i in range(n + 1):
            end = self.left if i == 0 else self.right if i == n else None
            if end is not None and end != "fixed":
                A[i, i] = 1
                b[i] = 0 if end == "pin" else end
                continue
            c = {}
            if i > 0:
                s = sp[i - 1]
                A[i, i - 1] += s.L / s.I
                A[i, i] += 2 * s.L / s.I
                b[i] -= s.three_moment_terms()[0] / s.I
            if i < n:
                s = sp[i]
                A[i, i + 1] += s.L / s.I
                A[i, i] += 2 * s.L / s.I
                b[i] -= s.three_moment_terms()[1] / s.I
            lhs = " + ".join(f"{A[i, j]:.4g}\\,M_{{{self.names[j]}}}" for j in range(n + 1) if A[i, j])
            self.equations.append((self.names[i], f"{lhs} = {b[i]:.4g}"))
        self.M_sup = np.linalg.solve(A, b)
        return self.M_sup

    # --- Hardy Cross
    def moment_distribution(self, tol=1e-4, maxit=200):
        sp, n = self.spans, len(self.spans)
        cols = [c for i in range(n) for c in (self.names[i] + self.names[i + 1], self.names[i + 1] + self.names[i])]
        hinge = [self.left != "fixed"] + [False] * (n - 1) + [self.right != "fixed"]
        target = {0: 0 if self.left == "pin" else self.left, n: 0 if self.right == "pin" else self.right}
        K = []
        for i, s in enumerate(sp):
            f = 4.0
            if (i == 0 and hinge[0]) ^ (i == n - 1 and hinge[n]):
                f = 3.0
            elif i == 0 and n == 1 and hinge[0] and hinge[n]:
                f = 3.0
            K.append(f * s.I / s.L)
        self.K = K
        DF = np.zeros(2 * n)
        for j in range(1, n):
            t = K[j - 1] + K[j]
            DF[2 * j - 1], DF[2 * j] = K[j - 1] / t, K[j] / t
        self.DF = DF
        m = np.zeros(2 * n)
        for i, s in enumerate(sp):
            l, r = s.fem()
            m[2 * i], m[2 * i + 1] = l, -r         # counter-clockwise +
        rows = [("FEM", m.copy())]
        # release hinged / known-moment ends once, then carry half over
        rel, co = np.zeros(2 * n), np.zeros(2 * n)
        if hinge[0]:
            rel[0] = -target[0] - m[0]
            co[1] += rel[0] / 2
        if hinge[n]:
            rel[-1] = target[n] - m[-1]
            co[-2] += rel[-1] / 2
        if n == 1 and hinge[0] and hinge[n]:
            co[:] = 0
        if rel.any():
            rows += [("Release hinged end", rel.copy()), ("Carry-over", co.copy())]
            m += rel + co
        for _ in range(maxit):
            bal, co = np.zeros(2 * n), np.zeros(2 * n)
            for j in range(1, n):
                u = m[2 * j - 1] + m[2 * j]
                bal[2 * j - 1], bal[2 * j] = -u * DF[2 * j - 1], -u * DF[2 * j]
            if np.abs(bal).max() < tol:
                break
            rows.append(("Balance", bal.copy()))
            m += bal
            for i in range(n):
                if not (i == 0 and hinge[0]):
                    co[2 * i] += bal[2 * i + 1] / 2
                if not (i == n - 1 and hinge[n]):
                    co[2 * i + 1] += bal[2 * i] / 2
            if np.abs(co).max() > tol:
                rows.append(("Carry-over", co.copy()))
            m += co
        rows.append(("**Final**", m.copy()))
        self.mdm_cols, self.mdm_rows = cols, rows
        # sagging + : left end = -m, right end = +m
        self.M_sup = np.array([-m[0]] + [m[2 * i + 1] for i in range(n)])
        return self.M_sup

    # --- shear and moment along the beam
    def diagrams(self):
        X, V, M, off = [], [], [], 0.0
        self.Vends = []
        for i, s in enumerate(self.spans):
            x = grid(s.L, s.loads)
            ss = DeterminateBeam(s.L, s.loads, supports=(0, s.L)) if s.loads else None
            v0, m0 = ss._VM(x) if ss else (0 * x, 0 * x)
            if ss:
                v0[-1] = -ss.RB
            ml, mr = self.M_sup[i], self.M_sup[i + 1]
            v = v0 + (mr - ml) / s.L
            X.append(x + off)
            V.append(v)
            M.append(m0 + ml * (1 - x / s.L) + mr * x / s.L)
            self.Vends.append((v[0], v[-1]))
            off += s.L
        n = len(self.spans)
        self.R = [(self.Vends[i][0] if i < n else 0) - (self.Vends[i - 1][1] if i else 0) for i in range(n + 1)]
        self.R[0] += self.oh[0]
        self.R[n] += self.oh[1]
        self.X, self.V, self.M = X, V, M
        # overhang diagrams, kept apart so X, V, M stay one entry per span
        self.oh_diagrams = [None, None]
        for k, o in enumerate(self.overhangs):
            if o is not None:
                x, v, m = _overhang_VM(o, "right" if k else "left")
                self.oh_diagrams[k] = (x + off if k else x - o.L, v, m)
        return X, V, M


def joint_moments(fem_unbalanced, k_members):
    """Distribute an out-of-balance moment at one joint: {name: k} -> {name: moment}."""
    t = sum(k_members.values())
    return {n: fem_unbalanced * k / t for n, k in k_members.items()}


def extreme(x, y):
    i, j = int(np.argmax(y)), int(np.argmin(y))
    return (x[i], y[i]), (x[j], y[j])
