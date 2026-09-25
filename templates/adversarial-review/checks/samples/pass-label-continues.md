## Summary

Reviewed the widget-cache diff. One defect in the eviction path, documented
below with the evidence split over several lines because the reproduction
takes three steps.

## Findings

Finding: eviction runs before the write-back completes
Evidence:
  cache.py:88 — `del self._entries[key]` executes before `flush()` returns;
  reproduce with put(k), evict(k), get(k) → None while the write is in flight
Impact:
  a burst of evictions on a hot key can drop its last write
Fix:
  call flush() first, then delete the entry
Priority: P1
Confidence: high
