# Verification report

Release: **1.1.0**  
Verification date: **2026-07-13**

## Automated checks

- Ruff format and lint checks in the tests workflow
- deterministic Krita importer ZIP build
- unit, controller, adapter, storage, package, and rule-engine tests
- offscreen PyQt5 docker construction test
- event-assisted scan coalescing test
- recursive Python bytecode compilation
- Bash syntax validation
- mocked Flatpak installation and replacement-backup test
- ZIP CRC/integrity and reproducibility checks

## Responsiveness regressions covered

- node wrappers are reused across hot scans;
- a successful rule correction does not force `Document.refreshProjection()`;
- the controller does not perform a second full UUID-resolution pass after enforcement;
- unrelated rules do not affect a triggered result;
- multiple immediate wake requests coalesce into one queued scan;
- the regular timer remains active as a fallback;
- the docker does not rebuild its rule tree for ordinary successful corrections.

## Synthetic benchmark

Run:

```bash
python3 scripts/benchmark_hot_path.py
```

This benchmark measures the pure rule-dispatch hot path. It does not measure Krita rendering, Qt event delivery, GPU work, or Flatpak overhead. Real responsiveness should also be checked interactively with the user's production-size `.kra` files.

## Remaining real-world test

The final performance proof is an interactive comparison inside the user's graphical Krita Flatpak. Compare 1.0.2 and 1.1.0 with the same file, rule set, fallback interval, and rapid eye-icon sequence while observing CPU use and perceived latency.
