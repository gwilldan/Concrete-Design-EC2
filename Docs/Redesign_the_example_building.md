# Redesign the example building

Change the building's inputs once, and the slab, beams, columns and pads are recalculated with the new loads.

[Back to Start Here](../00_Start_Here/0.1_Project_brief_and_references.ipynb) · Other ways: [Use a stand-alone sheet](Use_a_standalone_sheet.md) · [Make your own notebook](Make_your_own_notebook.md)

## 1. What you can change

Open `ec2/project.py` and edit the values in `BRIEF`. Notebook 0.1 has an **Input guide** for every name.

| Change | Names |
|:--|:--|
| Geometry | `lx_bay`, `ly_bay`, `storey`, `levels` |
| Sizes | `h_slab`, `beam`, `col` |
| Loads | `finishes`, `qk`, `partitions`, `facade` |
| Materials and durability | `fck`, `fyk`, `exposure`, `exposure_ground`, `fire` |
| Ground | `bearing`, `overburden` |
| National values | `ndp` |

**Fixed:** three bays each way, braced frame, `lx_bay` at least `ly_bay` with a ratio up to 2, square columns.

## 2. Edit, restart, run

1. Edit `BRIEF` and save the file.
2. In each notebook, restart the kernel and run all cells. Without the restart, Python keeps the old values.

Or do everything at once, with the notebooks closed:

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python tools/export_sheets.py --run
```

## 3. Follow the load path

| Order | Notebook | Receives |
|:--|:--|:--|
| 1 | [3.3 Two-way slab](../03_Slab_Design/3.3_Two_way_slab.ipynb) | Area loads |
| 2 | [4.1 Slab to beam loads](../04_Beam_Design/4.1_Load_transfer_slab_to_beam.ipynb) | Slab shears |
| 3 | [4.2 Continuous beam](../04_Beam_Design/4.2_Continuous_beam_design.ipynb) | Beam loads |
| 4 | [5.1 Column loads](../05_Column_Design/5.1_Column_types_and_load_transfer.ipynb) | Beam reactions |
| 5 | [5.2 Short columns](../05_Column_Design/5.2_Short_columns_B2_and_B1.ipynb), [5.4 Corner column](../05_Column_Design/5.4_Biaxial_corner_column_A1.ipynb) | Column loads and moments |
| 6 | [6.1](../06_Pad_Foundation_Design/6.1_Pad_under_internal_column_B2.ipynb), [6.2](../06_Pad_Foundation_Design/6.2_Pad_with_moment_edge_column_B1.ipynb) Pads | Column loads |

You can run them in any order, because each one recalculates what it needs. This order is the easiest to follow.

## 4. Revise what fails

`BRIEF` does not choose bars or pad sizes. They are in each notebook's `# INPUTS` cell.

**Example A: one more storey.** Change `levels=3` to `levels=4`.

| Notebook | Result | Fix | After the fix |
|:--|:--|:--|:--|
| 3.3, 4.2 | ✅ | none | ✅ |
| 5.2, 5.4 columns | ✅ | none | ✅ |
| 6.1 pad | ❌ bearing 1.23, ❌ steel 1.01 | `B=3100, hp=700` | ✅ |
| 6.2 pad | ❌ bearing 1.19 | `B=2300` | ✅ |

**Example B: heavier use.** Change `qk=3.0` to `qk=4.0`.

| Notebook | Result | What to change |
|:--|:--|:--|
| 3.3 slab | ❌ steel over the short-span support, 1.01 | closer bars in `bars` |
| 4.2 beam | ❌ top steel at support B, 1.03 | more or larger bars (`n_B`, `phi`) |
| 5.2, 5.4 columns | ✅ | none |
| 6.1 pad | ❌ bearing 1.03 | larger `B` |
| 6.2 pad | ✅ | none |

## 5. Print it

```bash
python tools/export_sheets.py            # every sheet, as last run
python tools/export_sheets.py 06_Pad     # one section
```

## Good to know

- Only panel P1, Beam B, columns B2, B1 and A1, and the pads of B2 and B1 are designed. Other members need their own sheets.
- `category` sets ψ₂ only. Change `qk` as well.
- If you change the slab bars in 3.3 over Beam B, update `slab_top` and `slab_bot` in 4.2.
- Keep a copy of the original `BRIEF`, or commit it to Git, before a big change.
