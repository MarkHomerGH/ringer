## Summary

Reviewed the widget-cache diff end to end: eviction, write-back, and the
metrics hook. One substantive defect in the eviction path; the metrics hook
is fine. Each finding below uses a heading so the block is easy to scan.

## Findings

### Finding: eviction runs before the write-back completes
Evidence: cache.py:88 — `del self._entries[key]` executes before `flush()` returns
Impact: a burst of evictions on a hot key can drop its last write
Fix: call flush() first, then delete the entry
Priority: P1
Confidence: high

### Finding: metrics counter is never reset between runs
Evidence: metrics.py:41 — `self.hits` is a class attribute, shared across instances
Impact: the hit-rate shown after a restart includes the previous process's count
Fix: move `hits` into `__init__`
Priority: P3
Confidence: medium
