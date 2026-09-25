## Summary

Read the widget-cache diff and the two tests that cover it. The eviction
ordering bug is real and reproducible with the sequence quoted below; nothing
else in the diff changes behaviour.

## Findings

**Finding:** eviction runs before the write-back completes
**Evidence:** cache.py:88 — `del self._entries[key]` executes before `flush()` returns
**Impact:** a burst of evictions on a hot key can drop its last write
**Fix:** call flush() first, then delete the entry
**Priority:** P1
**Confidence:** high
