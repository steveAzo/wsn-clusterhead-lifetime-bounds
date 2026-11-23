#!/bin/sh
# E14 (second review): re-planning interval sensitivity of the bound schedule, and CC2420 edge under realistic
# energy reporting. Layout 0, serial (3.7 GB RAM), resumable: lines already in the results file are skipped.
# R = 50 for FO centre / CC2420 edge (exact reports) already exists in e10_lp_protocol.txt.
cd "$(dirname "$0")/../.." || exit 1
OUT=results/e14_replan.txt
one() {  # model sink R extra-args...
  m=$1; s=$2; R=$3; shift 3
  if [ $# -gt 0 ]; then nz=0.1; key="LPSCHED $m $s seed 0 replan $R noise $nz report-cost delay miss 0.2:"
  else nz=0.0; key="LPSCHED $m $s seed 0 replan $R noise $nz:"; fi
  grep -qF "$key" $OUT 2>/dev/null && return
  t0=$(date +%s)
  python -I src/scoping/e10_lp_protocol.py $m $s 0 --replan $R --noise $nz --iters 600 --reiters 20 "$@" > results/e14_last.log 2>&1
  t1=$(date +%s)
  if grep -q "^LPSCHED" results/e14_last.log; then
    echo "$(grep '^LPSCHED' results/e14_last.log) wall=$((t1 - t0))s" >> $OUT
  else
    echo "FAIL $m $s R=$R $*" >> $OUT; tail -3 results/e14_last.log >> $OUT
  fi
}
# 1) exact reports, interval sweep
for m_s in "FO centre" "CC2420 edge"; do for R in 10 25 100 200; do one $m_s $R; done; done
# 2) CC2420 edge, realistic reporting at R = 50 (report cost only, then report cost + delay + 20% loss + 10% noise)
grep -qF "LPSCHED CC2420 edge seed 0 replan 50 noise 0.0 report-cost:" $OUT 2>/dev/null || {
  python -I src/scoping/e10_lp_protocol.py CC2420 edge 0 --replan 50 --noise 0.0 --iters 600 --reiters 20 --report-cost > results/e14_last.log 2>&1
  grep "^LPSCHED" results/e14_last.log >> $OUT || echo "FAIL CC2420 edge report-cost" >> $OUT; }
one CC2420 edge 50 --report-cost --delay --miss 0.2
# 3) realistic reporting, interval sweep (the report cost grows with re-plan frequency)
for m_s in "FO centre" "CC2420 edge"; do for R in 10 25 100 200; do one $m_s $R --report-cost --delay --miss 0.2; done; done
echo "E14 DONE $(date)" >> $OUT
