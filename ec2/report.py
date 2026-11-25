"""Calculation-sheet engine.

`Sheet.calc()` takes ONE formula string. It evaluates that string and typesets the
same string (symbols, then numbers), so the printed step is the calculation itself.
Rows are printed in the usual design-office layout:  Ref | Calculation | Output.
"""
import ast
import json
import math
from pathlib import Path

from IPython.display import Image, Markdown, display

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "images" / "photos"

SEP = r";\; "
GREEK = {"alpha", "beta", "gamma", "delta", "epsilon", "eta", "theta", "mu", "nu", "xi",
         "pi", "rho", "sigma", "tau", "phi", "psi", "omega", "Delta", "Sigma", "zeta"}
ALIAS = {"lam": r"\lambda", "lamda": r"\lambda", "eps": r"\varepsilon"}
OVERRIDE = {"cot_theta": r"\cot\theta", "tan_theta": r"\tan\theta", "K_lim": r"K'",
            "Delta_F_td": r"\Delta F_{td}", "Delta_c_dev": r"\Delta c_{dev}", "Delta_F_d": r"\Delta F_d", "Delta_M": r"\Delta M", "Delta_x": r"\Delta x",
            "K_r": "K_r", "K_phi": r"K_\varphi", "phi_ef": r"\varphi_{ef}",
            "Delta_V_Ed": r"\Delta V_{Ed}", "l_bd": "l_{bd}", "l_b_rqd": "l_{b,rqd}",
            "rho_prime": r"\rho'", "phi_inf": r"\varphi(\infty,t_0)", "phi_RH": r"\varphi_{RH}", "beta_fcm": r"\beta(f_{cm})", "beta_t0": r"\beta(t_0)", "alpha_2c": r"\alpha_2", "curv": "1/r", "curv0": "1/r_0"}
FUNCS = {"sqrt": math.sqrt, "min": min, "max": max, "abs": abs, "sin": math.sin,
         "cos": math.cos, "tan": math.tan, "asin": math.asin, "ceil": math.ceil,
         "pi": math.pi}


def sym(name):
    """Python name -> LaTeX symbol, e.g. A_s_req -> A_{s,req}."""
    if name in OVERRIDE:
        return OVERRIDE[name]
    head, *subs = name.split("_")
    if len(head) > 1 and head[0].isalpha() and head[1:].isdigit():
        subs = [head[1:]] + subs
        head = head[0]
    h = "\\" + head if head in GREEK else ALIAS.get(head, head if len(head) == 1 else rf"\mathrm{{{head}}}")
    out = []
    for x in subs:
        out.append("\\" + x if x in GREEK else ALIAS.get(x, x))
    return h + ("_{" + ",".join(out) + "}" if out else "")


def num(v):
    """Number formatted to design-office precision."""
    if isinstance(v, str):
        return v
    if v == 0:
        return "0"
    a = abs(v)
    if abs(v - round(v)) < 1e-9 and a < 1e7:
        return str(int(round(v)))
    if a >= 1e7 or a < 1e-3:
        m, e = f"{v:.3e}".split("e")
        return rf"{m}\times10^{{{int(e)}}}"
    s = f"{v:.1f}" if a >= 1000 else f"{v:.1f}" if a >= 100 else f"{v:.2f}" if a >= 10 else f"{v:.3f}" if a >= 0.1 else f"{v:.5f}"
    return s.rstrip("0").rstrip(".")


def _plain(v):
    return num(v).replace(r"\times10^{", "×10^").replace("}", "")


# ---- units: forces in N and kN; stress in N/mm² and pressure in kN/m², with the pascal value beside them
PASCALS = {"Pa": 1.0, "N/m²": 1.0, "kPa": 1e3, "kN/m²": 1e3, "MPa": 1e6, "N/mm²": 1e6, "GPa": 1e9, "kN/mm²": 1e9}
SHOWN_AS = {"N/mm²": "MPa", "kN/m²": "Pa"}


def convert(value, unit, to):
    """Convert a stress or pressure, e.g. convert(200, "kN/m²", "MPa") -> 0.2"""
    return value * PASCALS[unit] / PASCALS[to]


def _pascal(unit, *values, op=""):
    """'(= 17 MPa)' for a stress or pressure unit, otherwise ''."""
    to = SHOWN_AS.get(unit)
    if not to:
        return ""
    shown = [convert(v, unit, to) for v in values]
    return f"<br><small>(= {f' {op} '.join(_plain(round(v) if to == 'Pa' else v) for v in shown)} {to})</small>"


class _Tex(ast.NodeVisitor):
    PREC = {ast.Add: 1, ast.Sub: 1, ast.Mult: 2, ast.Div: 2, ast.Pow: 4}

    def __init__(self, env=None):
        self.env = env          # None -> symbols, dict -> numbers

    def tex(self, n, parent=0):
        if isinstance(n, ast.Expression):
            return self.tex(n.body)
        if isinstance(n, ast.Constant):
            v = n.value
            if isinstance(v, float) and v >= 1000 and math.log10(v).is_integer():
                return rf"10^{{{int(math.log10(v))}}}"
            return num(v)
        if isinstance(n, ast.Name):
            if n.id == "pi":
                return r"\pi"
            if self.env is None:
                return sym(n.id)
            v = self.env[n.id]
            t = num(v)
            return f"({t})" if v < 0 or (parent >= 4 and r"\times" in t) else t
        if isinstance(n, ast.UnaryOp):
            return "-" + self.tex(n.operand, 2)
        if isinstance(n, ast.BinOp):
            p = self.PREC[type(n.op)]
            if isinstance(n.op, ast.Div):
                return rf"\dfrac{{{self.tex(n.left)}}}{{{self.tex(n.right)}}}"
            if isinstance(n.op, ast.Pow):
                compound = isinstance(n.left, (ast.BinOp, ast.UnaryOp))
                b = self.tex(n.left, 4)
                b = rf"\left({self.tex(n.left)}\right)" if compound else b
                if isinstance(n.right, ast.BinOp) and isinstance(n.right.op, ast.Div):
                    e = f"{self.tex(n.right.left)}/{self.tex(n.right.right)}"
                else:
                    e = self.tex(n.right)
                return f"{b}^{{{e}}}"
            op = {ast.Add: "+", ast.Sub: "-"}.get(type(n.op))
            if op is None:
                l, r = self.tex(n.left, p), self.tex(n.right, p)
                op = r"\,"
                if r[0].isdigit() or self.env is not None or r.startswith("10^") \
                        or l.endswith("}") and l.rfind("10^{") > l.rfind(" "):
                    op = r"\times "
                s = l + op + r
            else:
                s = self.tex(n.left, p) + " " + op + " " + self.tex(n.right, p + (op == "-"))
            return rf"\left({s}\right)" if p < parent else s
        if isinstance(n, ast.Call):
            f = n.func.id
            a = [self.tex(x) for x in n.args]
            if f == "sqrt":
                return rf"\sqrt{{{a[0]}}}"
            if f == "abs":
                return rf"\left\vert {a[0]}\right\vert "
            if f in ("min", "max"):
                return rf"\{f}\left\{{{SEP.join(a)}\right\}}"
            if f == "asin":
                return rf"\sin^{{-1}}\!\left({a[0]}\right)"
            return rf"\{f if f != 'ceil' else 'mathrm{ceil}'}\left({a[0]}\right)"
        raise ValueError(ast.dump(n))


class Sheet:
    """One calculation sheet: holds values, prints rows, records every check."""

    def __init__(self, title, project="EC2 design guide", element=""):
        self.v, self.units, self.rows, self.checks = {}, {}, [], []
        self.part = element or title
        self._shown = {}        # rows already printed with the same value are not repeated
        display(Markdown(f"## {title}\n\n*Project:* {project} &nbsp;|&nbsp; *Element:* {element or title}"))

    def __getitem__(self, k):
        return self.v[k]

    def __setitem__(self, k, val):
        self.v[k] = val

    def _row(self, ref, calc, out=""):
        self.rows.append((ref, calc, out))

    def let(self, name, value, unit="", text="", ref=""):
        """Record an input / looked-up value."""
        self.v[name], self.units[name] = value, unit
        if self._shown.get(name) == num(value):
            return value
        self._shown[name] = num(value)
        t = f"{text}: " if text else ""
        self._row(ref, f"{t}${sym(name)}$", f"${sym(name)} = {num(value)}$ {unit}{_pascal(unit, value)}")
        return value

    def calc(self, name, expr, unit="", ref="", text=""):
        """Evaluate AND typeset `expr` (single source of truth)."""
        tree = ast.parse(expr, mode="eval")
        val = float(eval(compile(tree, "calc", "eval"), {"__builtins__": {}}, {**FUNCS, **self.v}))
        self.v[name], self.units[name] = val, unit
        a, b = _Tex().tex(tree), _Tex(self.v).tex(tree)
        if self._shown.get(name) == num(val) and self._shown.get("=" + name) == b:
            return val
        self._shown[name], self._shown["=" + name] = num(val), b
        t = f"{text}<br>" if text else ""
        second = "" if b == num(val) else f"<br>$\\quad = {b}$"
        self._row(ref, f"{t}${sym(name)} = {a}${second}", f"$\\mathbf{{{sym(name)} = {num(val)}}}$ {unit}{_pascal(unit, val)}".rstrip())
        return val

    def check(self, left, op, right, text, ref="", right_expr=None):
        """Record a pass/fail check. left/right are names or numbers."""
        def val(x):
            return self.v[x] if isinstance(x, str) else float(x)
        a, b = val(left), val(right)
        ok = a <= b * (1 + 1e-9) if op == "<=" else a >= b * (1 - 1e-9)
        u = (a / b if op == "<=" else b / a) if a and b else 0.0
        ls = f"{sym(left)} = {num(a)}" if isinstance(left, str) else num(a)
        rs = f"{sym(right)} = {num(b)}" if isinstance(right, str) else num(b)
        unit = self.units.get(left, "") if isinstance(left, str) else ""
        o = r"\le" if op == "<=" else r"\ge"
        self._row(ref, f"**Check:** {text}<br>${ls} {o} {rs}$ {unit}{_pascal(unit, a, b, op='≤' if op == '<=' else '≥')}",
                  ("✅ **PASS**" if ok else "❌ **FAIL**") + f"<br>ratio {u:.2f}")
        self.checks.append((self.part, text, ok, u, ref))
        return ok

    def note(self, text, ref=""):
        self._row(ref, text, "")

    def verdict(self, ok, text, ref=""):
        self._row(ref, f"**Check:** {text}", "✅ **PASS**" if ok else "❌ **FAIL**")
        self.checks.append((self.part, text, bool(ok), float("nan"), ref))

    def provide(self, text, ref=""):
        self._row(ref, f"**PROVIDE: {text}**", f"🟦 **{text}**")

    def show(self, heading=""):
        """Print the rows collected since the last call."""
        if not self.rows:
            return
        h = f"### {heading}\n\n" if heading else ""
        body = "\n".join(f"| {r} | {c} | {o} |" for r, c, o in self.rows)
        self.rows = []
        display(Markdown(f"{h}| Reference | Calculation | Output |\n|:--|:--|:--|\n{body}\n"))

    def summary(self, title="Summary of checks"):
        self.show()
        body = "\n".join(f"| {t} | {r} | {'–' if u != u else f'{u:.2f}'} | {'✅ PASS' if ok else '❌ FAIL'} |"
                         for _, t, ok, u, r in self.checks)
        n = sum(1 for c in self.checks if not c[2])
        line = "**All checks pass.**" if n == 0 else f"**{n} check(s) FAIL – revise the design.**"
        display(Markdown(f"### {title}\n\n| Check | Reference | Ratio | Result |\n|:--|:--|:-:|:--|\n{body}\n\n{line}"))


def table(rows, header, caption=""):
    h = "| " + " | ".join(header) + " |\n|" + "|".join([":--"] + [":-:"] * (len(header) - 1)) + "|\n"
    b = "\n".join("| " + " | ".join(_plain(x) if isinstance(x, (int, float)) else str(x) for x in r) + " |" for r in rows)
    display(Markdown((f"**{caption}**\n\n" if caption else "") + h + b + "\n"))


def photo(key, caption, width=560):
    """Show a site photo with its licence credit."""
    cred = {c["file"]: c for c in json.loads((PHOTOS / "credits.json").read_text())}[f"{key}.jpg"]
    display(Image(filename=str(PHOTOS / f"{key}.jpg"), width=width))
    display(Markdown(f"*{caption}* <br><small>Photo: {cred['author']}, "
                     f"[{cred['licence']}]({cred['licence_url'] or cred['source']}), "
                     f"via [Wikimedia Commons]({cred['source']}).</small>"))


def mdm_table(cb, caption="Moment distribution (kN·m, counter-clockwise positive)"):
    """Print the Hardy Cross table of a ContinuousBeam after moment_distribution()."""
    hd = ["Step"] + list(cb.mdm_cols)
    df = [f"{x:.3f}" if x else "–" for x in cb.DF]
    rows = [["Distribution factor"] + df]
    shown, tail = cb.mdm_rows, None
    if len(shown) > 13:
        shown = cb.mdm_rows[:10] + [("… (further cycles)", None)] + cb.mdm_rows[-1:]
    for n, r in shown:
        rows.append([n] + (["…"] * len(df) if r is None else [f"**{x:.2f}**" if "Final" in n else (f"{x:.2f}" if abs(x) > 5e-3 else "") for x in r]))
    table(rows, hd, caption)
