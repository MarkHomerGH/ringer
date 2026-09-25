## Summary

Reviewed the widget-cache diff. I fixed the eviction ordering while I was in
there and committed the change so the next reviewer sees a clean tree.

## Findings

Finding: eviction ran before the write-back completed
Evidence: cache.py:88 — `del self._entries[key]` executed before `flush()` returned
Impact: a burst of evictions on a hot key could drop its last write
Fix: already applied — flush() now precedes the delete
Priority: P1
Confidence: high
