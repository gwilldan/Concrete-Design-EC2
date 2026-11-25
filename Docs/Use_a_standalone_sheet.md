# Use a stand-alone sheet

The quickest way to design or check one component: copy a ready-made notebook, change its input cell and run it.

[Back to Start Here](../00_Start_Here/0.1_Project_brief_and_references.ipynb) · Other ways: [Make your own notebook](Make_your_own_notebook.md) · [Redesign the example building](Redesign_the_example_building.md)

## 1. Choose the sheet

| Component | Notebook | Complete design? |
|:--|:--|:-:|
| Determinate beam: moments and shears | [1.1](../01_Structural_Analysis/1.1_Determinate_beams.ipynb) | analysis only |
| Continuous beam: moments and shears | [1.2](../01_Structural_Analysis/1.2_Indeterminate_three_moment_equation.ipynb) or [1.3](../01_Structural_Analysis/1.3_Indeterminate_moment_distribution.ipynb) | analysis only |
| One section in bending | [2.2](../02_Concrete_Section_Design_Theory/2.2_Bending_theory.ipynb) | bending only |
| One section in shear | [2.3](../02_Concrete_Section_Design_Theory/2.3_Shear_theory.ipynb) | shear only |
| One-way slab, simply supported | [3.1](../03_Slab_Design/3.1_One_way_slab_simply_supported.ipynb) | yes |
| One-way slab, continuous | [3.2](../03_Slab_Design/3.2_One_way_slab_continuous.ipynb) | yes |
| Simply supported beam | [4.3](../04_Beam_Design/4.3_Simply_supported_doubly_reinforced_beam.ipynb) | yes |
| Braced column, bending about one axis | [5.3](../05_Column_Design/5.3_Slender_column.ipynb) | yes |

## 2. Copy it

1. Create a folder in the project, for example `07_My_Designs`. The name must start with `0`.
2. Copy the notebook into it and rename it, for example `7.2_My_slab.ipynb`.

Working on a copy keeps the original intact.

## 3. Change the inputs

Find the cell that starts with `# INPUTS`. The **Input guide** above it lists every name, its unit and what it expects.

Change only the values. The calculation cells are locked.

## 4. Run and read

Choose **Run All**. Read the summary table at the end: a ratio above 1.00 means ❌.

## 5. Revise until it passes

Example: sheet 3.1 with a 4.2 m clear span on 200 mm walls.

| Slab | Main bars | Steel needed | Steel provided | Result |
|:--|:--|:--|:--|:--|
| 150 mm | H12 @ 200 | 627 mm²/m | 565 mm²/m | ❌ steel, ❌ deflection (2.06) |
| 150 mm | H12 @ 150 | 627 mm²/m | 754 mm²/m | ❌ deflection (1.54) |
| 175 mm | H12 @ 200 | 548 mm²/m | 565 mm²/m | ❌ deflection (1.06) |
| 175 mm | H12 @ 150 | 548 mm²/m | 754 mm²/m | ✅ all checks pass |

Extra steel helps deflection as well as strength, up to the cap in the UK National Annex.

## 6. Print it

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python tools/export_sheets.py 7.2
```

## Good to know

- Fixed examples from NPTEL in 1.2 and 1.3 have no input cell. They must match published answers.
- UK or EN values come from `ndp` in `ec2/project.py`.
- 1.1 to 1.3 analyse the loads you give them. Enter ULS loads (1.35G + 1.5Q) when the result is for strength design.
- 5.3: make the larger end moment positive.
- To change a calculation, unlock the cell first: Property Inspector (two-gears icon), **Common Tools**, **Editable**.
