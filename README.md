# Communication–Compute Service Placement: Reproducibility Artifact

> **VERSION 1.0.0 (13 November 2026) — version-specific DOI supplied by the Zenodo record after archiving.**  
> Accompanies the six-page manuscript **v2.3.1**, *Non-Monotone Service Placement and Reconfiguration Barriers in Edge Orchestration*, by Gábor Kuruc and József Bíró.  
> **The corresponding author has confirmed institutional publication approval, MIT/CC BY 4.0 licensing, and the copyright attribution in the MIT LICENSE. No DOI has yet been assigned.** The experiments are synthetic, not measured telecom traces.

This package collects deterministic multi-service experiments, archived dynamic-controller outputs, exact placement certificates, paired mechanism ablations, manuscript figure assets and the technical supplement. All 5,616 archived controller trajectories (599,040 slots) and the deeper 64/129-slot rational payback calculations were also checked independently in a disposable working copy during preparation; see `docs/VERIFICATION_REPORT.md`. It deliberately excludes older internal research PDFs, older manuscript drafts, nested source ZIPs, bytecode, and unrelated notes.

## Scientific scope

One traffic-transforming stage per service is placed at RAN, MEC, or Core on a shared two-link logical transport route. The model varies available RAN compute headroom. It combines traffic reduction, shared transport congestion, shared compute congestion, per-service latency targets, and bounded relocations. **It does not represent a physical multi-MEC transport topology, local-breakout return-path shortening or calibrated hardware performance.**

## Folder map

- `experiments/multiservice/`: original Python model and controllers, reproducible synthetic populations, stored data/traces, n=2 comparisons and n=5 certificates.
- `experiments/ablation/`: one-factor mechanism-removal study and paired results for the same 72 populations; its `source/` subdirectory is a frozen source snapshot, not a new independent model.
- `figures/`: the three PDFs used in manuscript v2.3.1 and the explicit compact Fig. 1 generator; further manuscript-specific figure regeneration is listed as an open release check.
- `supplement/`: v2.3 companion LaTeX and six-page PDF; the feedback corrections in main manuscript v2.3.1 concern its author contact and model explanation, not the numerical results.
- `tools/`: **read-only** root integrity and fast scientific verification.
- `docs/`: claim-to-file map, evidence provenance, verification scope, DOI/publication steps, and approval checklist.

## Quick verification (Python 3.11+; tested here on Python 3.13.5)

From the extracted repository root:

```bash
python -m pip install -r requirements.txt
python -B tools/verify_release.py --quick
```

This verifies SHA-256 checksums, runs 13 unit tests, rechecks the five-service four-move barrier and archived 64/129 profitable-horizon certificates, and validates the paired 72-population ablation summaries. It is **read-only by default** (`-B` prevents bytecode generation), so a successful run leaves the release unchanged. It does **not** re-run the expensive rational dynamic program, reconstruct all trajectories, or recompute all ablation populations.

To run the optional deep rational certificate, from `experiments/multiservice/`:

```bash
python -B verify_n5_certificate.py --deep-payback
```

To save *regenerated* n=5 certificate files without touching this release, pass `--output-dir /some/scratch/location` to `verify_n5_certificate.py`.

Full experiment regeneration is more expensive and **writes outputs**: run `python -B run_all.py` only inside a disposable working copy of `experiments/multiservice/`, then compare output tables with the frozen data. The same applies to `experiments/ablation/run_fast.py` and figure-generation scripts. See `docs/REPRODUCTION.md`.

## Key paper-to-artifact links

- Minimal n=2 reversal and model: `experiments/multiservice/inputs/m1_n2_reference.py`, `data/n2_regression.csv`, `data/static_fraction_certificates.json`.
- N=5 strict exchange barrier: `experiments/multiservice/certificate/n5_14_all_placements.csv`, `n5_14_path.csv`, `n5_14_validation.json`.
- Free-terminal vs closed-return exact payback: `experiments/multiservice/data/fraction_certificates.json` and optional `--deep-payback`.
- 72-paired-population ablation: `experiments/ablation/population_outcomes.csv`, `matched_population_summary.json`.
- 432 primary traces and controller results: `experiments/multiservice/data/primary_traces.csv`, `data/primary_summary.csv`, `data/aggregate_primary.csv`.
- Controller exemplars and additional sensitivity results: `data/witness_timeseries.csv`, `data/pulse_map_summary.csv`; see `supplement/`.

The detailed claim-to-file map is in [`docs/MANIFEST.md`](docs/MANIFEST.md); independently performed checks are in [`docs/VERIFICATION_REPORT.md`](docs/VERIFICATION_REPORT.md).

## Archival status and known limitations

The release-specific DOI is assigned **by Zenodo after successful ingestion of the tagged GitHub release**; it is intentionally not hard-coded into this frozen source snapshot. Consult the corresponding Zenodo record for the verified DOI. A complete tested generator for the exact manuscript Fig. 2 and Fig. 3 PDFs has not been provided; the PDFs and underlying numerical evidence are included. The corresponding author confirms Nokia/BME publication approval and the MIT license copyright attribution. The conference's supplementary-material and anonymous-review rules should be checked before submitting the manuscript. Never cite an unverified DOI.

## Licenses and public release

Software code is MIT-licensed (`LICENSE`); original synthetic datasets, research figures and text are CC BY 4.0 (`LICENSE-DATA.md`). See `docs/LICENSING.md` for scope, third-party caveats, and the confirmed copyright attribution. The authoritative **version DOI** is the one displayed on the published Zenodo record, if archiving succeeds.
