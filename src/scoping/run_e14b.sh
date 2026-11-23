#!/bin/sh
# E14b (second review, point 4.1): nRF52840 with the original v2.0 product-brief currents (no scaled steps), E13 settings,
# layouts 0-2, three sinks. Waits for E14 (serial, 3.7 GB RAM). Resumable.
cd "$(dirname "$0")/../.." || exit 1
OUT=results/e14b_nrf_v2.txt
while ! grep -q "E14 DONE" results/e14_replan.txt 2>/dev/null; do sleep 120; done
for s in far edge centre; do for seed in 0 1 2; do
  grep -q "^R13 nRF52840 $s seed $seed " $OUT 2>/dev/null && continue
  python -I src/scoping/e13_revision.py nRF52840 $s $seed --iters 800 > results/e14b_last.log 2>&1
  grep "^R13" results/e14b_last.log >> $OUT || { echo "FAIL nRF52840 $s $seed" >> $OUT; tail -3 results/e14b_last.log >> $OUT; }
done; done
echo "E14B DONE $(date)" >> $OUT
