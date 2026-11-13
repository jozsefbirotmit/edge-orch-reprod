# Pre-publication approval and release checklist

Publication approvals, dual-license choices, and the two-author MIT copyright attribution were all confirmed by the corresponding author on 13 November 2026. No repository visibility change or release has yet been performed by these confirmations.

- [x] Confirm authorship/MIT copyright line; corresponding author explicitly confirmed the two-author attribution (13 November 2026).
- [x] Nokia and BME publication approvals **reported by corresponding author**; MIT copyright attribution also confirmed.
- [x] Public dissemination of the prepared original research artifact authorized according to the corresponding author; still review third-party material separately.
- [x] MIT license selected and `LICENSE` supplied.
- [x] CC BY 4.0 selected and `LICENSE-DATA.md` supplied for original data, figures and text; verify third-party elements.
- [ ] Double-check no private data, credentials, sensitive source or unpublished restricted PDF remains.
- [x] Run full trajectory validator and deep rational payback check in a clean working copy (13 November 2026; Python 3.13.5; see `VERIFICATION_REPORT.md`).
- [ ] Confirm whether exact Fig. 2/3 paper-specific generators should be added, or document generation sufficiently.
- [ ] Recheck `SHA256SUMS.txt` on final frozen source.
- [ ] Check VCC 2027 anonymous review, external materials and supplementary archive policies.
- [x] Create private GitHub repository `jozsefbirotmit/edge-orch-reprod` and upload the reviewed 92-file artifact; use a separate public-release step.
- [ ] Select Zenodo/direct archiving approach and obtain a **real version-specific DOI**.
- [ ] Verify DOI resolves to exact dataset and download contents match checksums.
- [ ] Update `CITATION.cff` with final release date, version and DOI; create tag and release notes.
- [ ] Insert verified artifact availability citation into manuscript and supplement; recompile six pages.
