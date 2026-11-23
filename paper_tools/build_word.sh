#!/bin/sh
# Build the Word copy of the Paper 5 draft from the same LaTeX source as the PDF (tools adapted from Paper 4).
# Usage, from Paper5/: sh paper_tools/build_word.sh v0.1     -> draft/deliverables/Paper5_draft_v0.1.{docx,pdf}
# Harvard (author-year) references, as in the PDF (elsarticle-harv): elsevier-harvard.csl.
set -e
VER=${1:?version, e.g. v0.1}
cd draft
mkdir -p build deliverables
latexmk -pdf -interaction=nonstopmode -silent main.tex > /dev/null 2>&1 || true
if grep -q "^!\|undefined\|multiply defined" main.log; then grep -n "^!\|undefined\|multiply defined" main.log; exit 1; fi
python -I ../paper_tools/make_pngs.py .
python -I -W ignore ../paper_tools/make_word.py . word_main.tex
pandoc word_main.tex -f latex -t docx --citeproc --bibliography=refs.bib --csl=elsevier-harvard.csl \
  --resource-path=. -M reference-section-title=References -o build/word_raw.docx
NEQ=$(python -I -c 'import json; print(json.load(open("word_main.tex.json"))["equations"])')
DATE=$(python -I -c 'import datetime; d = datetime.date.today(); print(d.strftime("%B ") + str(d.day) + d.strftime(", %Y"))')
python -I ../paper_tools/fix_word.py build/word_raw.docx "deliverables/Paper5_draft_$VER.docx" "$NEQ" \
  "Journal of Network and Computer Applications" "$DATE"
cp main.pdf "deliverables/Paper5_draft_$VER.pdf"
rm -f word_main.tex word_main.tex.json build/word_raw.docx
ls -la deliverables
