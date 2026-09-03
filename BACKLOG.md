# BACKLOG — ringer

Friction-free capture of deferred work (house convention). Entries move to real
work items when a session picks them up; nothing here is scheduled.

## Deferred items

### Shared report-check parsing module (de-drift the Finding-block checks)

**Filed:** 2026-09-02 (Mark, v0.4.2 spec-panel session)

The generic parts of review-report checking — locate the `## Findings` section,
split `Finding:` blocks, verify the Evidence/Impact/Fix/Priority/Confidence
labels, detect `NO FINDINGS` — exist as copy-evolved near-twins:
`templates/adversarial-review/checks/check_review_report.py` (the skeleton) and
per-job descendants like homer-workspace `reviews/_check_v04_review.py`. The
2026-09-02 phantom-block bug (Summary prose line-wrapping onto "finding:")
existed in BOTH and had to be fixed twice (homer-workspace 3601665, ringer
8bf5e31) — proof of the drift Mark flagged.

**Work:** extract the generic parsing into a small importable module in this
repo (e.g. `checklib/report_blocks.py`); template and per-job checks import it
and keep only job-specific rules (expected HEAD, finding-ID roster, anchor
counts). Regression fixtures: the five real v0.4.2 panel reports under
homer-workspace `reviews/_runs/v042-deploy-stage2-*` (one false-FAIL victim,
three honest PASSes, one genuine format FAIL).

**Why it matters:** panel checks are the gate the whole house pattern leans on;
a parser bug fixed once should be fixed everywhere, not per copy.
