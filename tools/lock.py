#!/usr/bin/env python
"""Lock or unlock the calculation cells ("editable": false in the cell metadata).

usage: lock.py            lock every calculation cell
       lock.py --off      unlock them
       lock.py --status   show what is locked, change nothing

Save and close the notebooks first, or an open tab can save the old state back.
JupyterLab respects the lock. It stops accidental typing only; it is not security.
"""
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parent.parent


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "--on"
    if arg not in ("--on", "--off", "--status"):
        sys.exit(__doc__)
    total = locked = 0
    for p in sorted(ROOT.glob("0*/*.ipynb")):
        nb = nbformat.read(p, 4)
        cells = [c for c in nb.cells if "calculation" in c.metadata.get("tags", [])]
        before = sum(c.metadata.get("editable") is False for c in cells)
        if arg == "--on":
            for c in cells:
                c.metadata["editable"] = False
        elif arg == "--off":
            for c in cells:
                c.metadata.pop("editable", None)
        after = sum(c.metadata.get("editable") is False for c in cells)
        if after != before:
            nbformat.write(nb, p)
        if cells:
            print(f"{after:3d} of {len(cells):2d} locked  {p.relative_to(ROOT)}")
        total, locked = total + len(cells), locked + after
    print(f"{locked} of {total} calculation cells locked")


if __name__ == "__main__":
    main()
