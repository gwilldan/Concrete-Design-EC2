# Make your own notebook

Design or check any component, outside the example building, by calling the project's functions on a new `Sheet`.
The example below designs a 6 m simply supported beam.

[Back to Start Here](../00_Start_Here/0.1_Project_brief_and_references.ipynb) · Other ways: [Use a stand-alone sheet](Use_a_standalone_sheet.md) · [Redesign the example building](Redesign_the_example_building.md)

## 1. Create the notebook

1. Create a folder in the project, for example `07_My_Designs`. The name must start with `0`, or the PDF tool will not find it.
2. Create a notebook in it, for example `7.1_My_beam.ipynb`.
3. Choose the `.venv` kernel.

## 2. Load everything

```python
import sys; sys.path.insert(0, '..')
from ec2.setup import *
```

## 3. Enter your inputs

```python
# INPUTS
L, gk, qk = 6.0, 18.0, 12.0             # span (m), characteristic loads (kN/m, gk includes self-weight)
b, h = 300, 500                         # mm
fck, fyk = 30, 500                      # N/mm²
n, phi, link, spacing = 4, 20, 8, 250   # bottom bars, bar size, link size, link spacing (mm)
```

## 4. Create the sheet and analyse

```python
s = Sheet("My beam", element=f"{b} x {h}, span {L} m")
D.materials(s, fck, fyk, UK)

s.let("L", L, "m", "Span"); s.let("g_k", gk, "kN/m"); s.let("q_k", qk, "kN/m"); s.let("h", h, "mm")
s.calc("w_Ed", "1.35*g_k + 1.5*q_k", "kN/m", "EN 1990 Exp. (6.10)")
s.calc("M_max", "w_Ed*L**2/8", "kN·m", "Statics")
s.calc("V_max", "w_Ed*L/2", "kN", "Statics")
s.show("Loads and analysis")
P.determinate(DeterminateBeam(L, [UDL(s["w_Ed"])], supports=(0, L)))
```

## 5. Design the bending steel

```python
c = D.cover(s, "XC1", phi, link)
s.calc("d", "h - c_nom - phi_link - phi/2", "mm", "", "Effective depth"); s.show("Effective depth")
d = s["d"]

As, _ = D.flexure(s, s["M_max"], b, d)         # steel needed
As_prov = D.beam_bars(s, n, phi, b, c, link)   # bars you chose
s.show("Bending")
```

## 6. Check the rest, draw and summarise

```python
D.shear_beam(s, s["V_max"], s["V_max"] - s["w_Ed"]*d/1000, b, d, As_prov, link, 2, spacing)
s.show("Shear")
D.deflection(s, L*1000, d, b, As, As_prov, "simply supported")
s.show("Deflection")
P.beam_section(b, h, c, link, (2, 12), (n, phi), "My beam")
s.summary()
```

Shear is measured from the support centre-line here, which is conservative.

## 7. Run it and revise

Run all cells and read the summary table. Change the bars until every check passes:

| Bars | Steel needed | Steel provided | Result |
|:--|:--|:--|:--|
| 3H20 | 1064 mm² | 942 mm² | ❌ area too small |
| 4H20 | 1064 mm² | 1257 mm² | ✅ all checks pass |

## 8. Print it without code

Save the notebook, then run:

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python tools/export_sheets.py 7.1
```

The PDF goes into `calc_sheets`.

## The pattern

| Call | What it does |
|:--|:--|
| `s.let(name, value, unit, text, ref)` | Stores an input |
| `s.calc(name, formula, unit, ref, text)` | Works out a formula and shows the working |
| `s.check(left, "<=", right, text, ref)` | Records a pass or fail. Use only `<=` or `>=` |
| `D.…(s, …)` | Adds a ready-made design step |
| `s.show("Title")` | Prints the steps so far |
| `s.summary()` | Lists every check |

Read a value back with `s["name"]`. Type a name with a question mark, such as `D.flexure?`, to see what it needs.

| Letter | Contains |
|:--|:--|
| `D` | Materials, loads, cover, bending, shear, deflection, cracking, anchorage, fire |
| `C` | Columns |
| `F` | Pad footings |
| `SL` | Slab coefficients |
| `P` | Diagrams and drawings |

## Before you rely on it

- **This example is not a complete design.** It leaves out fire, cracking and anchorage. [Notebook 4.3](../04_Beam_Design/4.3_Simply_supported_doubly_reinforced_beam.ipynb) includes them, so copy those lines when you need them.
- Values keep their names. A second `D.flexure` replaces `A_s_req`, so save the first result if you need it later.
- Units are labels. Nothing converts them for you: spans in m, sections in mm, forces in kN, stress in N/mm².
