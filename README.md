# Structural design to Eurocode 2 in Python

A programmatic calculation guide: **analysis → slab → beam → column → pad footing** for one small RC office building,
plus stand-alone examples. Every row prints reference, formula with numbers, and result.

## Start

Tested on Python 3.12. Run everything inside the project folder.

**1. Create the environment (once)**

macOS and Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**2. Activate it (every new terminal)**

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
```

The prompt then starts with the environment name. Every command below assumes the environment is active. Use `deactivate` to leave it.

**3. Open the notebooks**

```bash
jupyter lab                      # or open the .ipynb files in VS Code and pick the .venv kernel
```

Begin with `00_Start_Here/0.1_Project_brief_and_references.ipynb`.

| Folder | Content |
|:--|:--|
| `00_Start_Here` | Project brief, references, scope and limits |
| `01_Structural_Analysis` | Determinate beams; three-moment equation; moment distribution |
| `02_Concrete_Section_Design_Theory` | Materials, loads, cover, fire; bending; shear; serviceability, bond, detailing |
| `03_Slab_Design` | One-way simply supported, one-way continuous, two-way |
| `04_Beam_Design` | Slab-to-beam load transfer; continuous flanged beam; doubly reinforced beam |
| `05_Column_Design` | Column types and take-down; short; slender; biaxial |
| `06_Pad_Foundation_Design` | Internal column pad; pad with moment |
| `ec2/` | Calculation library. `project.py` = all project inputs; `codes.py` = code tables and national parameters |
| `tests/` | Checks against published results |
| `Docs/` | Guides: [use a stand-alone sheet](Docs/Use_a_standalone_sheet.md), [make your own notebook](Docs/Make_your_own_notebook.md), [redesign the example building](Docs/Redesign_the_example_building.md) |
| `calc_sheets/` | Printed sheets without code (PDF) |
| `images/photos/` | Site photos with licences in `credits.json` |
| `LICENSE` | CC BY-NC 4.0, non-commercial use only |

## Print without code

```bash
python tools/export_sheets.py            # everything, no code, PDF
python tools/export_sheets.py 04_Beam    # one section
python tools/export_sheets.py --run      # re-run the notebooks first
```

PDF needs Chrome, Edge or Chromium. Formulas are drawn by MathJax from its CDN, so the first print needs internet.

## Change the design

Each input cell has an **Input guide** above it: every name, its unit and what it expects. The guide for `BRIEF` is in Notebook 0.1.

- Whole building: edit `BRIEF` in `ec2/project.py`, then `tools/export_sheets.py --run`.
- UK or recommended values: `BRIEF["ndp"] = UK` or `EN`.
- One example: edit its cell marked `# INPUTS`, then run the cells below it.
- A failed check prints ❌ and is listed in the summary table at the end of the sheet.

## Lock the calculation cells

```bash
python tools/lock.py            # lock
python tools/lock.py --off      # unlock
python tools/lock.py --status   # show
```

Save and close the notebooks first. In JupyterLab, one cell can be changed in the Property Inspector (two-gears icon), **Common Tools**, **Editable**.

## Check the library

```bash
python -m pytest -q
```

Basis: EN 1992-1-1:2004 (first generation) with the UK National Annex (2009 amendment), EN 1992-1-2, EN 1990, EN 1991-1-1, EN 1997-1.
BS 8110-1:1997 (withdrawn) is used only where EC2 gives no rule: slab coefficients, corner steel, column moments, z ≤ 0.95d, one slender-column term.
This is a learning aid. A competent engineer must check any real calculation.

## Contributing

Corrections, new examples and new checks are welcome. By submitting one, you confirm it is yours to share and license it under the project license.

**Set up**

1. Copy or fork the project and work on your own copy.
2. Create the environment as shown in [Start](#start).
3. Run `python -m pytest -q`. Every test should pass before you change anything.

**Rules**

1. **Cite what you have read.** Every formula, factor and limit needs a clause, table or page reference. Do not cite a document from memory.
2. **Show the working.** Put formulas through `Sheet.calc`, so the printed step is the one that was evaluated. Use `let` for inputs and looked-up values, and `check` (only `<=` or `>=`) for limits.
3. **Keep inputs separate from code values.** Project inputs go in `ec2/project.py` or at the top of a notebook. National values and code tables go in `ec2/codes.py`.
4. **State assumptions** in the sheet, and say which side is conservative.
5. **Units.** Forces in kN or N, stress in N/mm², pressure in kN/m². Lengths in m for spans and mm for sections.
6. **Add a test** in `tests/test_benchmarks.py` for new calculations, against a published result, a hand calculation or equilibrium.
7. **Do not add copies of standards or books.** Short citations and the values needed for a check are enough.
8. **Photos** need a license that allows sharing, and an entry in `images/photos/credits.json`.

**Before you submit**

```bash
python -m pytest -q
python tools/export_sheets.py --run
```

Check that no sheet shows ❌ unless the example is meant to fail, and reload open notebooks afterwards.
Describe what you changed, why, and which reference supports it. If you found an error, include the inputs, the printed result and the result you expected.

**Useful first contributions**

- A second published worked example for any check.
- National values for another country in `ec2/codes.py`.
- Replacing the 1.35 and 1.5 typed in some notebooks with the values in `ec2/codes.py`.
- Making `bays_x`, `bays_y` and `category` in `BRIEF` drive the analysis.
- New members: staircases, flat slabs, retaining walls, combined footings.

## License

Copyright (c) 2026 GODSWILL DANIEL EFFIONG

This project is licensed under [Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](LICENSE).
You may share and adapt it if you give credit and do not use it commercially.

The site photos keep their own Creative Commons licenses (`images/photos/credits.json`).
The cited standards belong to their publishers.
