# Certified lifetime bounds for cluster-head selection in wireless sensor networks

Code, data, and results for the paper "Certified lifetime bounds and an audit of evaluation practice for cluster-head selection in
wireless sensor networks" by Kofi Sarpong Adu-Manu and Stephen Kwaku Azongo (Department of Computer Science, University of Ghana),
submitted to the Journal of Network and Computer Applications.

Cite as: see `CITATION.cff`. Licence: MIT for the code; CC BY 4.0 for the results, the audit data, and the figures (see `LICENSE`).
`MANIFEST.md` links every table, figure, and number in the paper to its result file and script.

## In brief

The study measures how far cluster-head (CH) selection protocols are from the best lifetime a network can achieve.

- Bounds. The lifetime to first node death (FND) is bracketed by column generation over round configurations, with exact pricing as a
  weighted facility-location mixed-integer programme. The upper bound (UB) is a Farley bound built on the solver's proven dual bound, so
  it stays valid whatever the convergence; the integer lower bound (ILB) is an integer programme over the generated columns, a
  whole-round schedule the network can play.
- Protocols. Direct transmission, LEACH, KMRE, and PSO-C on 20 layouts; tuned PSO-C, grey wolf optimisation, and a model-aware greedy
  method (MMAX) on layouts 0-2; and the bound's own schedule run as a protocol that re-plans at the sink.
- Radios. The first-order model and three datasheet-informed models (CC2420, nRF52840, CC1101 at 868 MHz), with the sink outside the
  field, at its edge, or at its centre.
- Audit. 80 articles drawn at random from the 655 open-access articles that Europe PMC returns for 2021-2026, of which 33 are CH papers,
  coded for energy model, sink position, datasheet radio, optimality reference, idle listening, and a direct-transmission baseline;
  a second coder checked 20 of the 80.

## Layout

| Path | Contents |
|---|---|
| `src/scoping/e1_radio_model_gate.py`, `e2_lifetime_gate.py` | Radio constants and parameters, the PSO-C implementation (imported by the later scripts) |
| `src/scoping/e8_model_v2.py` | Energy model (minimum-energy relays, control frames, single-hop membership), the four protocols, column generation with exact pricing |
| `src/scoping/e10_lp_protocol.py` | The bound schedule run as a protocol (re-plan interval, report noise, report cost, delayed and lost reports) |
| `src/scoping/e11_listening.py` | Protocols and bounds with a sleep baseline and a 2 ms guard time per reception |
| `src/scoping/e12_modern_baselines.py` | PSO-C and GWO with k in {3, 5, 8}, and MMAX |
| `src/scoping/e13_revision.py` | Protocols, UB, LB_LP, and the integer lower bound for one setting and layout (20-layout runs, control-frame and density variants) |
| `src/scoping/run_all.py` | Resumable orchestrator that produced the E8 to E13 result files |
| `src/scoping/run_e14.py` | Runner for E14 (re-plan interval) and E14b (nRF52840 with unscaled currents) |
| `src/lit/` | Audit sample from the Europe PMC REST API, keyword screen, excerpts for coding, and coder agreement (`audit_kappa.py`) |
| `src/paper/` | Tables and figures of the paper from the result files (see `MANIFEST.md`) |
| `papers/audit/` | The 655 identifiers of the sampling frame (`all655_ids.txt`), the 80 screened articles with the reason for each exclusion (`sample80.csv`), sample metadata (`sample.jsonl`), keyword screen (`audit.csv`), the coding sheet of the 33 CH papers (`coding.csv`) and of the four borderline articles (`coding_borderline.csv`), and the second coder's sheet (`second_coder/coder2.csv`); full texts are not redistributed |
| `hypotheses/HYPOTHESES_2026-11-19.md` | The hypotheses and pass criteria as written on 19 November 2026 (unedited) |
| `results/` | One file per experiment (see below) |
| `draft/figs/` | Figures of the paper (PDF) |

## Results

| File | Experiment |
|---|---|
| `results/e13_main.txt` | Main comparison: four protocols, UB, LB_LP, and ILB, 4 radios x 3 sinks x 20 layouts |
| `results/e13_adv.txt` | Control-frame variant (one reception per CH advertisement in range), layouts 0-2 |
| `results/e13_density.txt` | 50 and 200 nodes, layouts 0-1 |
| `results/e8_v2.txt`, `e8_v2_verify.txt`, `e8_v2_summary.txt` | Earlier three-layout runs and their re-verification with dual-bound-safe pricing (used by the sleep table) |
| `results/e10_lp_protocol.txt` | The bound schedule as a protocol, re-plan every 50 rounds, exact and 10% noisy energy reports, layouts 0-2 |
| `results/e13_lpsched.txt` | The bound schedule with a charged energy report and with realistic reports, layout 0 |
| `results/e14_replan.txt` | Re-plan interval R = 10 to 200, FO centre and CC2420 edge, exact and realistic reports; CC2420 edge report variants |
| `results/e14b_nrf_v2.txt` | nRF52840 with the unscaled version 2.0 currents, layouts 0-2 |
| `results/e11_listening.txt` | Sleep energy at reporting intervals of 10, 60, and 300 s |
| `results/e12_baselines.txt` | Tuned PSO-C and GWO, and MMAX |
| `results/e15_breakdown.txt` | Energy per round by component, DIRECT against PSO-C, nRF52840 edge sink |
| `results/fig_data/` | Traces behind the alive-node, residual-energy, and convergence figures |

## Reproducing

Python 3.13.5 with the packages in `requirements.txt` (NumPy 2.3, SciPy 1.17 with HiGHS). From the repository root:

```
python -I src/scoping/e13_revision.py FO centre 0 --iters 800        # one setting and layout: protocols, UB, LB_LP, ILB
python -I src/scoping/e10_lp_protocol.py FO centre 0 --replan 50 --noise 0.0 --iters 600 --reiters 20
python -I src/scoping/run_all.py heavy      # E10, E13 main, and the bound runs (resumable)
python -I src/scoping/run_all.py light      # E11, E12, E13 variants, and the bound re-verification
python -I src/scoping/run_e14.py            # E14 and E14b (resumable)
python -I src/paper/e15_breakdown.py nRF52840v3 edge 3 > results/e15_breakdown.txt
python -I src/paper/fig_data.py residual    # then cg and alive
python -I src/paper/make_figures.py
python -I src/paper/e13_tables.py           # and the other scripts listed in MANIFEST.md
```

The table scripts write LaTeX table bodies to `draft/`; the manuscript sources themselves are not published before the paper.
Run times on a 4-core laptop (Intel Core i3-1125G4) with 3.7 GB of RAM: 7 to 16 minutes per bound with 100 nodes, and from 3 minutes to
about 3.5 hours per bound-schedule run (the longest with re-planning every 10 rounds or on slow layouts). Run the solver
jobs one at a time on a machine with little memory.
