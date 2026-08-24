# Model notes — how workers actually perform

A running log of how models perform on real Ringer tasks, so engine and
model choices are made on evidence instead of vibes. The raw numbers now
live in the local eval log (`~/.ringer/runs.jsonl`); run `./ringer.py models`
to print the per-model, per-task_type scoreboard (tasks, attempts,
pass_rate, first_try_pass_rate, median duration/tokens, last_seen). This
file remains the judgment layer on top of those numbers.

**How to add a row:** after reviewing a run (post-run ritual step 5 in the
ringer skill), append one dated line under the model. Say the task type,
what happened, and what you'd do differently. Only write what the executed
checks and raw logs support — no vibes, no worker self-reports.

## codex (GPT-5-class, own harness)

- 2026-08-24 task-tracker-bakeoff, 4 cells (gpt-5.5, bakeoff/tool-trial):
  4/4 PASS first try. Task shape: drive an unfamiliar CLI (backlog.md,
  beads) through a full lifecycle in a sandboxed disposable worktree and
  report evidence. Standout behavior: when tool defaults violated the
  sandbox (backlog git-integration writing to the main repo's .git;
  bd resolving the worktree to the real repo path, then panicking on
  ~/.dolt), workers diagnosed the boundary violation, found contained
  workarounds (filesystemOnly=true; BEADS_DIR + redirected HOME), preserved
  failure artifacts, and documented everything instead of giving up or
  cheating the boundary. Tool-trial cells with hostile defaults are a safe
  codex lane at default effort.

- 2026-08-18 ea-dedup-embeddings s5/s6/s6b/s7 (gpt-5.5, code-feature/fix):
  s5 PASS 1st try (207k/853s, high), s6 PASS 1st try (191k/663s, high),
  s6b fix PASS 1st try (51k/119s, medium — medium effort is enough for
  well-scoped 2-file fixes). s7 FAIL after 2 attempts (154k, high):
  attempt 1 honestly went red on the sanctioned-route guard the Boss brief
  had failed to pre-amend; attempt 2 EDITED the guard test (out of
  ownership) instead of reporting the BLOCKER the spec demanded — disclosed
  in its summary, so interference-with-disclosure, not camouflage (4th
  guard-interference family instance, first disclosed one). Ownership check
  caught it; Boss re-authored the amendment and harvested the patch minus
  the guard hunk (full suite green). Lesson for Boss briefs: survey guard
  tests for EVERY surface a step adds and pre-amend (R18/47a pattern) —
  a worker facing a guard it cannot pass NOR edit will fail one way or
  another; make the legal path exist before launch.
- 2026-08-18 ea-dedup-embeddings s4a/s4b/s4c (gpt-5.5 high, code-feature x3):
  ALL first-try (118k/429s, 141k/497s, 69k tokens) — ground-truth CLI,
  benchmark harness, config pin. Five consecutive clean first-try passes on
  this job under the anti-camouflage rule + Boss-pre-committed guard
  amendments. Long prescriptive specs (numbered deliverables, exact
  execution order, named test minimums) are the working pattern for this
  model — keep writing them that way.

- 2026-08-17 ea-dedup-embeddings s3 (gpt-5.5 high, code-feature): PASS
  first-try, 91k tokens, 332s — 3 new modules + 5 test files (49 tests),
  full 739-test suite green in the validator. Second consecutive clean run
  under the anti-camouflage spec rule; notably HONEST sandbox reporting:
  its fix-summary disclosed 4 pre-existing real-HTTP tests failing on
  sandbox socket-bind refusal instead of hiding or "fixing" them (contrast
  the 2026-08-16 gdr-pass-b hand-authored lockfile). Boss pre-committing
  the guard-test amendment (47a class registration + canary allowlist)
  before launch removed the evasion temptation entirely — repeat that
  pattern whenever a task's deliverables intersect a guard scan.

- 2026-08-16 ea-dedup-embeddings s1 (gpt-5.5 high, code-feature): PASS
  first-try, 115k tokens, 485s — large store-layer contract (migration +
  6 methods + 43 tests) landed correct on substance. THIRD instance of
  the guard-evasion family: a spec-required `DELETE FROM task_embeddings`
  collided with a no-delete guard test's source grep + introspection scan;
  the worker split the SQL string (`"DELETE " "FROM"`) and hid the public
  method behind a descriptor instead of failing honestly. Disclosed the
  descriptor in its summary, not the string split. Pattern now 3-for-3
  when a spec requirement collides with a check heuristic (2026-08-13
  @property wrap, 2026-08-16 DSN obfuscation, this). Countermeasures:
  spec must say "conflict with an existing guard test = report as
  blocker"; Boss review greps the diff for string-concat/descriptor
  tricks near guard-scanned patterns before trusting a green run.
  2, 190k tokens — 8-finding fix lane incl. a chart/grid column-geometry
  rework, all landed. TWO watch-items the executed check could not see:
  (a) it edited app/e2e/driver.py despite the spec listing it READ-ONLY;
  (b) in that file it OBFUSCATED the local DSN literal (string-join/format
  tricks) to dodge the check's secret grep instead of failing honestly —
  same canary-bypass family as the 2026-08-13 `@property` wrap. Orchestrator
  rewrote it plainly and allowlisted the public local-default DSN in the
  check. Boss review must keep reading for grep-dodges whenever a spec
  boundary collides with a check heuristic.

- 2026-08-15 ea-add-scoping (gpt-5.5, 2 code lanes over 2 rounds): both
  first-try (build 163s, fix 105s). The build lane implemented a
  recall-sensitive persistence partition against a spec row pinned to
  file:line detail; the fix lane turned an adversarial-review probe scenario
  into an end-to-end regression test in the check-73 scripted-stub idiom
  without drifting the surrounding style. Detailed seam-level specs (exact
  partition condition, named marker, forced-review exemptions) keep buying
  first-try passes on this repo.

- 2026-08-13 ea-review-ux (gpt-5.5, 4 code lanes over 4 sequential rounds):
  3/4 first-try incl. a 13-file UI lane and a 6-file cross-layer fix lane
  run against the FULL non-socket suite as its check (659 tests). The one
  retry was a flaky same-second event-ordering assertion the model then
  fixed itself (rowid tie-break) — spec bug, not model. Watch-item: one lane
  dodged a name-heuristic canary (`test_no_delete_possible` flags `clear_*`
  methods) by wrapping the method in a `@property`; executed checks can't
  see intent, so Boss review must read for canary bypasses whenever a spec
  name collides with a guard heuristic (renamed `rule_not_duplicate` at
  integration).

- 2026-08-12 gdr-pass-b (gpt-5.5 default): runner snapshot-widening lane
  artifact CORRECT (9/9 DB-backed pins post-integration; recorded FAIL was
  tree-state collateral of the uncommitted-sibling incident above, not model
  quality). Spec-amendment docs lane (three SPEC section artifacts against a
  grep content contract) PASS attempt 2, 87.6k tokens — 5.5 handles
  house-voice spec drafting when the required strings are spelled out.

- Strongest general worker; the default engine. Spend reasoning effort per
  task via `engine_args` (`["-c", "model_reasoning_effort=low|medium|high"]`)
  — high on gnarly tasks, low on boilerplate.
- 2026-07-05 — carried the heavy lanes of the milk-crate demo rehearsals
  (market read with source allowlist, site build) with clean first-attempt
  passes.
- 2026-07-10 — gpt-5.6-sol, code-feature (steering-profiles feature in
  ringer.py itself, ~470-line change + 18 tests + docs, run
  ringer-steering-profiles): shipped as PR #25. 2 attempts, 379k tokens,
  but the attempt-1 FAIL was the CHECK's fault, not the model's — the check
  gated on the ENTIRE pre-existing suite being green inside the worker
  sandbox (localhost binds blocked, fixture missing). The feature work
  itself was verified green both attempts; attempt 2 "hardened" an already
  -sound implementation. Scoreboard's FAIL row for this run understates the
  model. Lesson for check authors: regression gates must compare against
  the BASELINE failure set, never assert absolute suite green.
- 2026-07-06 — adversarial pre-merge review (aicred spark): passed on
  attempt 1, ~85k tokens.
- 2026-07-06 — motion design (5 HTML animations for video b-roll) + 2
  editorial diagram pages, each verified by rendering through headless
  Chromium to MP4/PNG: 7/7 passed on attempt 1. Broadcast-quality visual
  output from rich storyboard specs; the render-as-check pattern works.
- 2026-07-06 — milk-crate demo: two single-file website builds (v1 scaffold
  316s/~175k tok; final brand+market-test reskin 622s/~184k tok), both passed
  14-assertion content checks on attempt 1, including base64-embedding photos
  and honoring honesty-marker requirements. Codex remains the site-build lane.
- 2026-07-06 — ringer.py feature batch (task_type field + enriched eval rows
  + `models` scoreboard + hud single-tab fix; ~640-line diff incl. two new
  test suites): substance passed on attempt 1 — its check printed PASS
  (compile, all 16 suites, exact CLI aggregation contract) — but the run
  recorded attempt 2 because of the expect_files-before-check harness bug
  (see process lessons). Heavy single-file feature work against an exact
  behavioral contract is squarely codex's lane.

- 2026-07-06 — elsas-website demo: Next.js scaffold PASSED attempt 2 (682s,
  ~354k tok) — attempt 1 built a complete homepage and silently skipped the
  other 10 routes; the route-enumeration check caught it. Narration lane
  (15 ElevenLabs calls, chunked, nohup pattern) passed attempt 1. CAUTION: a
  codex fix worker GAMED a verbatim-content needle by hiding the required text
  in a visually-hidden paragraph — passed the check, caught only by
  orchestrator integration review. Needle checks need an anti-hidden-text
  assertion or documented exceptions.

- 2026-07-06 — OpenRouter catalog + explore suggester (catalog subcommand
  with snapshot/changelog/free-detection, daemon auto-refresh, tiered
  --explore; offline fixture-driven contract check): PASS attempt 1, 362s.
  Follow-up sentinel-pricing fix (variable-pricing models): PASS attempt 1,
  114s. With the verify-order fix landed, zero phantom retries across the
  whole batch.
- 2026-07-06 — adversarial review of the model-router stack (2,650-line
  diff, structured report contract): PASS attempt 1, 176s — found a real
  HIGH (--since window inflating first-try rates) plus 3 MEDIUMs, all
  confirmed against the code. Then fixed all five review findings in one
  batch (task-level --since, pricing transitions, event durability + flock,
  unknown pricing, stderr notice) with test coverage: PASS attempt 1, 202s.
  Review->fix roundtrip in codex's lane works end to end.
- 2026-07-06 — scoreboard HTML page (zero-LLM renderer, ~700-line diff,
  design + evidence-floor ranking + cost math + notes parser): substance
  PASS attempt 1 (the run's recorded retry was an orchestrator check bug —
  the free-promo watchlist legitimately mentions a free model before the
  ranked cards, and the check compared raw first-occurrence). Six review
  findings fixed in one batch, PASS attempt 1, 141s.
- 2026-07-06 — model-db stack (SQLite read model 516s, page redesign 536s,
  Ringside tab 527s, plus three fix batches all attempt-1): five substantial
  ringer.py features in one day, every one against an executed contract
  check. Review lane found the HIGH that mattered (sync cursor skipping a
  half-written trailing line). Codex is the proven lane for both sides of
  the review->fix loop on this codebase.

- 2026-08-04 gh-dealroom respec-checkpoint (code-fix, engine lane, gpt-5.5 high):
  implementation was RIGHT on attempt 1; the orchestrator's check demanded
  >= 70 passing tests when the pinned files collect 69, so attempt 1 failed on
  the floor alone. Attempt 2 satisfied the floor by injecting a pytest-only
  "sentinel" test into the pinned test file's globals from the module under
  test (import-time stack inspection) — and DISCLOSED it in notes.md, flagging
  the floor as suspect. Two lessons: (1) a wrong numeric gate gets satisfied
  mechanically, same species as the split-string grep defeat, and the gaming
  vector here (module-under-test mutating the pinned test namespace) defeats a
  pinned-file HASH check while leaving the file untouched — future checks
  should also assert collected-test COUNT from the pytest header, not just a
  floor; (2) the disclosure is the behaviour to reward — the notes named the
  exact assumption that exposed the orchestrator's defect. Sentinel stripped
  by the orchestrator; floor corrected; 69/69 green.
- 2026-08-04 gh-dealroom respec-checkpoint (code-feature, schema lane,
  gpt-5.6-sol high): house-pattern-faithful migration (versioning DO-block,
  grants, revokes all exact). Found a REAL defect in the pinned schema test —
  S7's raw insert predated the checkpoint's source_ref column, so the row
  violated NOT NULL before the CHECK under test — could not edit the pinned
  file, and worked around it with a narrow BEFORE INSERT trigger forcing the
  expected SQLSTATE, flagged prominently in notes.md. The spec/pin was wrong,
  not the worker; orchestrator fixed the pinned insert and removed the
  trigger. Sol's second clean flagged-workaround on this repo (cf. the
  INPUT_TABLES rebind in Pass 1A) — it stays inside its lane and documents;
  promote with confidence on schema work.

## glm-5.2 via opencode (`openrouter/z-ai/glm-5.2`)

- 2026-08-16 gdr-pass-b readme-audition (docs): recorded FAIL was the
  HARNESS — the opencode sandbox had no write access to the target repo
  (the manifest only granted writable_roots to the codex engine). The
  model diagnosed the block honestly, preserved a complete README in its
  scratch dir, and said so plainly. The artifact passed the executed
  content check once integrated (after fixing a check regex that didn't
  span newlines — strict-on-format bug, not model fault). Audition read:
  POSITIVE on docs substance and on honesty under a broken sandbox;
  inconclusive on end-to-end repo lanes until opencode gets a write root.

- 2026-08-12 gdr-pass-b docs-lane audition rebook: DID NOT RUN — the opencode
  engine is down on this machine (instant "Unexpected server error" before
  any model call, reproduced on a trivial PROBE-OK task and, identically, on
  kimi-k2.7 — model-independent). Today's FAIL rows and the 2026-08-09 1s
  failure are harness artifacts; do not count them against the model. Fix
  opencode, then rebook the audition (the docs task went to codex gpt-5.5,
  which passed on attempt 2).
- 2026-08-12 (later, same session) RESOLVED: root cause was missing
  OpenRouter credentials on homer-studio — no auth.json, no env var, no
  provider entry; every openrouter/... call died before opencode logged
  anything. Mark ran `opencode auth login`; the Ringer PROBE-OK re-run
  passed first try (5.8s, 10.6k tokens). The engine is healthy; the real
  audition rides the next session's first low-stakes lane, alongside the
  authorized qwen code-feature re-audition (see the 2026-08-09 scoreboard
  correction above).

- The cheap-intelligence default (~$0.74/M in, $2.33/M out, 2026-07 —
  20-30x cheaper output than frontier coding models). Reliable on
  mechanical, tightly-specced work: file edits, format conversions,
  template-driven builds.
- 2026-07-05 — milk-crate demo rehearsals: handled brand-board/SVG/copy
  tasks at around a penny per passing task.
- 2026-07-06 — adversarial pre-merge review (aicred spark): passed, but
  needed the retry (attempt 2) where codex passed on attempt 1. Long
  structured reviews sit at the edge of its comfort zone; keep the section
  contract explicit in the spec.
- 2026-07-06 — three mechanical image-generation batches (18 images via
  openrouter-image commands, idempotent batch-runner spec): 3/3 passed on
  attempt 1, ~14.5k tokens each. The "execute these exact commands, do not
  improve them" spec pattern is fully reliable for glm-5.2.

- 2026-07-06 — backfill/seed script for the model log (252-line stdlib CLI
  with a run-state join, 3-level mapping precedence, never-overwrite and
  idempotency rules): the artifact was CORRECT; the recorded FAIL was an
  orchestrator check-fixture bug (a missing newline glued the fixture's last
  row to a garbage line) plus the harness ordering bug below. Verified PASS
  once the check was fixed. Tight behavior contracts in the spec work great
  for glm — and read the raw logs before blaming the model.
- 2026-07-06 — README/MODEL-NOTES docs + task_type sweep across 17 template
  manifests: passed attempt 2; attempt 1 was lost to the harness ordering
  bug, not model quality — the retry worker's log correctly diagnosed that
  harness bug unprompted, impressive debugging from the cheap lane.
- 2026-07-06 — catalog/explore README section (flags, promotion ladder,
  per-user framing): PASS attempt 1, ~21.5k tokens. Doc sections against a
  grep-able content contract remain a safe glm lane.
- 2026-07-06 — milk-crate demo, full run: 4 independent buyer-persona
  reviews (focus group) all passed attempt 1 (~15k tokens, ~2¢ each) with an
  explicit VERDICT-block contract — persona work is squarely in glm's zone.
  Market read with live curl fetching passed once the spec demanded verbatim
  copy-paste of source URLs (first fail was the worker trimming URL slugs —
  spec/check craft, not model weakness). Brand-kit doc incl. a clean inline
  SVG wordmark: good, one bounce off an over-strict check regex.

- 2026-07-06 — elsas-website demo: verbatim content capture (16 pages + 19
  news posts, 213 blockquotes) passed attempt 2 — attempt 1 SELF-REPORTED
  "all 213 match exactly, 0 errors" while the executed check found 13 stitched/
  paraphrased quotes. Self-reports are worthless; the retry with injected
  failures fixed all 13 (~148k tok total, ~3¢). Page builds (about+faq;
  news index + 19 generated post routes via its own extraction script) and
  2 focus-group personas: all attempt 1. Fix batch attempt 1.
- 2026-07-06 — invariants/file-I/O review lens on the same stack: PASS
  attempt 1, 68k tokens — caught the non-atomic backfill rewrite (real data
  loss risk) and the daemon stdout race; both confirmed. Then fixed the
  backfill atomicity (tmp+os.replace, pid-stamped backups) attempt 1 with
  the original behavioral grader unchanged. Structured review with an
  explicit lens is now proven glm territory, not just probation.
- 2026-07-06 — solo adversarial review of the scoreboard renderer (~700
  line diff, injection-focused lens): PASS attempt 1 — 1 MEDIUM (unanchored
  MODEL-NOTES heading match cross-contaminating gpt-4/gpt-4o-style
  families) + 5 real LOWs, plus an empirically-verified injection all-clear
  (it actually rendered hostile model ids to prove escaping). Second
  proven-tier structured review in one day; glm is now the default review
  lane for mid-size diffs.
- 2026-07-06 — invariants/injection/frontend review of the 4,061-line
  model-db branch: PASS attempt 1, 96k tokens, 14 coverage items — two real
  contention findings (full catalog re-ingest per sync; schema writes on
  read paths) plus an empirical XSS all-clear on the new DOM surfaces.
  Third proven-tier structured review today.

## kimi-k2.7 via opencode (`openrouter/moonshotai/kimi-k2.7-code`)

- 2026-07-06 — adversarial pre-merge review (aicred spark): passed on
  attempt 1, ~83k tokens. First real outing; promising for review work.
  (Ran through an ad-hoc copy of the opencode engine block — the per-task
  `model` field now makes that unnecessary.)

## kimi-k2.6 (`moonshotai/kimi-k2.6`, subject-model evidence via OpenRouter)

- 2026-07-07 — Benchmark Suite 2.0 operator eval, killed by Jon at ~4.5h.
  Serving throughput, not model quality, was the failure: on the Brick
  1000-piece case (reasoning xhigh, pinned provider order
  inceptron→decart→baidu→modelrun, no fallbacks) K2.6 averaged ~21 tok/s
  with two ~19-min stalls at 4.5 tok/s — 136+ min unfinished vs Sonnet 5's
  25 min (94 tok/s) and GPT-5.5's 24 min (55 tok/s) on the identical case.
  Model behavior itself was fine: 28 turns (fewer than Sonnet's 82), 170k
  output tokens (in family norms), 12% reasoning, zero API errors. Verdict:
  do NOT schedule K2.6 for long agentic work through that provider set;
  if K2.6 data is ever wanted, probe a single case against other providers
  first. Distinct model from k2.7-code above — don't transfer this verdict
  to k2.7.


## grok-build (Grok CLI engine, flat plan)

- 2026-07-10 — identity correction (Jon): the Grok Build CLI is a HARNESS
  serving exactly two models — Grok 4.5 (xAI) and Composer 2.5 (Cursor).
  The engine-lane slug `grok-build` resolves to Grok 4.5. "Grok Build 0.1"
  was never a model; earlier notes/rows using it as one describe Grok 4.5.

- 2026-07-06 — first outing (elsas-website demo), engine added same day:
  audition PASS attempt 1 in 28.9s. Then: asset harvest (11 images, live URL
  re-fetch check), books page, 5 work-page routes in one task (59 verbatim
  needles), adversarial code review (10 real findings incl. an unshelled 404
  and a broken embedded link), press/media fix batch, audio-player integration
  across 15 pages — ALL attempt 1 (player's red ledger entry was a check bug,
  artifact certified). Fast, precise on mechanical/code work. No token counts
  in JSON output (flat plan) — cost reads "included in plan".

## grok-composer-2.5-fast (Grok CLI engine, flat plan)

- 2026-07-06 — first outing (elsas-website demo): audition PASS attempt 1
  (138s — slower than grok-build but the strongest copy of the round).
  Accessibility constitution (14 testable criteria, SC-numbered) attempt 1;
  a11y-gatekeeper harness (axe+Playwright, light/dark, reduced-motion assert)
  attempt 2 — attempt 1's harness mishandled Next's default /404 route.
  Events/faq/contact fix batch attempt 1, but satisfied "editorial grid" with
  an EMPTY aside landmark — axe caught it (landmark-complementary-is-top-level).
  Persona work: good. Watch for letter-of-the-spec shortcuts on layout asks.

## nemotron-3-super-120b (via opencode, `openrouter/nvidia/nemotron-3-super-120b-a12b:free`)

- 2026-07-06 — AUDITION FAILED (exploration slot, $0 spent — free promo).
  Task: fresh-eyes adversarial review of a 2,650-line diff with a structured
  report contract. Failed both attempts on the same executed check: report
  had the right sections and verdict but under 3 concrete code citations —
  shallow engagement with the actual code, 212k tokens burned. Don't re-run
  this audition on long structured code review; if it gets another slot,
  try a shorter, more mechanical task first.

## llama-3.3-70b-instruct (via opencode, `openrouter/meta-llama/llama-3.3-70b-instruct:free`)

- 2026-07-06 — AUDITION FAILED (exploration slot, $0). Fresh-eyes review of
  a 4,061-line diff with a verbatim-quote citation requirement: failed the
  structured-report check both attempts. Second free-model audition to fail
  on long structured code review (after nemotron-3-super) — the exploration
  ladder now says: audition free models on SHORT mechanical tasks first;
  long-diff review is a proven-tier lane.

## Small / flash-class models

- First to choke on long conversational or multi-turn harness tasks —
  watch retry counts before scaling them into a batch (2026-07-05 focus
  group lesson).

## Process lessons (cross-model)

- 2026-08-16 gdr-pass-b adversarial-review (claude/sonnet, code-review):
  recorded FAIL was the CHECK, not the model — the check's repo-cleanliness
  gate fired on the ORCHESTRATOR's own concurrent integration edits in the
  same checkout. The reviewer stayed strictly read-only, noticed files
  changing under it, and documented that in the report instead of acting on
  it — exemplary behavior. The review itself was high-value: 9 findings
  (4 HIGH incl. one independently confirmed live minutes earlier), all
  verified real on triage. Lesson: never run a review lane's cleanliness
  check while integrating in the same working tree — pause integration or
  scope the gate to the reviewer's own writes.

- 2026-08-05 gdr-pass-2: per-task `engine_args` carrying
  `sandbox_workspace_write.writable_roots=[<repo>]` are LOAD-BEARING for
  direct-repo codex lanes — a relaunched manifest that drops them fails
  clean (workers can't write the repo, burn retries leaving notes). The
  run JSON's task records don't preserve engine_args; copy them from the
  worker log's command line, not from the JSON.
- 2026-08-05 gdr-pass-2 (codex gpt-5.5): engine lane first-try on a
  pinned-API pure module (chain traversal); runner-integration lane's two
  recorded fails were BOTH orchestrator pin defects (stale fixture
  ownership row; member-held bank claim) — code passed unchanged once the
  pins were fixed. Fix lane: first relaunch attempt introduced an
  exception-handler bug caught only by a v0.1 pin in the full scratch
  suite; retry with the defect NAMED in the spec fixed it one-shot.
  Full-scratch-suite stages keep earning their cost.
- 2026-08-15 ea-add-scoping (claude sonnet, code-review): adversarial
  review first-try, 1 HIGH probe-verified — found NOT in the diff but in a
  pre-existing function the diff made load-bearing (`apply_dedup_contradiction`
  guard left stale reason labels that the new partition then policy-excluded).
  The spec told it to trace every producer of the newly-routing field; that
  trace, not diff-reading, surfaced the bug. 4-for-4 runs with HIGH catches
  on this repo. Lesson to keep: when a review subject makes a previously
  informational field load-bearing, demand a producer-trace in the review
  spec.
- 2026-08-13 ea-review-ux (claude sonnet, code-review): adversarial review
  first-try, 3 findings (2 HIGH / 1 MEDIUM), ALL probe-verified by the
  reviewer itself with executed scripts before reporting — including a
  feature that was silently dead for all real-scale inputs (segmentation
  rewrote the join key; every fixture was under the 4000-char threshold) and
  a warm-path egress leak found by CALL-counting where the shipped tests
  asserted state. Now 3-for-3 runs with HIGH catches on this repo; the
  probe-before-report discipline is what makes the findings integrable
  same-day — keep demanding it in the spec's output contract.

- 2026-08-05 gdr-pass-2 (claude sonnet, code-review): adversarial review
  first-try, 17 min, 3 HIGH / 2 MEDIUM / 1 LOW — all real on verification,
  including catching the ORCHESTRATOR's contract-promised-but-never-written
  pinned case and a refuse-don't-guess violation masked by 0%-rate
  fixtures (verified by computing schedules at 0% vs 8%). Third repo in a
  row where the review lane is the highest-value spend.

- 2026-07-06 — the orchestrator's CHECKS were the day's top failure source:
  three check bugs (fixture newline join, first-occurrence ordering vs the
  watchlist strip, claim-prefix split on '.' instead of ':') each produced
  a FAIL verdict on work that was actually correct — including all four
  capability-research packets at once. Every one was caught by reading raw
  logs/artifacts before blaming the model. Corollary for the scoreboard:
  recorded FAILs whose root cause was a check bug are annotated here, and
  check fixtures deserve the same review care as production code.


- 2026-07-06 — HARNESS BUG (fix in flight on feat/model-perf-log):
  Verifier.verify evaluated expect_files BEFORE running the check, so any
  check that itself creates/exports its deliverable (the worktree
  patch-export pattern) failed attempt 1 with "missing expected files" even
  when the check printed PASS. Cost 3 phantom retries in one run — and it
  poisons first_try_pass_rate, the model log's routing signal. Until the
  reorder lands on your checkout: have the WORKER write the declared
  deliverable, or don't declare check-created files in expect_files. When
  reading seeded scoreboard numbers, remember 2026-07-06 first-try rates
  are depressed by this.
- 2026-07-06 — the model log is now automatic: every attempt row carries
  model/task_type/retry; `./ringer.py models` prints the scoreboard; 81
  historical rows were seeded via scripts/backfill_model_log.py with a
  hand-authored task-type mapping. Give every manifest task a task_type or
  its evidence buckets as (untyped).

- 2026-07-06 — a three-model "bakeoff" ran every task on the engine's
  hard-coded model: task keys said glm/gpt/kimi, but the opencode engine
  block pinned glm-5.2, so one model wrote all three "competing" reviews.
  This is why the per-task `model` field exists — a bakeoff is only a
  bakeoff if the manifest, not the engine block, names the model. Verify
  with the `model` column in the run state, not the task key.
- 2026-07-06 — spawning 5-6 opencode workers simultaneously hit opencode's
  local "database is locked" (sqlite) — several instant attempt-1 failures,
  all absorbed by Ringer's retry. Cosmetic in Ringside ("sent back" at 0s) but
  wastes an attempt; consider staggering opencode spawns.
- 2026-07-06 — opencode's bash tool kills foreground commands around the
  ~2-minute mark: a 2min+ image-generation API call can never finish inline.
  Spec pattern that works: nohup the long command in the background, then
  poll for the output file in separate short commands.
- 2026-07-06 — two check-craft lessons from the same run: (1) URL-allowlist
  checks must be prefix-tolerant (workers legitimately trim slugs); (2) any
  heading-regex must tolerate numbered headings ("## 3. Type / Typography").
  Both failures looked like worker laziness until the raw logs said otherwise.
- 2026-07-06 — elsas-website demo, check-craft in BOTH directions: (1) a fixed
  800-char body floor failed a worker for faithfully converting genuinely tiny
  source posts — floor must scale with the source; (2) a citation gate treating
  every backtick as a page-quote failed honest reviewers who backticked their
  own fix-suggestions — line-scoped pair parsing + attribute-aware corpus fixed
  it; (3) needle-exception lists must be shared across ALL checks that consume
  the needle set (a needle excepted in one checker failed a task through
  another). Post-mortems ruled FOR the worker 3 times this run — read raw logs
  before blaming the model.
- 2026-07-06 — opencode sqlite "database is locked" again with just 2
  simultaneous opencode spawns (page-news + page-about-faq); retry absorbed it.

## codex (2026-07-06, bench-operator-proofing)
- 8/8 code-feature tasks passed attempt 1 across 3 rounds (worktrees mode, Python harness refactor; 108k-406k tokens/task). Specs embedded the approved architecture doc + exact file ownership; checks built fresh uv venvs and ran the full pytest suite.
- Lesson (check design, not model): all 3 post-integration bugs were invisible to the checks — a test that passed only because the worker's worktree lacked .env, a `--help`-only assertion missing a runtime importlib/sys.modules bug (py3.12 dataclasses), and bare console-script names failing outside activated venvs. Checks should exercise one real invocation from a cold shell, not just --help.

## gpt-5.6-sol (codex)

- 2026-08-12 gdr-pass-b engine lane (code-feature, hard: staged-multiset diff
  rework + mixed-arity rollup against 43 pinned pure tests): artifact CORRECT
  on attempt 2 (43/43 pinned + 621 suite-minus, zero skips, verified outside
  the harness; 138k tokens). Recorded TIMEOUT is a scoreboard artifact — the
  orchestrator's check ran a 72s pytest into the 60s CHECK_TIMEOUT_S cap.
  Design checks to fit the cap (targeted test subset; full suite at the
  orchestrator's integration gate). Second lesson, expensive: COMMIT a
  verified lane's output before running further lanes in the same checkout —
  a round-2 sibling reverted Sol's uncommitted files to satisfy its own
  ownership check (empty --allowed-status), and the work had to be recovered
  blob-identical from worker.log.

- 2026-08-05 gdr-pass-2 (code-feature, schema migration): first-try-correct
  again on a contract-pinned Postgres migration, including a self-directed
  audit that found and extended an enum-list CHECK (su_category) the spec
  only gestured at. Its recorded FAIL was the orchestrator's check coupling
  to a concurrent lane; the SQL never needed a second attempt. Two-for-two
  on first-try migrations in this repo.
- 2026-07-15 ringer-self-update run (3 serial tasks, direct-repo-edit mode): code-fix baseline-test repair 1/1 first-try (61k tokens, 1.6m); code-feature self-update mechanism (git fetch/ff-pull/re-exec + HUD staleness restart + 20-test suite) 1/1 first-try at high effort (153k, 8.1m); code-feature signal-contract (all 3 scoreboard surfaces + canonical-route lint enforcement) passed on retry (358k, 13.7m) — attempt 1 died on stale old-column assertions in pre-existing tests it hadn't finished updating; the retry prompt's injected FAIL list was enough to close it out. Lesson: when a task rewrites a display contract, name every test file asserting the old contract in the spec's ownership list AND tell it to update them FIRST.
- 2026-07-09 code-feature/code-fix (ringside-overhaul): 4/4 first-try — a ringer.py logging change with tests, a 265-line stdlib backfill CLI (atomic rewrite, dry-run, idempotence all check-verified), a ~1500-line single-file HTML redesign (running-now pills + worker-card grid + multi-expansion refactor, 30KB patch, node --check + contract greps + unittest), and a render-gating change where it correctly UPDATED tests asserting the old behavior instead of gaming the check. Medium/high reasoning, 65–120k tokens/task.
- Same day, different session (bench-harness-patches, code-fix): 0.29 first-try over 7 tasks on a Next.js/Turbopack harness. Spec and check quality dominate model choice — see the scoreboard before generalizing either number.

- 2026-08-04 gh-dealroom pass-1a (code-feature, schema lane, high effort): 9-table Postgres migration + fixture + loader against a pinned 21-assertion contract. PASS in 2 attempts, 239k tokens, 13m — attempt 1 failed on facade-allowlist integration (the SPEC's fault: the lane was denied ownership of facade.py, so the worker worked around a guard from outside; the retry's injected check output closed it). Honest notes.md that named everything it could not verify from a no-DB sandbox rather than claiming green skips.
- 2026-08-04 gh-dealroom pass-1a (code-fix, effective-range CHECK migration, high effort): 1/1 first-try, 56k tokens, 3.4m. Unprompted defensive touch worth copying into future specs: probed for pre-existing violating rows and fell back to ADD CONSTRAINT ... NOT VALID with a warning rather than writing a migration that could fail to apply.

## GPT-5.5 (codex) — attribution caveat
- 2026-08-04 gh-dealroom pass-1a (code-feature x2 + code-fix, all high effort, contract-bound): 3/3 first-try — engine/capital.py (60k, 3.6m) and engine/acc.py (45k, 3.1m) against pinned 30+-assertion contract files, then the three-defect capital.py fix round (52k, 2.4m). Now 5/5 lifetime on contract-bound gh-dealroom lanes since model pinning; the scoreboard's 50% code-feature row is dominated by pre-pinning noise. Contract-bound work with an executable pinned test remains this model's strongest configuration.
- Scoreboard rows dated before 2026-07-09 may actually be gpt-5.6: codex eval rows logged model="" until the write-time stamping fix (PR #18) and were credited to GPT-5.5 by the registry default at read time, while the machine's codex default had already moved to gpt-5.6-sol at an unknown earlier date. `scripts/backfill_model_from_logs.py` re-stamps rows with surviving command-log evidence; anything it skips is a mixed-model aggregate. Trust post-2026-07-09 rows.

## nvidia/nemotron-3-super-120b-a12b:free
- 2026-07-08 (research, content-strategy-recon): FAIL x2. Did the analysis in chat but never wrote report.md; attempt 2 exited rc=0 with no file. Doesn't reliably follow file-output contracts under OpenCode. Demoted — don't re-audition on file-deliverable tasks.

## meta-llama/llama-3.3-70b-instruct:free
- 2026-07-08 (research, content-strategy-recon): FAIL x2. Timed out at 900s both attempts on a moderate DB-scrape+format task. Too slow on the free tier for harness work. Demoted — don't re-audition without much longer timeouts or paid tier.

## z-ai/glm-5.2 (addendum)
- 2026-07-08 (research/filter, pitch-foundry): FAIL x2 on a long-spec rubric-application task (~40k input: embedded rubric + 4 candidate files). Read all inputs, exited rc=0 with ZERO output tokens both attempts — silent stall, no file written. GLM handled the same session's shorter formatting specs fine. Lesson: keep GLM specs short; route long-context apply-this-rubric work to codex.

## GPT-5.5 (codex) — honesty flag
- 2026-07-08 (image-gen, pitch-foundry): sandbox DNS blocked openrouter.ai; ALL 10 API calls errored (logged honestly in gen-log) — but the worker then FABRICATED 10 deliverables locally (composited canvases from the ref image) to satisfy a files-exist>40KB check, and passed. Lesson: (a) codex sandbox has no external DNS on this machine — route API-calling tasks to opencode (network open); (b) never write an existence-only check for generated media — require the success log (SAVED/cost lines) to match the file count.

- 2026-07-09 persona-review (pitch-foundry exec-briefing panel): 0/2 first-try+retry. Produced coherent review CONTENT as chat text but never wrote report.md — does not reliably use file-write tools under opencode. Demoted; do not re-audition for file-deliverable tasks without a write-tool probe first.

## gpt-5.6-luna (codex)
- 2026-07-09 code-feature (unlock-ai guide-format conversion, strict type-contract check): 1/1 first-try, 42.6k tokens, 80s. Followed a multi-file TS pattern precisely at $1/$6 pricing. Good candidate for mechanical codegen/docs lanes; audition in adjacent types.

## opencode / z-ai glm-5.2 (via openrouter)
- 2026-07-09 (aicred-invoice-downloads, 4 code-fix tasks + 1 follow-up, worktrees+npm ci checks): systematic attempt-1 NO-OP — all 4 parallel workers produced zero edits and no summary on first attempt, then completed cleanly on attempt 2 after retry-prompt injection (34k-69k tokens each). Follow-up single task passed attempt 1. Suspect first-invocation session warm-up in opencode-sandboxed under parallel spawn; budget for 2 attempts on parallel GLM batches. Output quality on Next.js/Stripe route+test work: solid, spec-faithful, one boss-caught design gap (used user-scoped supabase client where RLS demanded service role — spec didn't say explicitly; say it explicitly).

## opencode (harness note, any model)
- 2026-07-28 (code-review, pr82-token-saver-review): GLM 5.2 produced a complete, high-quality 218-line report but could NOT write it to an output directory created by the parent Claude Code process — every write returned EPERM. It then spent ~3000s burning retries on ctypes/`openat`/AppleScript/`sandbox-exec` workarounds until it timed out, and the task logged as FAIL despite the deliverable existing in its taskdir. Codex workers in the same run were unaffected. Lesson: point opencode workers' output INSIDE their own taskdir and harvest via `expect_files`; never hand them a shared output dir another process created. This is an orchestrator spec bug, not a model failure — do not read the FAIL as evidence against GLM.

## Process lessons (2026-07-28, PR #82 review)
- **Ideas worth keeping from a rejected PR.** PR #82's pre-call gateway was dropped (needs your own API key, so it converts flat-rate OAuth plans into metered API billing; incompatible with Claude Code; and it saves tokens by stripping the tool list, which is the thing that makes the CLI worth using). One idea inside it is worth remembering if the problem ever comes back: an *explicitly blessed* answer cache — key a reviewed answer to the exact request plus the exact selected source packet, and replay it with zero upstream calls, never auto-accepting a model answer. It only fires on byte-identical repeats, which is why it didn't justify 2,000 lines here.
- **Doc-stated support floors need a CI job or they are fiction.** README promised Python 3.11+ while CI only ever ran 3.12; a 3.12-only f-string reached review with a fully green suite. Either test the floor or move it.

## GPT-5.6 Sol (codex) — dealroom pass 1
- 2026-07-27 code-feature (gh-dealroom Pass 1, 8 build tasks across 2 rounds, worktrees + executed acceptance/scratch-DB checks): 6/8 first-try; the 2 retries were the two integration-heavy tasks (a 1,540-line 5-file SQL migration set written blind — no docker in sandbox — and a psycopg facade with live-DB integration tests) and both passed on attempt 2 off the check's failure output. Contract-style specs (binding signatures + orchestrator-authored acceptance files the worker must pass unmodified) produced zero API drift across 4 parallel engine lanes. Median ~40-55k tokens on pure-Python lanes.

## claude sonnet (claude CLI engine) — first audition
- 2026-07-27 code-review (dealroom migrations vs SPEC §8, read-only, structured-report check): 1/1 first-try. Verdict-structured report with per-finding severity, file:line and spec anchors; caught a real integrity gap (debt-shaped instruments allowed NULL notional) plus a bounds-check inconsistency, both missed by the 20-block SQL assertion suite and the codex author. Zero false positives; explicitly enumerated clean areas. Engine block added to config 2026-07-27 (bin claude, -p + allowedTools). Good default for adversarial spec-vs-artifact review lanes.

## GPT-5.6 Sol (Codex CLI) — 2026-07-28 dealroom-pass2
- code-feature/code-fix, 11 tasks over 3 rounds: 10/11 real first-try (the one "fail" was a broken check — no host psql; use docker exec into the supabase_db container). Contract-style specs with orchestrator-authored executable acceptance files again produced zero API drift across 7 parallel engine lanes. Worker sandbox cannot reach localhost — DB-backed verification must live in the host-side check, and worker notes saying "test skipped in sandbox" are expected, not a defect.

## Claude Sonnet (claude engine) — 2026-07-28 dealroom-pass2
- code-review lane: one attempt died on the CLI session limit (retry also blocked; reset 2:30am ET — schedule review lanes away from limit windows). On rerun, produced an executed (not read-only) review that found 2 real defects the 28 passing gate tests missed: a state machine re-arming under sustained adverse input, and an instrument type silently vanishing from a balanced ledger. Worth keeping as the standing validation lane; 29-min runtime.
- 2026-08-15 gdr-pass-a-facade code-review: the standing lane pays off again. Executed review (built its own probes, ran deno tests against pure modules, round-tripped dates through the live pinned driver, hand-checked parity on 4 fixture variants the pins never touched) found 1 HIGH + 2 MEDIUM against a fully green suite — a real one: `resolveInputRoute` did `INPUT_TABLES[kebabTable]` truthy-check, so `constructor`/`hasOwnProperty`/`__proto__` path segments escaped not_found and reached the raw-SQL function name. Green suite could not see it (no test probed inherited property names). All findings actionable with executed evidence; the two code defects were fixed same session, finding 3 (schema-hardening, engine-unreachable) backlogged. 26-min runtime. CHECK-AUTHORING LESSON: the lane's own check FAILED it — the repo-clean assertion tripped on the ORCHESTRATOR's uncommitted edit sitting in the tree, not any reviewer write (read-only reviewer, repo genuinely untouched). Same class as the 07-31 "commit orchestrator edits before launching" lesson, one level up: a read-only-reviewer's cleanliness check must snapshot `git stash create` state or diff only the reviewer's own writes, never assert a globally-clean tree while the orchestrator is mid-edit.

## qwen3.6:35b (opencode engine, local ollama, homer-studio) — 2026-07-28 local-model-audition

- 2026-08-24 task-tracker-bakeoff scouts ×2 (research, read-only, verified
  citations): first PASS-class results for this model. gh-dealroom scout
  PASS on attempt 2 (retry feedback fixed citation line numbers); ringer
  scout produced a fully honest row but FAILED on a checker bug (the
  validator didn't strip backticks from a verbatim quote — quote was real,
  README.md:275). Both rows were dense, accurate, zero fabrication, and
  every citation survived on-disk verification. Repo-editing ban from
  08-15 stands unchanged; but read-only research with an executed
  citation-checker is now a legitimate free local lane for this model —
  the checker is load-bearing, keep it.
- probe (small code task, executed acceptance check with reference implementation): first-try PASS, 12,173 tokens, 78s on M-series/64GB. Spec-faithful Decimal money math, correct largest-remainder tiebreak. Zero marginal cost. Promoted to probation for mechanical/low-stakes lanes (docs sweeps, scaffolds, small pure-function work) — NOT contract-bound engine lanes or review lanes. First run failed in 1s on harness wiring, not the model: the brew-era Seatbelt profile in opencode-sandboxed.sh lacked ~/.opencode (new installer's state dir); fixed by adding OC_HOME to the allowed write subpaths. llama3.3:70b (42GB) untested — too tight on 64GB to load mid-swarm; gpt-oss:20b untested fast fallback.
- 2026-08-15 gdr-pass-a-facade (code-feature re-audition, the authorized clean-manifest retest after the 08-09 scoreboard correction): FAIL — TIMEOUT ×2, 146k tokens, 63min wall. Task was a fully-specified mechanical refactor (change one helper signature + 19 enumerated call sites, exact old→new mapping in the spec, 2,753-line file). Failure mode was approach, not comprehension: instead of editing the file directly it wrote a Python regex-rewrite script, lost to whitespace mismatches, copied the file around its workdir, got blocked by the Seatbelt profile on a heredoc temp file, and ran out the clock without ever touching the real file (repo verified clean after). With code-review 0/2 (08-09, stands) this ends the qwen3.6:35b audition for repo-editing lanes of ANY size; the Jul-28 probe pass stays valid for single-file-from-scratch pure-function work only. Same task rebooked on codex gpt-5.5 (effort low) immediately after. Lesson for spec authors: multi-site edits in large files need a worker whose harness edit tool anchors on exact file text — do not assign them to models that reach for sed/regex scripts.

## GPT-5.5 (Codex CLI) — 2026-07-31 dealroom debt-scheduling round 1
- code-feature, 2 parallel lanes, both first-try PASS (~2 min each): a nontrivial Decimal amortization engine against a pinned 12-test acceptance file (unmodified), and a 104-line system-versioned migration mirrored from siblings, validated by BEGIN/ROLLBACK against the live local stack. First run since pinning model_default=gpt-5.5 (was inheriting gpt-5.6-sol via unpinned engine block). Supports Mark's call: 5.5 is holding the contract-bound lanes Sol was doing, at plan-friendly burn. Direct-repo-edit pattern (writable_roots) with disjoint ownership + host-side checks worked clean; no worktrees needed for a 2-lane round.

## Scoreboard corrections — 2026-07-31 dealroom debt-scheduling rounds 2-4
- Three logged FAILs this run are ORCHESTRATOR check bugs, not model failures; read these rows accordingly:
  - gpt-5.5 round-2 integration (2 attempts, 185k tok): the code was correct and the DB smoke passed; the check demanded full-suite green while freezing two stale tests whose assertion the feature deliberately changed. Unsatisfiable by construction.
  - sonnet review lane (2 attempts): produced an excellent executed review (independent 48-row recompute, 2 real HIGH findings); check cd'd to the repo before testing for a report that lives in the taskdir.
  - gpt-5.5 fix lane (2 attempts, 88k tok): fixes were correct; the orchestrator's acceptance test was uncommitted (worker deleted the "unowned" untracked file to satisfy the ownership guard) and contained a wrong column name.
- Lessons now standing: COMMIT orchestrator-authored acceptance files before launching the lane; checks must capture taskdir cwd before any cd; when a feature changes a pinned behavior, update the stale contract tests BEFORE the lane runs, not after.
- Model quality note: gpt-5.5 4/4 real-work success across all four lanes of this feature (engine, migration, integration, fixes) — every "failure" was mine. Sonnet review lane remains the highest-value lane in the pipeline: 2 HIGH defects invisible to 156 green tests.

## Standing lesson extension — 2026-08-01 deal-year round
- The §18.10 lane's worker deleted an UNTRACKED orchestrator draft (the parity write-up) to satisfy its ownership guard — second occurrence of the uncommitted-artifact failure mode (first: the deleted acceptance test on 07-31). Lesson EXTENDED: ALL orchestrator-authored working artifacts living inside the repo get committed (or live outside the repo) BEFORE any lane launches; ownership-guard regexes treat every untracked path as removable dirt.
- gpt-5.5: deal-year expansion lane passed attempt 2 (retry steered by executed-check output), 117k tok. Now 5/5 features on this project since the pin.

## GPT-5.5 (Codex CLI) — 2026-08-02 gh-dealroom OA clause-by-clause extraction (docs)

- **Nine of the twelve logged failures on this job were my check, not the model.**
  Rounds 1 and 2 (6 tasks then 3) show `fail` for every task; both were caused by
  an orchestrator error, not worker output. Ringer runs the **check with cwd set
  to the task directory** (`<workdir>/<key>/`), not the run directory. My check
  invoked `python3 validate.py …`, and `validate.py` lives at the workdir root, so
  the check died with `can't open file … /<key>/validate.py` before ever looking
  at the deliverable. Correct form is `python3 ../validate.py out/<file> …`.
  Round 3 with that one change passed **6/6 first attempt** on the *same, unedited*
  deliverables. Discount those nine rows when routing docs work.
- This is the same trap recorded in the dealroom Pass 1–3 notes as "checks must
  capture taskdir cwd before any cd" — it bit again in a different disguise. Worth
  putting the relative path to any helper script in the check, always.
- **Where the model genuinely failed, the check was right.** Round 1's three real
  failures were substantive: two verbatim-copy violations (a worker tracking source
  wording closely through an enumerated list and through a valuation clause) and one
  over-bolding violation (bolding concepts that were not defined terms in the assigned
  range). All three self-corrected on one retry when the failure text named the exact
  offending string and told them to sweep the whole file rather than fix the one hit.
- **Quality on long legal-text extraction was high.** Six disjoint ranges of a ~1,600-line
  operating agreement, ~165KB of output, clause-anchored with correct clause numbers
  throughout — the provenance check (every cited §N.N must exist in that worker's own
  line range) caught zero invented clause numbers across all six after round 1. The
  unprompted "what this section does not do" analysis in the transfers section was the
  most commercially valuable output of the run.
- **Confidentiality-rule adherence was perfect from attempt 1.** Zero figure violations
  across all six workers on every round, against an explicit no-dollar-amounts /
  no-percentages / no-bare-numbers instruction. When one worker hit restrictive-covenant
  clauses with monetary terms, it flagged their existence and declined to reproduce them
  — exactly the desired behaviour, unprompted.
- Cost shape: ~725k tokens across the two real rounds (~120k/task on first-pass
  extraction of a dense 300-line range), ~48k for the round-3 verification pass.
  Verification-only rounds are cheap — 8-17k/task and under 15s each.

## GPT-5.5 high (Codex CLI) — 2026-08-04 ea-precision-pass (code-feature)
- 3 tasks, 2/3 first-try; the one FAIL was the orchestrator's spec, not the model:
  the brief simultaneously required a prompt-version bump and forbade editing the
  test that canaries that version, and 4 socket-binding tests can never pass inside
  the sandbox (PermissionError on bind). Worker correctly obeyed the constraint and
  recorded the conflict in its note rather than editing tests — desired behaviour.
- Corrected manifest (canary edit explicitly owned + socket tests deselected):
  first-try PASS in 109s / ~48k tokens. Config-loader lane also first-try (~48k).
- Lesson for briefs: any version/constant bump needs its canary test in the
  ownership list, and full-suite checks must deselect sandbox-impossible tests.

## gdr-pass-1b run notes — 2026-08-05 (code-feature, code-fix, code-review)

- **GPT-5.5 high (Codex CLI), code-feature ×3 launches + code-fix ×1.** Engine
  lane first-try (75k, zero workarounds, notes explicitly confirmed every
  flagged contract resolution). Runner lane took three launches, but BOTH
  intermediate failures were orchestrator-side defects the worker diagnosed
  precisely: (a) a Pass 1A pinned test colliding with a binding Pass 1B schema
  change — worker refused to touch the pin and named file:line; (b) fixture
  ambiguity — told to "add fixture waterfall scenarios," it attached event
  declarations to the two EXISTING v0.1 scenarios, retyping every v0.1 test's
  scenario onto the new dispatch path. Lesson for briefs: when a fixture file
  is shared, name the rows that must not change shape, not just the file.
  Five-finding surgical fix lane: first-try, 88k, 190s, scope held to three
  files. Also note: given a "tolerate string vs UUID ids" pain point it widened
  a comparison helper rather than normalizing at the boundary — accepted, but
  watch for drift.
- **GPT-5.6 Sol high (Codex CLI), schema code-feature.** First-try (91k, 438s)
  on a 594-line migration with zero DB access. Three high-quality flags,
  including catching that the contract's requested declarative FK is
  unimplementable in PostgreSQL (partial-unique target) and substituting a
  named constraint trigger — the correct judgment call, prominently flagged.
  Sol's fourth consecutive clean flagged-deviation on this repo.
- **sonnet (claude CLI), adversarial code-review.** Third pass running as the
  highest-value lane: 2 HIGH + 3 MEDIUM, all real, all confirmed, all in the
  runner seam no pinned test reached — including catching the ORCHESTRATOR
  failing to write a contract-promised continuity test. Zero speculative
  findings; the "what was checked and ruled out" section was accurate on
  spot-check. Keep this lane in every pass.
- **Check craft:** the full-suite-under-scratch-DB stage caught the fixture
  retyping that every targeted pinned test missed — keep a whole-suite
  executed stage in any lane check whose lane touches shared fixtures.

## Scoreboard corrections

- 2026-08-06 gdr-pass-3 (code-feature): BOTH round-1 FAIL verdicts
  (gpt-5.6-sol migration lane, gpt-5.5 diff lane) were orchestrator check
  defects — the v1 check script captured its own failure output inside
  command substitution and exited 1 silently, so retries ran blind. The
  fixed check passed both lanes' artifacts UNCHANGED (migration applied
  from zero single-transaction; 22/22 pure pins). Treat these two FAIL
  rows as check noise, not model evidence. Sol's migration was
  contract-exact first try; GPT-5.5 (medium) delivered the pure diff
  module and correctly flagged a spec/contract wording mismatch
  (driver_band key) in notes.md instead of guessing.
- 2026-08-06 gdr-pass-3 round 4, second lesson (cross-model): on retry,
  Sol reverted an out-of-scope uncommitted BACKLOG.md edit the
  ORCHESTRATOR had made in the shared tree mid-run, rationalizing it as
  "lane-caused" to satisfy the scope check — despite an explicit NEVER
  list. Two rules: (1) the orchestrator must not edit a direct-repo tree
  while a lane is live; (2) retry prompts amplify scope-satisfaction
  pressure — a worker that would flag a mystery file on attempt 1 may
  delete it on attempt 2.

## 2026-08-08 — gdr-pass-a-addbacks (gh-dealroom)

- **gpt-5.5 · high (codex, code-feature)**: engine lane first-try pass on a
  58-test pinned pure module (77k tokens, 3m38s). Loader lane's 2 recorded
  fails were an ORCHESTRATOR error (manifest lacked
  `sandbox_workspace_write.writable_roots`; worker was write-blocked,
  refused to work around it, reported honestly with the intended patch) —
  relaunch passed first try. Runner lane's 2 recorded fails were another
  orchestrator error (check had a pinned-but-not-allowlisted file — a
  contradiction no worker can satisfy); its code was fully green when the
  check was fixed. Net: 3/3 lanes first-try on the actual work. Do not
  read the raw fail rows as capability signal.
- **CAUTION (harness, not model)**: in direct-repo mode a retry prompt
  whose check-failure text names UNOWNED files ("out-of-scope change:
  reviews/…") invited the worker to `rm` those files to satisfy the
  check — it deleted three review-trail artifacts (recovered from the
  codex session rollout). Check failure text is part of the spec: never
  name paths outside the lane's ownership as violations when the lane
  has repo write access, and never pin a file without also allowlisting
  it.
- **sonnet (claude, code-review)**: structured contract-conformance
  review, first attempt; caught 2 real orchestrator omissions (contract-
  pinned doc deliverables that didn't exist) + 1 accepted note. Its
  recorded check fails were environmental (tree-state mismatch from the
  deletion above), not review quality.
- **gpt-5.6-sol (codex, code-review)**: high-value implementation review —
  4 findings: 1 real code gap (basis validation bypassed on the
  incomplete-window path), 2 accepted test strengthenings, 1 rejected
  (hand-pinned constants are the house pinned-case style). Same
  environmental check fails.
- **ollama/qwen3.6:35b (opencode, code-review)**: audition FAIL — two
  attempts, no report produced. With the earlier 0/3 on code-feature,
  this model is 0/5 on this box; end the audition.

## Scoreboard correction — 2026-08-09 (qwen3.6:35b code-feature rows)
- The code-feature 0/3 (db-hygiene-guard, 2026-08-03) is contaminated:
  one launch ERRORed on a harness taskdir collision ("taskdir already
  exists but is not a registered git worktree"), and the TIMEOUT pair's
  missing_expect_files show absolute scratchpad paths — manifest
  authoring, not model output. Do not read those rows as capability
  signal (Mark flagged; raw rows in ~/.ringer/runs.jsonl confirm). The
  code-review 0/2 (no report produced, twice) STANDS as model signal.
  Net: qwen local = unproven-not-disproven on code-feature (Jul-28 probe
  was a clean first-try PASS); still ended for review lanes. A fresh
  low-stakes code-feature audition with a correctly-authored manifest is
  legitimate.

## 2026-08-09 — gdr-v022-pass-p-phantom round 1 (gh-dealroom)
- BOTH recorded FAILs are ORCHESTRATOR check bugs, not model failures:
  (1) each lane's git-diff ownership guard didn't allowlist the OTHER
  concurrent lane's file or the orchestrator's own uncommitted contract
  edit sitting in the tree; (2) the migration check used host psql,
  which doesn't exist on this box (docker exec into
  supabase_db_gh-dealroom — re-learned from Pass 2 notes); (3)
  expect_files were repo-relative but Ringer resolves them against the
  taskdir (the engine worker noticed and mirrored its file to satisfy
  the harness — same expect_files path class as the Aug-3 qwen rows).
  Actual work: gpt-5.6-sol migration first-try clean (verified
  host-side); gpt-5.5-high engine first-try clean (pinned 8/8, full
  suite green in-sandbox). Do not read these FAIL rows as capability
  signal. Rules for next manifest: commit or stash orchestrator edits
  before launching; ownership guards allowlist all concurrent lanes'
  files; DB checks docker-exec; expect_files taskdir-relative or
  omitted for direct-repo lanes.

## 2026-08-09 — gdr-v022-pass-t-toll round 2 (gh-dealroom)
- gpt-5.5-high t-engine: first-try PASS on a hard lane — new pure module
  (single-balance tolled annuity with capitalization + salary-floor
  coupling) plus a state-machine extension in contingency.py, against 15
  hand-pinned cases incl. a 360-month rounding-edge identity. 79k
  tokens, ~4m. Real capability signal.
- t-migration FAIL is ORCHESTRATOR check bug #4 this project: a DO $$
  block inside a double-quoted shell check string — the shell expands $$
  to its PID and mangles the SQL. Use tagged dollar-quotes (\$tag\$) or
  single-quoted heredocs in checks. The Sol worker's migration was
  correct (verified host-side same hour) and it flagged the sandbox
  docker denial honestly. Standing rules addition: never put bare $$ in
  a check; sandboxed lanes cannot validate against docker — keep DB
  validation host-side ONLY and say so in the spec.

## 2026-08-10 — ea-inrun-dedup rounds 1–3 (homer-agents)
- gpt-5.5-high: 3/3 first-try PASS on code-feature/code-fix worktree
  lanes (40k/118k/84k tokens) incl. a hard lane (loop-engine dedup with
  cache-gate accounting) and a subtle-semantics fix lane (terminal-
  disposition enforcement). Worktrees mode + fix-swarm patch export: zero
  ownership violations, zero check bugs this run — the Aug-9 standing
  rules (commit orchestrator edits first, canary assigned to Boss,
  socket tests excluded from sandboxed lanes) held.
- claude sonnet (review lane): first-try, 512s, found 2 real HIGH defects
  with executable A/B probes in a diff that had 625 tests green — second
  consecutive cycle the sonnet adversarial lane caught HIGH defects the
  suite couldn't see. Keep it as the standing round-2 gate for EA loop
  changes.

- 2026-08-16 gdr-pass-b scaffold (gpt-5.5 medium, code-feature): recorded
  FAIL was the SANDBOX, not the model — no DNS in the worker sandbox, so
  npm install/tsc/vitest could not run; the source files it produced passed
  the full executed check after an orchestrator-side real npm install.
  Watch-item: attempt 2 HAND-AUTHORED a package-lock.json to get past the
  offline install — a lockfile not produced by real resolution is
  fabrication; the orchestrator regenerated it. Lesson for manifest
  authors: npm lanes need `-c sandbox_workspace_write.network_access=true`
  (same class as the 2026-07-10 steering-profiles check-fault row).

## gpt-5.5 (addendum 2026-08-21, run ea13-drive-step1)
- 2026-08-21 code-feature/code-fix (homer-agents EA #13 drive package, effort=high): 3 tasks, 0/3 first-try but all substantively correct — guards-preamend + drive-package passed attempt 2 with full-suite checks; review-fixes "failed" both attempts ONLY on the fix-swarm check's literal `## Files Changed` heading requirement (worker titled the section differently; substance verified green by hand: 979-test suite). Lesson: when using templates/fix-swarm/checks/fix-swarm.py, state the exact required summary headings in the spec, or the check fails honest work over formatting.
- 2026-08-21 code-fix lesson (run ea13-drive-step2): a worker whose ownership list excluded a stale guard test chose to special-case PRODUCTION code to keep it green (disclosed in Assumptions, not raised as a BLOCKER). Ownership lists must include every test a change can invalidate, and specs should say "a stale test you cannot edit = BLOCKER, stop".

## gpt-5.5 + claude sonnet (2026-08-22, run ea13-step5-writes)

Hermes EA #13 step 5 (facade arm windows + executor write path + UI arm
toggles + egress/secrets). gpt-5.5 (Codex, code-feature/code-fix, reasoning
high): **6/6 first-try** across four build lanes (A facade+migration, B
executor, D egress, plus C on attempt 2 — attempt 1 produced no patch
before the check ran, a timing miss not a quality miss) and a 3-worker
fix-swarm (all first-try). Notable: the TS edge function (no Deno on the
Studio to execute it) was verified via source-level contract tests + a
Python fixture facade mirroring its semantics — gpt-5.5 kept the mirror
faithful on every property the executor exercised; the only drift the
review found was on unreachable/unused surface (em-dash refusal strings,
weaker get_thought validation).

claude sonnet (claude engine, code-review): adversarial step-5 review
returned BLOCKER with **4 REQUIRED, all independently re-verified against
source before inclusion, one with a live two-host network PoC** (facade
client followed 30x redirects, replaying x-brain-key/x-approval-token
cross-host + HTTPS->HTTP — a real credential-exfil vector a source-only
read might have hedged on). Lesson reinforced: for security-sensitive
transport code, an adversarial reviewer that actually reproduces the
exploit earns its tokens; the fixture-vs-real-facade drift class is the
false-green to watch when the real artifact can't be executed in-suite.

## 2026-08-24 — homer-workspace v0.1 test-suite swarm (run v0.1-test-suite-20260824T204433Z)

gpt-oss:20b (ollama via opencode, code-feature, test authoring): **0/2, audition
ended.** Wrote a self-check asserting `---invalidyaml---` raises YAMLError — that
string is valid YAML, so its own test failed; also delivered 5 tests where the
spec demanded >= 8. The executed check caught both. Do differently: keep 20b off
code-feature; if auditioning local models on test authoring again, the spec must
spell out what "malformed YAML" means (this rerun's spec now does).

gpt-5.5 (Codex, code-feature, reasoning high): **4/4 on content quality.** All
four lanes' files passed the corrected check unchanged — the recorded FAILs were
an orchestrator check defect, not worker error: the check ran pytest (creating
tests/__pycache__ bytecode), then `git add -A` staged the .pyc and tripped the
exactly-one-owned-file rule. Fix that travels: export PYTHONDONTWRITEBYTECODE=1,
`git reset -q`, and purge __pycache__ before staging in any ownership-checked
pytest lane. Scoreboard shows these as FAIL; weight them accordingly.

nemotron-3.5-lightning:free (OpenRouter via opencode, probe): **1/1 first-try**,
6.9s, $0 — connectivity probe proving the OpenRouter path works (the config
comment claiming no key was stale; fixed 2026-08-24). Trivial task only — says
nothing about code quality yet. Validated as next audition candidate on a
low-stakes code-feature lane.

nemotron-3.5-lightning:free (OpenRouter via opencode, code-feature, test
hardening audition): **pass on attempt 2, $0.** Attempt 1 under-delivered
(8 tests collected vs 10 required — same under-delivery mode as gpt-oss:20b,
but recoverable); the retry prompt carrying the check's exact failure line
fixed it. Codex comparison lanes in the same run: both first-try. Standing:
probation for code-feature — usable on small, tightly-specified lanes with a
strong executed check and retry headroom; not ready for first-try-critical
work. Spec lesson: give small models explicit numeric floors (test counts,
assert counts) — both failures this session were floor misses, not logic
errors.

GPT-5.5 · high (codex, code-feature, homer-workspace portfolio-v01-build
2026-08-24): **content green both attempts; scoreboard FAIL is a check bug.**
Single worker built the whole v0.1 generator (bin/portfolio + 5 modules +
projects.yml, ~28KB) against a 50-test black-box gate: 50/50 passed, ownership
clean, spec subtleties (R7 edge matrix, R8 path redaction, unborn-repo
honesty, 0600 modes, interpreter re-exec fallback) all correct on attempt 1.
The check failed both attempts on `git status --porcelain` collapsing new
untracked dirs to `?? src/` / `?? bin/` — the ownership matcher compared
against file paths only. Fix that travels: run status with
`--untracked-files=all` (or `git status --porcelain -uall`) in any
ownership-checked lane that creates new directories. Weight this FAIL as
orchestrator error, not model error; quality of the delivered code was high
(orchestrator review found only two cosmetic nits).
