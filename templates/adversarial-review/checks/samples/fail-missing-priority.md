## Summary

Reviewed the widget-cache diff. One defect in the eviction path.

## Findings

**Finding:** eviction runs before the write-back completes
**Evidence:** cache.py:88 — `del self._entries[key]` executes before `flush()` returns
**Impact:** a burst of evictions on a hot key can drop its last write
**Fix:** call flush() first, then delete the entry
**Confidence:** high
