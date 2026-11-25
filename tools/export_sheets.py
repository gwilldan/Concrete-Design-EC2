#!/usr/bin/env python
"""Print notebooks as calculation sheets WITHOUT code:  calc_sheets/*.pdf

usage: export_sheets.py [text ...] [--run] [--html-only]
  text         only notebooks whose path contains this text
  --run        re-execute the notebooks first
  --html-only  write HTML instead of PDF
The HTML is an intermediate file: it is deleted once its PDF exists.
PDF uses headless Chrome / Edge / Chromium. If none is found, the HTML is kept so it can be printed by hand.
MathJax is loaded from its CDN, so the first render needs an internet connection.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "calc_sheets"
CSS = """<style>
@page{size:A4;margin:14mm 13mm 16mm 13mm;@bottom-right{content:counter(page) " / " counter(pages);font:8pt sans-serif}}
body{max-width:1000px;margin:0 auto!important;padding:0 16px!important;background:#fff!important}
.jp-Cell{padding:0!important;margin:0 0 6px!important}
.jp-InputPrompt,.jp-OutputPrompt,.jp-InputCollapser,.jp-OutputCollapser{display:none!important}
.jp-RenderedMarkdown,.jp-RenderedHTMLCommon{padding:0!important;font-size:13px!important}
.jp-RenderedHTMLCommon table{width:100%!important;margin:4px 0 10px!important;border-collapse:collapse;font-size:12.5px!important;table-layout:auto}
.jp-RenderedHTMLCommon th,.jp-RenderedHTMLCommon td{border:1px solid #cfcdc7!important;padding:4px 8px!important;vertical-align:middle;text-align:left!important}
.jp-RenderedHTMLCommon thead th{background:#eceae4!important}
.jp-RenderedHTMLCommon tr{page-break-inside:avoid;background:#fff!important}
.jp-OutputArea-output{overflow:visible!important}
.jp-RenderedImage img{max-width:100%!important;max-height:215mm}
.jp-RenderedImage{page-break-inside:avoid}
.jp-RenderedHTMLCommon table:has(thead th:nth-child(3):last-child){table-layout:fixed}
.jp-RenderedHTMLCommon table:has(thead th:nth-child(3):last-child) th:nth-child(1){width:17%}
.jp-RenderedHTMLCommon table:has(thead th:nth-child(3):last-child) th:nth-child(3){width:22%}
td .MathJax_CHTML,td .MathJax{font-size:101%!important;padding:2px 0!important;display:inline-block!important}
.jp-RenderedHTMLCommon table:has(thead th:nth-child(4):last-child) td:last-child{white-space:nowrap}
h1,h2,h3{page-break-after:avoid;break-after:avoid;margin-top:14px!important}
.jp-Cell,.jp-Cell-outputWrapper,.jp-Cell-outputArea,.jp-OutputArea,.jp-OutputArea-child,.jp-OutputArea-output,.jp-RenderedMarkdown{display:block!important;page-break-inside:auto!important;break-inside:auto!important}
.jp-RenderedHTMLCommon table{page-break-inside:auto!important;break-inside:auto!important}
.jp-RenderedMarkdown p{margin:4px 0!important}
</style></head>"""
BROWSERS = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "google-chrome", "chromium", "chromium-browser", "chrome", "msedge"]


def browser():
    for b in BROWSERS:
        p = b if Path(b).exists() else shutil.which(b)
        if p:
            return p


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    run, html_only = "--run" in sys.argv, "--html-only" in sys.argv
    books = [p for p in sorted(ROOT.glob("0*/*.ipynb")) if not args or any(a in str(p.relative_to(ROOT)) for a in args)]
    if not books:
        sys.exit("No notebook matches.")
    OUT.mkdir(exist_ok=True)
    exp = HTMLExporter(template_name="lab", exclude_input=True, exclude_input_prompt=True, exclude_output_prompt=True, embed_images=True)
    chrome = None if html_only else browser()
    for p in books:
        nb = nbformat.read(p, 4)
        if run:
            ExecutePreprocessor(timeout=300).preprocess(nb, {"metadata": {"path": str(p.parent)}})
            nbformat.write(nb, p)
        nb.cells = [c for c in nb.cells if "input-guide" not in c.metadata.get("tags", [])]      # guides are for editing, not printing
        html, _ = exp.from_notebook_node(nb, {"metadata": {"name": p.stem.replace("_", " ")}})
        h = OUT / f"{p.stem}.html"
        h.write_text(html.replace("</head>", CSS, 1))
        msg = h.name
        if chrome:
            pdf = h.with_suffix(".pdf")
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=45000",
                            f"--print-to-pdf={pdf}", h.as_uri()], capture_output=True, timeout=180)
            if pdf.exists() and pdf.stat().st_mtime >= h.stat().st_mtime:
                h.unlink()
                msg = pdf.name
            else:
                msg += "  (PDF failed: HTML kept, open it and print it)"
        print(msg)
    if not html_only and not chrome:
        print("No Chrome/Edge/Chromium found: open the HTML files and use Print > Save as PDF.")


if __name__ == "__main__":
    main()
