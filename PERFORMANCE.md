# Performance and responsiveness notes

## V1.0.2 hot path

A normal visibility correction could perform all of the following:

1. resolve every tracked layer UUID;
2. read every tracked layer's visibility;
3. evaluate every enabled rule on each cascade pass;
4. apply linked visibility changes;
5. force a full document projection refresh;
6. resolve and read every tracked layer again;
7. rebuild the complete plugin rule tree, including another tracked-layer lookup.

The 125 ms timer also meant an ordinary eye-icon click could wait almost a full polling interval before enforcement.

## V1.1.0 changes

- Public Qt mouse-release and shortcut events schedule one coalesced scan with `QTimer.singleShot(0, ...)`.
- The timer remains as a fallback for programmatic and unusual visibility changes.
- UUID-resolved node wrappers are reused for 500 ms and invalidated on rule/document changes or wrapper errors.
- Rule membership is compiled into `member ID -> affected rules` indexes.
- Cascade passes process only rules touched by the current trigger set.
- Changed layers are read back directly; the tracked set is not fully resolved and reread again.
- The plugin does not call `Document.refreshProjection()` after `Node.setVisible()`.
- The docker tree is rebuilt only when document/rule/missing-layer status changes, not after each successful toggle.

## Synthetic rule-engine benchmark

The included benchmark measures pure Python rule dispatch with six members per linked rule. It does not measure Krita rendering, Qt event delivery, GPU work, or Flatpak overhead.

Observed on the development environment, in median microseconds per visibility event:

| Rules | V1.0.2-style dispatch | V1.1.0 compiled dispatch | Speedup |
|---:|---:|---:|---:|
| 10 | 19.47 µs | 10.48 µs | 1.86× |
| 50 | 88.28 µs | 34.39 µs | 2.57× |
| 100 | 175.51 µs | 64.19 µs | 2.73× |
| 250 | 466.91 µs | 166.71 µs | 2.80× |

Run it on another machine with:

```bash
python3 scripts/benchmark_hot_path.py
```

## Recommended settings

- **125 ms:** conservative default and good compatibility fallback.
- **250–500 ms:** lower idle API traffic while ordinary layer-list clicks still wake immediately.
- **25–50 ms:** useful for stress tests or programmatic workflows where every millisecond matters, at higher idle CPU cost.

## Remaining bottleneck

For realistic sprite files, Krita/Qt API calls and canvas invalidation are expected to dominate the sub-millisecond pure rule engine. The most useful real-world measurement is therefore perceived click-to-correction latency and idle CPU use in the production `.kra`, not only the synthetic benchmark.
