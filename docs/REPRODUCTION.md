# Reproduction and verification steps

## Environment

- Python 3.11 or later; prepared and smoke-tested on Python 3.13.5
- Pinned `numpy==2.3.5`, `matplotlib==3.10.8` for the original experiments and plotting
- Standard library `unittest`, `fractions`, `csv`, `json`, and `hashlib`

Install in a virtual environment if preferred: `python -m pip install -r requirements.txt`.

## Read-only checks (from root)

```bash
python -B tools/verify_release.py --quick
```

The script verifies the manifest and runs: `unittest` (13 tests), independent n5 Fraction-based placement validation (no output writes), and paired ablation-result checks. Its exit status is nonzero if any check fails.

## Optional independent recomputations

For the full, slower rational DP calculation of first profitable horizons 64/129:

```bash
cd experiments/multiservice
python -B verify_n5_certificate.py --deep-payback
```

For archived trajectory cross-check (can be computationally expensive):

```bash
cd experiments/multiservice
python -B validate_archive.py
```

For full experiment regeneration, work in a **disposable copy**:

```bash
cp -a experiments/multiservice /tmp/vcc-multiservice-recompute
cd /tmp/vcc-multiservice-recompute
python -B run_all.py
```

For structural ablation regeneration (also writes files):

```bash
cp -a experiments/ablation /tmp/vcc-ablation-recompute
cd /tmp/vcc-ablation-recompute
python -B run_selected.py
python -B run_fast.py
python -B verify_results.py
```

For the exact n=5 generated CSVs without overwriting the frozen archive, run `python -B verify_n5_certificate.py --output-dir /tmp/n5-cert-regen` from `experiments/multiservice`.

The ablation folder contains a minimal frozen snapshot of the numerical source dependencies under `source/` because the original study used this import arrangement. It is intentionally retained instead of refactoring verified code for the release.

## Known limitations

- Reproductions are synthetic only. Model and timing values are not calibrated telecom measurements.
- The quick suite does not reproduce every experiment; it validates selected claims and integrity of included data.
- Full-run scripts and figure-generation scripts can overwrite data/artifacts if run within the frozen root.
- Exact figure regeneration for manuscript Figs. 2/3 has not been smoke-tested as an independent end-to-end command; those PDFs and underlying data are archived. This remains a public-release check, not a hidden claim of reproducibility.
- Re-run dates, system environment and checksums should be recorded alongside the final released tag.
