## Summary

The diff is small and the tests are thorough. There is exactly one substantive
finding: the eviction path deletes the entry before the write-back returns.
Everything else I checked (the metrics hook, the rename, the two new tests)
holds up.

## Findings

Finding: eviction runs before the write-back completes
Evidence: cache.py:88 — `del self._entries[key]` executes before `flush()` returns
Impact: a burst of evictions on a hot key can drop its last write
Fix: call flush() first, then delete the entry
Priority: P1
Confidence: high
