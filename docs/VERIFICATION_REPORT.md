# Validation record — 13 November 2026

**Artifact:** private `v1.0.0-rc1`, aligned with six-page manuscript `v2.3.1` and technical supplement `v2.3`.

## Independently executed in the preparation session

| Check | Result | Scope |
|---|---|---|
| Python unit tests | **PASS 13/13** | `python -B -m unittest discover -s tests -v` from `experiments/multiservice` |
| N5 exact structural certificate | **PASS** | Full 243-state Fraction-based enumeration; 242 feasible; four-move shortest improving sequence; witness gain ≈ 0.0006581378223342 |
| Rational payback recomputation | **PASS** | `python -B verify_n5_certificate.py --deep-payback` in a disposable source copy; free-terminal first profitable horizon 64 and initial-state-return first profitable horizon 129 |
| Paired ablation results | **PASS** | `python -B verify_results.py` from `experiments/ablation`; counts full 55/70, no transform 0/4, no transport congestion 1/5, no compute congestion 53/10 |
| Archived controller trajectories | **PASS** | Independently re-evaluated **5,616 trajectories across 599,040 operating slots**, with maximum total-cost numerical error `2.2737367544323206e-13`; ran in a disposable copy, as the program writes a validation summary |
| Compact Fig. 1 generator | **PASS** | Generated figure from the included Python source, rendered both PDFs at 100 dpi; rendered PNGs pixel-identical (350 × 201 pixels) |
| Release integrity smoke | **PASS** | Root quick checker verifies SHA-256 hashes, the unit tests and both short scientific checks; archive content remained unchanged |

## Not executed in this session

- Full regeneration of the 72 populations × six primary scenarios across all controller settings from scratch, followed by comparison against stored outputs.
- Paper-specific regeneration of exact Fig. 2 and Fig. 3 PDFs from raw archived inputs. The figure PDFs and relevant source data are included, but corresponding canonical generation scripts still need to be packaged and tested.
- Repeating the ±2% robustness campaigns from scratch.
- Any real-field dataset validation or production-scale deployment trial (none is claimed).

## Integrity practices

- Source ZIPs are retained unchanged outside the release candidate; their SHA-256 values are recorded in `SOURCE_PROVENANCE.md`.
- The n5 quick certificate is **read-only by default**. To write regenerated files, supply an explicit `--output-dir` outside the frozen release.
- The full archived trajectory validator writes a JSON report, so it was executed only in a disposable copy.
- `SHA256SUMS.txt` must be regenerated if any file is changed before DOI issuance.

**Interpretation:** These checks substantiate the archived mathematical and numerical claims; they do not prove robustness to alternate traffic models, topologies, real measurements, missing forecasts, or deployment environments.
