## Summary

I read the widget-cache diff and both new tests, traced the eviction path
and the write-back, and ran the sequence put/evict/get by hand.

## Findings

No findings. Eviction ordering, write-back completion and metrics scoping
all hold; the rename is mechanical.
