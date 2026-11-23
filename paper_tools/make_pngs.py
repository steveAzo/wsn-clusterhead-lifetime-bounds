"""PNG copies of the figures for the Word build: figs/*.pdf -> figs/*.png (300 dpi), and the screening-flow
figure (drawn with LaTeX boxes) cropped from main.pdf -> figs/fig_flow.png.
Usage (from Paper5/draft): python -I ../paper_tools/make_pngs.py .
"""
import pathlib
import sys

import pymupdf

d = pathlib.Path(sys.argv[1])
for pdf in sorted((d / "figs").glob("*.pdf")):
    with pymupdf.open(pdf) as doc:
        doc[0].get_pixmap(dpi=300).save(pdf.with_suffix(".png"))

with pymupdf.open(d / "main.pdf") as doc:
    for page in doc:
        top = page.search_for("Europe PMC query, 2021")
        cap = page.search_for("Screening flow of the audit")
        if top and cap:
            r = page.rect
            clip = pymupdf.Rect(r.x0 + 60, top[0].y0 - 8, r.x1 - 60, cap[0].y0 - 4)
            page.get_pixmap(dpi=300, clip=clip).save(d / "figs" / "fig_flow.png")
            break
    else:
        raise SystemExit("screening-flow figure not found in main.pdf")
print("figure PNGs written")
