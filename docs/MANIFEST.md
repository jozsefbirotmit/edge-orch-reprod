# Claim-to-file map (manuscript v2.3.1)

| Manuscript claim/asset | Archived evidence | Regeneration status |
|---|---|---|
| Two-service optimal placement `MC → MR → RM → RR`, witness H=40/100/400 | `experiments/multiservice/inputs/m1_n2_reference.py`; `experiments/multiservice/data/n2_regression.csv`, `static_fraction_certificates.json`; source `m1_general.py` | Unit test and n=2 reference available |
| Strict n=5 trap at H=30; 243 candidate placements, 242 feasible, four-move route | `experiments/multiservice/certificate/n5_14_all_placements.csv`, `n5_14_path.csv`, `n5_14_validation.json`; `verify_n5_certificate.py` | Exact quick per-state recomputation from rational model |
| Constant-headroom `K_out=64`, `K_ret=129` | `experiments/multiservice/data/fraction_certificates.json` | Stored exact rationals checked in quick mode; expensive independent DP optional |
| 72 population structural reversal/trap counts and mechanism ablations (55/70 full; 0/4, 1/5, 53/10) | `experiments/multiservice/data/populations.csv`, `experiments/ablation/population_outcomes.csv`, `matched_population_summary.json`; `experiments/ablation/run_fast.py` | Paired output count check; full rerun is optional and writes data |
| 432 primary headroom traces and control cost gaps | `experiments/multiservice/data/primary_traces.csv`, `primary_summary.csv`, `aggregate_primary.csv`, `aggregate_by_trace.csv`, `findings.json`; `run_experiments.py`, `validate_archive.py` | Archived complete outputs; full rerun not part of quick verification |
| Selected pulse-control case study, robustness and 270 sensitive combinations | `experiments/multiservice/data/witness_timeseries.csv`, `pulse_map_summary.csv`, `pulse_thresholds.csv`, `local_robustness.csv` | Source and tables included; see supplement |
| Manuscript Fig. 1: logical network and reversal | `figures/fig1_model_reversal.pdf`, `figures/generate_fig1_compact.py` | Regenerable from exact functions; generator included |
| Manuscript Fig. 2: n=5 barrier | `figures/fig2_exchange_barrier.pdf`, `experiments/multiservice/certificate/n5_14_all_placements.csv`, `n5_14_path.csv` | Figure PDF and data archived; paper-specific generator pending |
| Manuscript Fig. 3: selected controller traces | `figures/fig3_pulse_control.pdf`, `experiments/multiservice/data/witness_timeseries.csv` | Figure PDF and data archived; paper-specific generator pending |
| Further parameter tables and mathematical detail | `supplement/technical_supplement.pdf` and `.tex` | Source and PDF included |

**Definitions:** A sampled inherited strict local trap is not necessarily a finite-step reachable exchange barrier. Payback with fixed initial-state return is distinct from RAR reconnection to an evolving shadow plan. The large-scale experiments use perfect queried forecasts and synthetic workloads; no field prevalence claims are made.
