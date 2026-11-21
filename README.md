# Exact lifetime bounds for cluster-head selection in wireless sensor networks

Code and results for the paper "Exact lifetime bounds and an audit of evaluation practice for cluster-head selection in wireless sensor
networks" by Kofi Sarpong Adu-Manu and Stephen Kwaku Azongo (Department of Computer Science, University of Ghana), submitted to the
Journal of Network and Computer Applications.

Cite as: see `CITATION.cff`. Licence: MIT for the code; CC BY 4.0 for the results, the audit coding sheet, and the figures (see `LICENSE`).

## In brief

The study measures how far cluster-head (CH) selection protocols are from the best lifetime a network can achieve. Lifetime brackets
(lower and upper bounds on the rounds to the first node death) are computed by column generation over round configurations, with exact
pricing as a weighted facility-location mixed-integer programme; the upper bound uses the solver's proven dual bound, so it stays valid
if a pricing call stops at its time limit. Four protocols (direct transmission, LEACH, KMRE, PSO-C), tuned PSO-C and grey wolf
optimisation, and a model-aware greedy method are compared with the bracket under the first-order radio model and three datasheet radios
(CC2420, nRF52840, CC1101 at 868 MHz), with the sink outside the field, at its edge, or at its centre. The schedule from the bound is also
run as a protocol that re-plans every 50 rounds. An audit of 80 randomly sampled open-access papers from Europe PMC (2021 to 2026)
records the evaluation practice of 33 CH papers.

## Layout

| Path | Contents |
|---|---|
| `src/scoping/e1_radio_model_gate.py`, `e2_lifetime_gate.py` | Radio constants and parameters, the PSO-C implementation (imported by the later scripts) |
| `src/scoping/e8_model_v2.py` | Energy model v2 (minimum-energy relays, control frames, single-hop membership), the four protocols, the column-generation bracket |
| `src/scoping/e10_lp_protocol.py` | The bound schedule run as a protocol (re-plan every 50 rounds, optional report noise) |
| `src/scoping/e11_listening.py` | The same with a sleep baseline and a 2 ms guard time per reception |
| `src/scoping/e12_modern_baselines.py` | PSO-C and GWO with k in {3, 5, 8}, and the model-aware greedy method MMAX |
| `src/scoping/run_all.py` | Resumable orchestrator that produced every result file below |
| `src/scoping/e8_summary.py` | Summary of `results/e8_v2.txt` |
| `src/lit/audit_collect_epmc.py`, `audit_collect.py`, `audit_extract.py`, `audit_excerpts.py` | Audit sample from the Europe PMC REST API, keyword screen, and excerpts for coding |
| `src/paper/` | Tables and figures of the paper from the result files (`make_figures.py`, `fig_data.py`, `e10_table.py`, `e11_table.py`, `e12_table.py`, `make_audit_table.py`) |
| `papers/audit/` | Audit sample metadata (`sample.jsonl`), keyword screen (`audit.csv`), and the coding sheet of the 33 CH papers (`coding.csv`); full texts are not redistributed |
| `results/` | One file per experiment (see below) |
| `draft/figs/` | Figures of the paper (PDF) |

## Results

| File | Experiment |
|---|---|
| `results/e8_v2.txt` | FND of the four protocols and the LB/UB bracket, 4 radios x 3 sinks x 3 layouts |
| `results/e8_v2_verify.txt` | Every bracket recomputed with dual-bound-safe pricing (identical to `e8_v2.txt`; adds FO far layout 1) |
| `results/e10_lp_protocol.txt` | The bound schedule as a protocol, exact and 10% noisy energy reports |
| `results/e11_listening.txt` | Protocols and bracket with sleep energy at reporting intervals of 10, 60, and 300 s |
| `results/e12_baselines.txt` | Tuned PSO-C and GWO, and MMAX |
| `results/fig_data/` | Traces behind the alive-node, residual-energy, and convergence figures |

## Reproducing

Python 3.13.5 with the packages in `requirements.txt`. From the repository root:

```
python -I src/scoping/e8_model_v2.py FO centre 0 --lp --iters 800
python -I src/scoping/e10_lp_protocol.py FO centre 0 --replan 50 --noise 0.0 --iters 600 --reiters 20
python -I src/scoping/run_all.py heavy      # every E10 and bound run, resumable
python -I src/scoping/run_all.py light      # E12, E11, and the bound re-verification
python -I src/paper/fig_data.py residual    # then cg and alive
python -I src/paper/make_figures.py
```

Run times on a 4-core laptop with 3.7 GB of RAM: 1 to 10 minutes per bracket, 10 minutes to 3.5 hours per E10 run (memory-bound).
