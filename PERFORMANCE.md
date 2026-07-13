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

## V1.1.0 optimization

- Public Qt mouse-release and shortcut events scheduled a coalesced scan at the next event-loop opportunity.
- The timer remained as a fallback for programmatic and unusual visibility changes.
- UUID-resolved node wrappers were reused for 500 ms and invalidated on rule/document changes or wrapper errors.
- Rule membership was compiled into `member ID -> affected rules` indexes.
- Cascade passes processed only rules touched by the current trigger set.
- Changed layers were read back directly; the tracked set was not fully resolved and reread again.
- The docker tree was rebuilt only when document/rule/missing-layer status changed.

The zero-delay enforcement and removal of explicit projection refreshes proved too aggressive for some Krita rendering paths.

## V1.1.1 render-safe hot path

- Layer-list and shortcut input is debounced for 32 ms, allowing Krita's own visibility transaction and asynchronous projection scheduling to settle.
- Rapid clicks restart the single-shot timer and are coalesced into one dependent visibility batch.
- One `Document.refreshProjection()` runs after the complete plugin-generated batch, not after every individual layer.
- Node caching, compiled dispatch, affected-rule-only cascades, direct changed-layer readback, and reduced docker rebuilding remain enabled.
- The minimum fallback polling interval is 50 ms.

## Synthetic rule-engine benchmark

The included benchmark measures pure Python rule dispatch with six members per linked rule. It does not measure Krita rendering, Qt event delivery, GPU work, Flatpak overhead, the 32 ms render-settle delay, or projection rebuilding.

Observed on the development environment, in median microseconds per visibility event:

| Rules | V1.0.2-style dispatch | V1.1 compiled dispatch | Speedup |
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
- **250–500 ms:** lower idle API traffic while ordinary layer-list clicks use the separate 32 ms render-safe path.
- **50–100 ms:** useful for programmatic visibility workflows, at higher idle API cost.

## Remaining bottleneck

For realistic sprite files, Krita/Qt API calls, projection rebuilding, and canvas invalidation dominate the sub-millisecond pure rule engine. The most useful real-world measurements are perceived click-to-correction latency, visual correctness after rapid switching, and idle CPU use in the production `.kra`.
