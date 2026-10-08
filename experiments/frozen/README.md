# Authoritative Frozen Experiment: `stage20_corrected_20260923_092749`

This directory provides the authoritative manifest and configuration files for the frozen experiment:

* **`experiment_id.txt`**: Records the exact authoritative experiment identifier: `stage20_corrected_20260923_092749`.
* **`configuration/`**:
  * `experiment_corrected_48g.yaml`: Complete hyperparameter specification.
  * `graph_split_manifest_48g.csv`: Deterministic train/validation/test split for all 48 graphs.
* **`manifests/`**:
  * `FINAL_LOCK_MANIFEST.json`: Top-level machine-readable lock manifest.
  * `LOCK_CHECKSUMS.txt`: SHA-256 digests for all 44 audit evidence files.
  * `SOURCE_PROVENANCE_MANIFEST.json`: Source file hashes and provenance history.

The corresponding raw benchmark logs and processed metrics reside at:
`results/stage20_corrected_20260923_092749/`
and authoritative audit artifacts reside in:
`FINAL_CORRECTED_AUDIT/`.
