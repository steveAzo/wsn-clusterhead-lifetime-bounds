# Manifest: tables, figures, and numbers in the paper

Each table and figure of the paper, the experiment behind it, the raw result file, and the script that produces it from that file.
All scripts run from the repository root with `python -I <script>`. Table numbers refer to the submitted manuscript; labels are given
so they can be matched after renumbering.

## Figures

| Figure (label) | Content | Result file(s) | Script |
|---|---|---|---|
| Audit screening flow (`fig:flow`) | 655 -> 80 -> 33 articles, exclusion reasons | `papers/audit/sample80.csv` | counts typed from the file (column `included`, `screening_note`) |
| Deployment (`fig:deployment`) | Layout 0, three sink positions, CC2420 range | none (layout seed 100) | `src/paper/make_figures.py` (`fig_deployment`) |
| Convergence (`fig:cg`) | LB_LP and UB during column generation | `results/fig_data/cg.json` | `src/paper/fig_data.py cg`, then `make_figures.py` (`fig_cg`) |
| Audit summary (`fig:audit`) | Shares with Wilson intervals; sink positions | `papers/audit/coding.csv` | `make_figures.py` (`fig_audit`) |
| Share of the UB (`fig:gap`) | Four protocols and the bound schedule, 4 radios x 3 sinks | `results/e13_main.txt`, `results/e10_lp_protocol.txt` | `make_figures.py` (`fig_gap`) |
| Alive nodes (`fig:alive`) | Alive and connected nodes per round, layout 0 | `results/fig_data/alive.json` | `fig_data.py alive`, then `make_figures.py` (`fig_alive`) |
| Residual energy (`fig:residual`) | Residual energy at FND, FO centre, layout 0 | `results/fig_data/residual.json` | `fig_data.py residual`, then `make_figures.py` (`fig_residual`) |

## Tables

| Table (label) | Experiment | Result file(s) | Script |
|---|---|---|---|
| Prior exact approaches (`tab:prior`) | literature | none | none |
| Radio models (`tab:radios`) | parameters | none | constants in `src/scoping/e1_radio_model_gate.py` (`RADIOS`) and `src/scoping/e8_model_v2.py` (`EXTRA_RADIOS`) |
| nRF52840 power steps (`tab:nrf`) | parameters | none | constants as above; range and energy from the link budget in `e8_model_v2.Model` |
| Audit (`tab:audit`) | E9 audit | `papers/audit/coding.csv` | counts from the file; `make_figures.py` (`fig_audit`) plots the same counts with Wilson intervals |
| Audit coding sheet (`tab:coding`, appendix) | E9 audit | `papers/audit/coding.csv` | `src/paper/make_audit_table.py` |
| Coder agreement (text, audit method) | second coder | `papers/audit/coding.csv`, `sample80.csv`, `second_coder/coder2.csv` | `src/lit/audit_kappa.py` |
| FND and bounds (`tab:gap`) | E13, 20 layouts | `results/e13_main.txt` | `src/paper/e13_tables.py` |
| Spread across layouts (`tab:var`) | E13 | `results/e13_main.txt` | `src/paper/e13_tables.py` |
| Paired comparisons (`tab:paired`) | E13 | `results/e13_main.txt` | `src/paper/e15_paired.py` |
| Energy breakdown, nRF52840 edge (`tab:breakdown`) | E15, layouts 0-2 | `results/e15_breakdown.txt` | `src/paper/e15_breakdown.py` (writes the result file) |
| Tuned baselines and MMAX (`tab:baselines`) | E12, E10, layouts 0-2 | `results/e12_baselines.txt`, `results/e10_lp_protocol.txt`, `results/e13_main.txt` | `src/paper/e15_baselines.py` |
| Bound schedule as a protocol (`tab:lpsched`) | E10, layouts 0-2 | `results/e10_lp_protocol.txt`, `results/e13_main.txt` | `src/paper/e10_table.py` (prints the rows) |
| Report cost and errors (`tab:lpvar`) | E13b, E14, layout 0 | `results/e10_lp_protocol.txt`, `results/e13_lpsched.txt`, `results/e14_replan.txt` | `src/paper/e13_tables.py` |
| Re-plan interval (`tab:replan`) | E14, layout 0 | `results/e14_replan.txt` (R = 50 from `e10_lp_protocol.txt`, `e13_lpsched.txt`) | `src/paper/e15_replan.py` |
| Sleep and idle energy (`tab:sleep`) | E11 | `results/e11_listening.txt`, `results/e8_v2.txt` | `src/paper/e11_table.py` (prints the rows) |
| Control-frame accounting (`tab:adv`) | E13, per-CH variant, layouts 0-2 | `results/e13_adv.txt` | `src/paper/e13_tables.py` |
| Node density (`tab:density`) | E13, 50 and 200 nodes, layouts 0-1 | `results/e13_density.txt` | `src/paper/e13_tables.py` |

## Numbers in the text without a table

| Statement | Result file | Script |
|---|---|---|
| Bound gaps over the 220 cases (LB_LP/UB, ILB/LB_LP, ILB/UB) and pricing calls solved to optimality | `results/e13_main.txt` | `src/paper/e13_tables.py` (prints them) |
| nRF52840 with the unscaled version 2.0 currents (regime map) | `results/e14b_nrf_v2.txt`, `results/e13_main.txt` | `src/paper/e15_nrf_v2.py` |
| Re-plan time per plan (median 8 s) | run logs (not published, machine-specific) | stderr of `src/scoping/e10_lp_protocol.py` |

## How the result files were produced

| Result file | Producer |
|---|---|
| `results/e8_v2.txt`, `e8_v2_verify.txt`, `e10_lp_protocol.txt`, `e11_listening.txt`, `e12_baselines.txt`, `e13_*.txt` | `src/scoping/run_all.py heavy` and `run_all.py light` (resumable orchestrator; each job line is listed in the script) |
| `results/e14_replan.txt`, `results/e14b_nrf_v2.txt` | `src/scoping/run_e14.py` |
| `results/e15_breakdown.txt` | `src/paper/e15_breakdown.py nRF52840v3 edge 3` |
| `results/fig_data/*.json` | `src/paper/fig_data.py` |

## Hypotheses

`hypotheses/HYPOTHESES_2026-11-19.md` is an unedited copy of the hypotheses file as written on 19 November 2026 (Appendix A of the
paper). It was kept in the authors' project files, not lodged with a registry.
