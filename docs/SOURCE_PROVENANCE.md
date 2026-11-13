# Provenance and release boundary

This release candidate is assembled from frozen 2026 project artifacts. The original input ZIPs remain untouched. Its structure is intentionally navigable rather than a ZIP-of-ZIPs.

| Source | Use in this release |
|---|---|
| `VCC2027_Reproducibility_Package_v1_0.zip` | Multi-service Python source, original synthetic inputs, output tables, exact certificates |
| `VCC2027_Ablation_Study_v1_0.zip` | Paired 72-population ablation code and results |
| `VCC2027_Overleaf_v2_3_1_Gabor_Feedback.zip` | Exact main-paper figure PDFs, compact Fig. 1 Python generator, supplement TeX source |
| `VCC2027_Technical_Supplement_v2_3.pdf` | Six-page companion PDF, numerically unchanged by later manuscript feedback |

The archived script `experiments/multiservice/verify_n5_certificate.py` was minimally adapted to be read-only by default, with a new explicit `--output-dir` flag to save regenerated files. No underlying model, stored primary data, archived certificate or numerical conclusion was edited.

Excluded: intermediate manuscript versions, old internal technical PDFs/research notes, nested ZIP files, generated Python bytecode and outdated archival metadata. This is a *curation* for possible future release, not an independent scientific replication of all experiments.

### Input archive hashes (SHA-256)

- reproducibility package — `VCC2027_Reproducibility_Package_v1_0.zip`: `915484ebfcf8c1ee0411f2741b33dd1bdab2f04eba385d42679d20724c819b3e`
- ablation package — `VCC2027_Ablation_Study_v1_0.zip`: `631014c54d26f13e67ff863a81b05c1c053687412cd9cf1bc37e369be7b8e0dd`
- Overleaf v2.3.1 source — `VCC2027_Overleaf_v2_3_1_Gabor_Feedback.zip`: `cc7f721ff5c76979c7b75db2ada9932cfa5ffc7c758c64b06d30d2f9f86257e0`
- supplement PDF — `VCC2027_Technical_Supplement_v2_3.pdf`: `1aa025aa0f2aa1e1cfac1cb362e6845f77aebde1085f4979e4689f6dcf8d7125`
