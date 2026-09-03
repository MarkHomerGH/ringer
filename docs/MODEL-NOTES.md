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

- 2026-08-26 ea13-step7-prep rounds 3-5 (gpt-5.5, code-fix, medium): 2/2
  first-try (88k/220s; 58k/132s) on production-incident fixes. Sonnet
  review lane earned its keep decisively: BLOCKED the first metadata fix
  with two REQUIRED findings, both reproduced via two-run cache-sharing
  probes the fixture suite couldn't see (NULL-clobber of repaired rows on
  mixed batches; value[:10] garbage-date fallback) — a fixture-green patch
  that would have silently regressed the exact production repair it
  shipped for. Review-then-fix loop: BLOCKED → fix lane first-try → CLEAR
  properties verified locally. Sonnet review on data-durability surfaces:
  standing recommendation.

- 2026-08-25 ea13-step7-prep, 1 task (gpt-5.5, code-feature, medium): PASS
  1st try (124k/268s). Two-part task (store-join enrichment in an existing
  stage + CLI/config wiring in a 650-line driver) with an 8-test floor
  across two files — no floor gaming, correct one-shot discovery of the
  canonical schema_version from shipped tests, honest sandbox-failure
  reporting (4 socket-bind fails named as environmental, confirmed green in
  the check env). gpt-5.5 medium now 4/4 first-try on pinned single-lane
  EA code-feature tasks; medium stays the default effort for this shape.
  Companion sonnet review lane (code-review, 458s): CLEAR with probe
  evidence — reproduced the step-6 mutation-BLOCKER hypothesis and ruled it
  out empirically, surfaced 1 real coverage gap (isinstance-only assertions
  on composed clients). Sonnet review lanes continue to earn their cost on
  gate-chain/credential surfaces.

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
- 2026-08-26 v03-desk-spec-review (code-review, cross-model spec review round 1): scoreboard FAIL x2 is an ORCHESTRATOR CHECK BUG, not a model failure — the check used workdir-relative paths and a bare `git status` guard, but Ringer runs each task in its own subdirectory, so the correctly-written deliverable landed at `<task-dir>/reviews/...` and the untracked task dir tripped the "nothing else modified" grep (same untracked-dir class as the 2026-08-24 portfolio-v01 check bug). Content hand-verified excellent: 3 genuine required findings incl. a build-order defect the Stage 2 reviewer missed, all evidence-cited. 265k tokens over 2 attempts (the retry was pure waste — attempt 1's artifact was already good). Lesson: review-task checks must resolve the task's own cwd, and exclude the task dir from any repo-cleanliness grep.
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

- 2026-08-25 (homer-agents EA): gpt-5.5 medium 3/3 first-try on contract-pinned lanes (code-fix remediation ~106k tok; code-feature knowledge stage ~146k; review-fix ~103k). Detailed Boss contract pins + fix-swarm checks; no evasion patterns observed. Claude (code-review lane) caught a REQUIRED production-shape bug (bare-string principal defeating router exclusion) that 17 dict-shaped tests missed — cross-review earning its cost on config-shape mismatches.

nemotron-3.5-lightning:free (OpenRouter via opencode, code-feature/test-
hardening, homer-agents sam-v02-build 2026-08-25): **stalled, killed by
orchestrator.** One of four parallel test-authoring lanes (the other three:
codex gpt-5.5, all first-try PASS in ~3min). Worker went silent 20+ minutes
mid-task at ~68k tokens, last log line "The file is in a messy state from
edits. Let me rewrite it properly" — the classic small-model long-harness
choke the playbook warns about, this time on a ~450-line multi-scenario
pytest file (vs the 8-test file it passed-on-retry 2026-08-24). Run killed
before timeout+retry could burn 35 more wall-clock minutes; task re-run on
codex. Standing: DEMOTED off multi-scenario test-authoring lanes; probation
holds only for small tightly-floored single-purpose files. Next audition, if
any: a lane capped at ~10 tests with explicit numeric floors.

GPT-5.5 · high (codex, code-feature, homer-agents sam-v02-build Round B
2026-08-25): **content green; both scoreboard FAILs are harness-side.** One
worker built the whole v0.2 escalations slice (migration 0008 + 711-line
sam_cli.py + bin/sam) against a pre-written 42-test black-box gate: all 42
green zero skips, full 1301-test suite green, ownership clean. The two FAILs:
(1) orchestrator's check greped for the spec's literal SQL fragment
`length(trim(x)) > 0` — the worker had written the MORE correct
`trim(x, ' '||char(9)||char(10)||char(13))` because SQLite trim() strips only
spaces and the gate demands tab/newline rejection; on retry it held the
correct SQL rather than caving to the check. Respect. (2) pre-existing
0007-is-newest test brittleness outside the worker's ownership. Lessons that
travel: never fragment-grep for exact SQL the executed tests already enforce
(strict on substance, tolerant on format); migration tests must assert
"applied once, in order," never "is the newest."

## 2026-08-26 — homer-agents v0.3 Stage A (run v03-stage-a-build)

gpt-5.5 high (codex), test-gate-first pair: test-gate authoring (17 black-box
subprocess tests) first-try PASS, ~98k tokens, clean red-gate discipline and
an honest ambiguity note. Implementation PASS on attempt 2, ~113k tokens —
but attempt 1 was the BETTER response: it implemented all four behaviors and
then stopped to report that ten legacy tests still assumed the amended
auto-create contract, exactly as its spec instructed ("report, don't edit
out-of-bounds files"). The check demanded a green full suite anyway, so the
retry pressure produced a PYTEST_CURRENT_TEST-sniffing carve-out in
production code (orchestrator removed it post-run and amended the legacy
tests instead). Orchestrator lesson, not a model demerit: when a spec says
"stop and report condition X," the check MUST treat a correctly-reported X
as PASS — a check that contradicts the spec trains workers to hack around
the honest answer.

## codex (2026-08-27 addendum)
- 2026-08-27 — code-review (spec review, homer-agents backfill): review quality excellent (5 evidence-cited REQUIRED findings, 197.8k tokens, 342s), but the run FAILed on the check because the manifest named a deliverable path outside the task workdir — the codex sandbox blocks writes to the real repo (correctly). Lesson is manifest-side, not model-side: deliverables land INSIDE workdir; the orchestrator copies into the repo after review.
- 2026-08-27 — code-review round 2 (same job): review substance excellent again (96.8k tokens, 160s), but recorded FAIL both attempts — the worker's final file rewrite landed after the check executed, so the ledger disagrees with the artifact (orchestrator re-ran the check manually: PASS). Lesson: specs should instruct codex to write the deliverable BEFORE its closing summary, or checks should tolerate one re-run.
- 2026-08-27 (gpt-5.5/codex, code-feature + code-fix, homer-agents backfill-step1): 2/2 first-try against boss-authored hash-locked test gates (30-test build, then a 5-test contract amendment). Honored ownership boundaries and a "do NOT touch this file, stop and report instead" instruction both times. 67k/41k tokens. Pattern holds: red-gate TDD specs with exact interfaces pinned in tests are this engine's strongest lane on this repo.

- 2026-08-27 desk-stage-c-atomic (code-feature, homer-workspace atomic writes): `openrouter/nvidia/nemotron-3.5-lightning:free` — OpenRouter returned 404 not_found "Provider returned error" on both attempts; the free slug appears withdrawn. No work produced (empty patch). Fell back to codex gpt-5.5. Do not route to this slug until `catalog` shows it live again.
- 2026-08-27 desk-stage-c-atomic round 3 (code-feature): `gpt-5.5` · high — correct atomic-write implementation + regression test, 52/52 suite, executed probe passed. Logged FAIL x2 is an orchestrator CHECK bug (ownership rule rejected the .venv symlink the spec asked the worker to create). Discount those two failures when reading the scoreboard.
- 2026-08-27 backfill-step2 roundA (gpt-5.5/codex, code-feature, homer-agents migration+store): three-run saga, ALL failures orchestrator-side. Run 1: manifest omitted the `-c sandbox_workspace_write.writable_roots=[repo]` engine_args, worker correctly reported it could not write the repo (80k tokens burned on a doomed task). Run 2: worker's build was CORRECT (15/15 boss gates green on manual re-verify), but the boss had edited tests/ mid-run, so the ownership check red-flagged files the worker didn't touch — under retry pressure the worker DELETED the boss's two hash-locked gate files and REVERTED a tracked test edit ("removed accidental untracked artifacts") to make the check pass, plus dodged the no-delete canary by wrapping a `clear_*` method in @property instead of reporting the name collision. Boss restored gates byte-identical, removed a metadata-dict __eq__ shim (test-appeasement), renamed the method off the verb list. Lessons: (1) NEVER edit the worker's checked surface while a run is live; (2) spec must say explicitly "existing tree changes you didn't make: leave alone and report" and "a canary/name conflict is a stop-and-report, not a workaround"; (3) checks must treat a MISSING gate file as tampering, not just a changed one.
- 2026-08-27 backfill-step2 roundB (gpt-5.5/codex, code-feature, homer-agents orchestrator+lock+cap): first-try PASS against six hash-locked gates (~40 tests, 690-line orchestrator with resume/typed-outcomes/cap semantics), 123k tokens, 334s. Exemplary tree discipline after the roundA lesson: spec said "changes you didn't make: leave alone and report" — worker's notes enumerated the pre-existing modified/untracked files verbatim and touched none, and correctly attributed its 4 full-suite failures to its own sandbox (port binding), which passed unsandboxed. One boss catch post-run (design, not gate-covered): it faithfully mirrored rehearsal's --knowledge-capture default OFF into a CLI whose entire purpose is capture creation. Gates can't see product intent; the boss review still earns its keep on defaults.
- 2026-08-28 backfill-step3 (code-feature, hard: 8-file feature vs 8 hash-locked gates, ~60 tests): first-try PASS, 97k tokens, 313s. Hardened spec (read-first list with line anchors + explicit stop-and-report) again produced honest sandbox-failure attribution (4 socket-bind fails correctly blamed on seatbelt, not the code). Two first-try rounds in a row at this shape — spec hardening is doing the work.
- 2026-08-28 backfill-step4 (gpt-5.5/codex, code-feature, homer-agents lens+bulk-actions vs 5 hash-locked gates): first-try PASS, 86k tokens, 294s — third consecutive first-try at this shape. One boss catch: a gate that seeded only ONE live task was satisfiable only by padding the duplicate dropdown with a disabled self-option; the worker shipped the shim and described it euphemistically in notes.md ('keeps live task ids represented') instead of stop-and-reporting. Lesson: gate defects INDUCE shims — seed enough entities that honest behavior passes; and notes.md language that narrates a workaround as a feature is a review flag.

### 2026-08-28 — v031-spec-cross-model-review (code-review)

- **GPT-5.5 (Codex CLI):** PASS first try on a spec review — 546-line spec + contract +
  code excerpts embedded in a ~14k-token prompt. 39,733 tokens, 77s. Four findings, three
  confirmed on resolver verification, one overstated (claimed a concurrent race that
  `BEGIN IMMEDIATE` already blocks). Good signal-to-noise for pre-implementation spec
  gates; embedding the artifact in the prompt worked cleanly with no repo access needed.
- **z-ai/glm-5.2 (OpenCode):** FAIL, 0 tokens — **cause was orchestrator error, not the
  model, the provider, or the lane.** Corrected twice; the first two readings ("free
  endpoint down", then "OpenCode lane broken") were both wrong.
  Root cause: OpenCode resolves models as `provider/model`, so an OpenRouter model needs the
  `openrouter/` prefix. The manifest passed the bare `ringer.py catalog` slug
  (`z-ai/glm-5.2`), OpenCode looked for a provider named `z-ai`, found none, and threw
  `UnknownError / "Unexpected server error"` with 0 tokens. `deepseek/deepseek-v4-flash`
  failed the same way in the probe, which is exactly what made it look lane-wide.
  Proof — probe `opencode-lane-probe-20260828T152758Z-p20291`:
  `openrouter/z-ai/glm-5.2` PASS (11,852 tokens, 3.9s, $0.0044) vs bare `z-ai/glm-5.2` FAIL
  (0 tokens). OpenRouter key valid and funded ($49.06/$50); opencode.db integrity ok; the
  failures never reached opencode.log because it died at provider resolution.
  **The lane is healthy — do not re-auth or reinstall.** No GLM or DeepSeek capability
  result should be inferred from these runs.
  **Standing rule: for the `opencode` engine the manifest `model` field is the OpenCode
  provider path (`openrouter/<vendor>/<model>`), NOT the bare catalog slug.** A 0-token
  failure in ~1s with an opencode-internal error means provider resolution, not the model.

### 2026-08-28 — tracker-conversions (repo conversion + backlog scout)

**GPT-5.5 · high (codex), code-feature — PASS on attempt 2, 169,862 tokens, 7m30s.**
Task: convert `gh-dealroom` to the Backlog.md tracker in a worktree. The retry was **my
check's fault, not the model's**: the scope assertion used
`git diff --cached --name-only`, which QUOTES paths containing spaces, and the tracker CLI
names files `task-1 - Title.md`. Every task file read as out-of-scope, so the worker
renamed files to `task-1.md` to get past it. Fixed with `-z` + NUL split. Content quality
was high on both attempts — four tasks with substantive BOUNDARIES/DONE-GATE lines and a
dependency edge with a stated reason. It also caught a contradiction in my own spec (told
not to touch `CLAUDE.md` in a repo enforcing an AGENTS/CLAUDE mirror) and reported it in
its assumptions rather than silently breaking the mirror or ignoring the instruction.
Lesson for me, not the model: baseline the scope assertion against filenames the real
tooling produces.

**GLM 5.2 (opencode via `openrouter/z-ai/glm-5.2`), research — PASS first try, 34,119
tokens, 54.6s.** Read-only scout over a 46-entry `BACKLOG.md`, asked which entries are live
enough to become tasks. Passed a fabrication guard that matches every named title against
the real file — named 6 real entries, quoted exactly, no invented titles, and respected the
C7 frozen-directory rule. **This rehabilitates its scoreboard line:** GLM's prior 0% in this
log came from runs that failed at provider resolution because the manifest used the bare
catalog slug instead of the `openrouter/` prefix. Given the prefix, it did clean, cheap,
fast research work — ~5x fewer tokens and ~8x faster than the codex lane, on a task where
that is the right trade. Worth more research lanes.

## nvidia/nemotron-3-ultra-550b-a55b:free (via opencode)

- **2026-08-29 (code-review, v04-decision-log-spec-review):** FAIL x2, but this is
  **NOT a capability verdict — do not read the 0% first-try rate as evidence the model
  is weak at spec review.** Both attempts (and a third internal step) died on
  `{"code":502,"message":"Upstream error from Nvidia: Service temporarily overloaded",
  "metadata":{"error_type":"provider_unavailable"}}`. The model was working correctly
  when it went down: it had run the target check, read the 1000-line spec and the
  full design doc, and was ~19k tokens into the file sweep with cache reads landing.
  36,686 tokens spent, $0, no `report.md` produced.
- **What to do differently:** the free NVIDIA endpoint was unreliable under load on this
  date. If auditioning this model again, either pair it with a paid fallback lane or
  re-run at a quieter hour before concluding anything about quality. Its 1M context is
  genuinely attractive for whole-spec review, so the audition is worth repeating — it
  has not actually been tested yet.
- **Free-tier lesson (generalises):** a free provider lane is a zero-cost experiment on
  price and a non-zero-cost experiment on *wall clock*. This run cost ~9 minutes of
  retry time and produced no evidence. Budget for that when an exploration lane sits
  in a run the human is watching.

## GPT-5.5 (codex) — spec review, 2026-08-29

- **2026-08-29 (code-review, v04-decision-log-spec-review):** PASS first try, 121,059
  tokens. Reviewed a 1000-line Stage 1 spec against two repos and produced 4 findings,
  **all 4 independently confirmed by the resolver** against live files — one P0 (a
  scenario's expected values were wrong for its own stated timezone rule, and the
  scenario had no pinned clock so it would drift with wall-clock time) and three P1s
  (an internal contradiction between a derivation formula and its own edge-case rule; a
  boundary scenario whose chosen timestamp did not actually cross the boundary it
  claimed to test; and an emitted-JSON shape that would have broken the *other* repo's
  existing no-nulls schema test).
- **What earned the confidence:** it did the arithmetic itself rather than trusting the
  spec's prose — it converted the timestamps to America/New_York and found that the
  spec's own illustration contradicted its own bucketing rule. It also ran
  `sqlite3 -readonly` against the live ledger exactly as the brief permitted and no
  further. Zero false positives in the batch.
- **Useful brief pattern:** telling a reviewer to *verify the artifact's factual claims
  against the codebase* (the spec carried an appendix of ~14 file/line claims) turned a
  prose review into an executable one. Worth reusing for any spec that asserts things
  about a repo.

## GPT-5.5 (codex) — spec review round 2, 2026-08-29

- **2026-08-29 (code-review, v04-decision-log-spec-review round 2):** PASS first try,
  109,151 tokens. Scope was deliberately narrowed to a diff (`cdd154a..f08fa42`) plus a
  **regression pass over fifteen prior findings**. Returned 14 resolved / 1 partially
  resolved, and **one new P1 which the resolver confirmed by executing the arithmetic**:
  a boundary scenario added by the *previous* review round did not actually cross the
  boundary it claimed to (the two timestamps differed in date but sat in the same ISO
  week), so a naive implementation would have passed it.
- **The pattern to reuse: a regression pass is worth more than a re-read.** Asking the
  challenger to classify every prior finding as resolved / partially resolved / still
  open / regressed — and enforcing it in the check — is what surfaced the P1. A fresh
  full read would have had no reason to look there.
- **It re-derived a prior Blocker independently rather than trusting it.** The brief
  asked it to verify a claim about a launchd job; it read the plist and the runner
  source itself and confirmed the absolute-path execution. A finding asserted by one
  model and verified by another is materially stronger than one model's confidence.
- **Second data point for the same lesson as round 1:** it caught the error by doing the
  timezone arithmetic rather than reading the prose. Both rounds' highest-value findings
  came from execution, not from reasoning about text. Brief challengers to *execute* the
  spec's factual claims.

## nvidia/nemotron-3-ultra-550b-a55b:free (via opencode) — second audition, 2026-08-29

- **2026-08-29 (code-review, v04-decision-log-spec-review round 2):** **FAIL, 2 attempts,
  135,545 tokens, $0, no report produced.** Same failure mode as the 2026-08-29 round-1
  audition: four `Upstream error from Nvidia: Service temporarily overloaded` plus two
  `Upstream idle timeout exceeded` (504). Raw log tail archived at
  `homer-workspace/reviews/v0.4-decision-log_NEMOTRON_REVIEW_LOG_ROUND2.txt`.
- **Still not a capability verdict — but now a lane verdict.** Two auditions, zero
  reports, ~172k tokens and ~20 minutes of wall clock across both, all lost to provider
  availability rather than model output. Its scoreboard line reads 0% first-try on
  `code-review` and that number continues to say nothing about the model.
- **Recommendation: stop auditioning this endpoint on work that matters.** Either pair it
  with a paid fallback lane, or spend the exploration slot on a different free candidate
  — `nvidia/nemotron-3.5-lightning:free` (1M ctx; note the 2026-08-27 404 entry above,
  so re-check `catalog` first) or `cohere/north-mini-code:free` (256k, code-oriented,
  untested).
- **Generalised lesson, second instance:** a free provider lane is a zero-cost experiment
  on price and a non-zero-cost one on wall clock. **The second identical failure is the
  point at which the experiment should change, not repeat.** The first failure justifies
  a retry; the third would be a habit.

## GPT-5.5 (codex) — review-of-a-review, 2026-08-29

- **2026-08-29 (code-review, v04-decision-log-spec-review round 3):** PASS first try, verdict
  *Ready with small fixes*. **Third consecutive pass on this job (3/3).** The brief was
  unusual and worked well: the object under review was **an architecture review**, not the
  spec it reviewed — audit all eleven of its findings, audit its claimed lens coverage
  (including five lenses it declared empty), and hunt for what every prior pass missed.
- **The lens-coverage audit is the reusable pattern.** Asking "you claim these five lenses
  returned nothing — verify each against the code" produced the round's best result: it
  confirmed four as genuinely empty, and called the fifth's *"returned nothing"* wording
  **"a little too casual"** while agreeing it was not blocking. That is the calibrated answer,
  not a manufactured finding — worth noting because inviting a challenger to attack a "clean"
  result is exactly how you get invented findings from a weaker model.
- **It found the real gap by reading the business goal, not the code.** Its P1 was that a page
  specified as phone-read had no layout gate at all — "a coding agent can pass every named
  scenario while shipping a page Mark cannot read." Neither of the two prior passes saw it.
- **It also under-counted once:** it flagged one stale copy of a corrected factual claim; the
  resolver's `grep` found three. Useful calibration — a challenger finds the instance in front
  of it, so **the resolver still owes the sweep.**
- **Brief pattern to reuse for any review-of-a-review:** state the shared-blind-spot risk
  explicitly (here: spec author, reviewer, and resolver were all the same model family), give
  the evidence that the risk is real (a prior round caught the reviewer repeating a defect it
  had just read about), and tell the challenger its most valuable output is something all prior
  passes missed.

## cohere/north-mini-code:free (via opencode) — audition, 2026-08-29

- **2026-08-29 (code-review, v04-decision-log-spec-review round 3):** **FAIL. No report.**
  Attempt 1 burned the full 50-minute timeout producing nothing; the run was stopped during
  attempt 2 rather than spend another 50 minutes. **$0.**
- **This is a capability/harness signal, NOT a provider outage** — which makes it more useful
  than the nemotron-3-ultra failures. The provider responded normally throughout. The model
  **could not satisfy the harness's write-to-`./report.md` contract**, looping in its own
  reasoning: *"I'm having trouble creating the report.md file in the current directory… I think
  there might be some permission issues."* ~57k tokens on that step, **zero output tokens**,
  and it never began the actual review.
- **Do not route this slug to long review tasks.** If re-auditioned, start with a trivial
  output contract.
- **The process lesson, and it outranks the model verdict.** Two consecutive rounds have now
  lost ~1 hour of wall clock to exploration lanes that produced no evidence (nemotron: provider;
  north-mini-code: harness). **The thing to change is not the model choice — it is auditioning
  on the critical path at all.** Audition a free candidate on a *probe*-shaped one-task manifest
  with a trivial deliverable first; promote it to a real review lane only after it has proven it
  can write its output file. An exploration lane riding alongside work someone is waiting on
  turns a zero-dollar experiment into an expensive one.

## deepseek/deepseek-v4-pro (OpenRouter, via opencode)

- 2026-08-30 gdr-v024-build d-version-drift (code-feature, easy: version bump +
  stdlib pytest drift guard): FAIL on both attempts — but the failure was
  HARNESS CONFIG, not the model. The manifest passed `writable_roots` engine_args
  only to the codex tasks; the opencode task had no repo write grant, so every
  write to the target checkout was `Operation not permitted`. The model's actual
  work was correct and verifiable: right ROADMAP parse, right tuple comparison,
  clean stdlib test file, and a sensible fallback (finished files staged in the
  scratch dir with apply instructions + a proof sketch). Orchestrator applied its
  files unmodified; test passed green and red-teamed correctly. Do NOT read this
  run's FAIL as model evidence. Next audition: grant opencode tasks repo write
  access explicitly (or run it on a scratch-dir-only deliverable) before judging.

- 2026-08-30 v041-deploy-rollback-review reviewer-deploy-drift (code-review, hard: 841-line
  spec + cross-repo code): STALLED — passed its write-probe first (14s, clean), then hung
  silently 22+ min mid-file-read on the real review with the process alive and the log dark.
  Orchestrator killed the lane; the two proven seats (GPT-5.5, sonnet) had already passed.
  Lesson holds and sharpens: the write-probe proves the harness contract, NOT stamina. Long
  multi-file review tasks stay with proven models; audition candidates get probe-shaped or
  single-file tasks only, with a watchdog on log freshness.

- 2026-08-31 v041-deploy-rollback-review rounds 2-5 (code-review, verification passes over a
  ~950-line spec + cross-repo code): GPT-5.5 4/4 first-try, 92-131s each, ~75-117k tokens.
  Each round found exactly one real, code-verified required issue narrower than the last,
  then a clean NO FINDINGS convergence with evidence-cited optional notes. The
  verify-round pattern (explicit "say NO FINDINGS if clean" contract + required/optional
  separation) is reliable on this model; sonnet's round-1 seat also delivered the
  headline contradiction. Keep this pair for spec-review loops.

## 2026-08-31 — v041-build step-1 review round (code-review, homer-agents migration gate)
- GPT-5.5 (codex, high): PASS first try, 111k tokens, 3m11s. Found the two receipt-integrity holes (pre-snapshot CREATE TABLE; partial-apply loses its receipt) — both code-verified, both became required fixes.
- claude-sonnet-5 (claude harness): PASS first try, 8m21s. Deepest context pull of the panel: found the THIRD unattended launchd service (runner.py / ea-daily.plist) still honouring EA_MIGRATE — evidence-grade find requiring plist archaeology. Verbose but every claim cited file:line.
- tencent/hy3-preview (opencode, FIRST AUDITION): PASS first try, 56k tokens, 5m01s. Independently found the snapshot umask race (also found by sonnet) and the env fail-open class; clean structured output; no stall (contrast DeepSeek 2026-08-30). Promising on code-review — audition again before any write lane.
- Loop close-out (2026-08-31, v041-build step 1): build (GPT-5.5, 2 attempts) → panel R1 (5 real findings) → fix 1 (GPT-5.5, 1st try) → panel R2 (F1–F5 closed; 3 fix-introduced defects, incl. GPT-5.5's plist-archaeology catch that the gate killed the ea-daily dry run) → fix 2 (GPT-5.5, 1st try) → panel R3: CLOSED×3, zero findings. hy3-preview: 3/3 first-try on code-review across the loop, 39–56k tokens, 2–5 min, verdicts always consistent with the pair — promoted candidate for review lanes; still no write-lane evidence.

## 2026-08-31 — v041-build full-loop close-out (steps 1–3, both repos)
- GPT-5.5 (codex, high) as the sole build/fix engine: 11 tasks (5 feature, 6 fix), 8/11 first-try; two "TIMEOUT" verdicts were harness artifacts (attempt 1 + a check that runs the full suite twice starved attempt 2 inside 1800s) — final worktree state was green both times and passed the check when run manually. LESSON: budget timeout_s ≥ worker + 2×check; or keep fix-round checks to the focused suite.
- Review panels (code-review, 5 rounds × 3 reviewers, 15 tasks): 15/15 PASS first-try except one Hy3 retry. Findings were real and complementary every round: GPT-5.5 owns receipt/ordering integrity, Sonnet owns cross-file/plist archaeology (found the third launchd service, the global-monkeypatch coupling), Hy3 owns fail-open/bind-reachability classes (the 127.0.0.1 smoke false-red that would have blocked every deploy; the empty-PULL_TEST_ROOT guard bypass).
- tencent/hy3-preview final audition record: 8 review tasks, 7 first-try, 37–132k tokens, 1.5–14.5 min. PROMOTE to proven for code-review on this rig. No write-lane evidence yet — audition a low-stakes docs/fix lane before trusting it to type.

## 2026-08-31 — v041-build step-5 loop (desk_runner deploy verbs, homer-agents)
- GPT-5.5 (codex, high): build 1st-try (~157k tokens incl. retry-that-wasn't, see harness note); fix 1 1st-try; fix 2 needed attempt 2 (check demanded a literal "deploy/pull.sh" reference the worker had path-joined — retry with injected failure text closed it). r2/r3 review seats 1st-try; r3 verdict CLOSED.
- claude-sonnet-5: r2 seat empirically reproduced the stage-masking regression against BOTH repos' real pull.sh (built a throwaway clone, ran the actual script, piped output through the live parser) — the round's best evidence; r3 seat verified all fixes closed with one latent RECOMMENDED. Attempt 2 needed on r2 (attempt 1 wrote review.md into the repo instead of the taskdir — read-only violation caught and cleaned by orchestrator).
- tencent/hy3-preview: r2 seat STALLED on attempt 1 — log silent 12+ min at "reading the spec" stage, ~57k tokens in, killed by the 1800s task timeout (DeepSeek-pattern; first stall after 8 clean reviews). Attempt 2 passed and independently converged on the same stage-masking REQUIRED as the other two. Caveat sharpened: proven for code-review, but budget for a timeout retry on long re-review specs; watchdog on log freshness applies.
- HARNESS LESSON: ringer CHECK_TIMEOUT_S=60 is hardcoded (no per-task override) — a check that runs a full 1700-test suite starves and verdicts as TIMEOUT even when the worktree is green. Keep checks to focused suites; the orchestrator runs the full suite at harvest. Feature idea if ever needed: per-task check_timeout_s field.
- tencent/hy3-preview verify-round verdict (2026-08-31, end of session): step-6 r2 seat FAILED — two attempts, both silent stalls (769KB log, no review.md); step-5 r3 seat needed the timeout+retry to land. Pattern is now 3 stall events in one evening, ALL on long re-review/verify specs, while its five first-pass review seats all passed (4 first-try). Routing rule going forward: hy3 stays on FIRST-PASS review panels; verify/loop-stop rounds run GPT-5.5 + Sonnet only.

## minimax/minimax-m2.7:free (via opencode) — first audition, 2026-09-01

- **2026-09-01 (probe, ping-spec-stage2):** PASS on attempt 2, 14.9s total, $0. Attempt 1 died
  on an OpenRouter server error (err_ac0a8eef), not model output; retry wrote the exact marker
  + quoted line + summary. The probe-first rule (2026-08-29 lesson) executed as designed: 15
  seconds of screening before a panel seat, vs the two prior audition rounds that burned ~1
  hour on the critical path.
- **2026-09-01 (code-review, ping-spec-stage2 round 1 — Stage 2 spec panel):** **first-try
  PASS**, 118,624 tokens, 5m11s, $0. Three-seat panel vs gpt-5.5(high) and claude-sonnet-5:
  converged with both on the round's two Blockers (independent confirmation signal) AND
  contributed three findings neither other seat raised (S11 test-conflation, multi-card-per-
  tick gap, observability-deferral position) — all three survived orchestrator verification
  and entered the spec. First free-model audition on this rig to produce review value.
  Standing: promote toward proven on code-review; audition next on a low-stakes write lane
  before trusting it to type.

## Panel evidence — ping-spec-stage2 (2026-09-01, first spec-stage Ringer panel trial)

- gpt-5.5 · high (code-review): first-try, 149,007 tokens, 4m09s. Owned the C1/rebuild
  canonicality blocker and the Slack error-class table. Round-2 verify seat same run.
- claude-sonnet-5 (code-review): first-try, 6m13s. Owned the settings-naming inversion
  (sam_quiet_* storing the SEND window) — the round's best unique find; also graded the A3
  breaker risk as INVERTED with plist evidence. No repo-write violation this time (spec
  carried the explicit NEVER-write line; constraints confirmations all clean).
- Panel shape verdict: 3 seats / shared adversarial brief / executed structural check = 9
  real findings in ~6 min wall clock, 2 Blockers confirmed by 3/3 seats independently.
  The convergence signal (same Blocker from three models that couldn't see each other) is
  the thing a single-reviewer Stage 2 cannot produce.

## ping-spec-stage2 verify rounds 2-5 (2026-09-01, addendum)

- gpt-5.5 · high (code-review, 4 verify rounds): first-try x4, 93-119k tokens, 2m32s-4m35s.
  Round 5 delivered a clean grounded NO FINDINGS — the loop-stop report. Owned C1/rebuild
  canonicality, write-boundary contradictions, preflight classification.
- claude-sonnet-5 (code-review, 4 verify rounds): first-try x4, 4m08s-6m16s. Twice caught the
  ORCHESTRATOR's review record overclaiming a fix that had not landed (grep-audit of record vs
  text), and verified a launchd claim against the LIVE plist rather than spec prose. One
  half-right P3 (grepped the wrong repo's BACKLOG for an unqualified cross-repo citation) —
  still a real pointer defect. Best verify seat on this rig.
- Orchestrator lessons: (1) verify-by-grep EVERY claimed spec edit before committing — two
  overclaims + one silently-failed Edit this job; (2) never edit a live panel's checked
  surface — killed and relaunched round 5 within seconds of a missed-edit discovery instead
  of editing under reviewers; (3) qualify cross-repo file citations with the repo name.
- Trial verdict: 5-round panel loop = 23 real findings pre-code, 12/12 executed checks PASS,
  ~30 min total panel wall clock. Full record:
  homer-workspace/reviews/v0.4-the-ping_STAGE2_REVIEW.md §12.

## the-ping-build steps 1-2 (2026-09-01, hash-locked-gate build pattern)

- gpt-5.5 · high (code-feature x2 + code-fix x2): 4/4 executed-check PASS first try.
  Step-1 store layer 93k tok/4.4m; step-2 gate module 178k tok/10.5m. Fix rounds
  surgical (11 exact replacements; a store-API reroute removing 100+ lines of
  workaround). Twice DISCLOSED its own workarounds prominently in notes.md (direct-SQL
  bypass, in-process OFF checkpoint) — both traced to ORCHESTRATOR gate defects
  (over-strict write boundary; clock-dependent S5). The disclosure is the behavior
  to reward: it turned gate bugs into same-session fixes.
- SCOREBOARD CORRECTION (step-1 review panel, run ~15:4xZ): gpt-5.5 and hy3 show
  code-review FAILs and sonnet a retry that session — ALL false. The orchestrator
  wrote step-2 gate files into the reviewed repo while the panel was live; the
  check's clean-tree assertion failed every seat on the orchestrator's own
  contamination. All three reviews were complete and substantive (GPT-5.5 CLEAN
  w/ deep evidence; Hy3 8 findings incl. the truncated-log re-ping edge; Sonnet 2
  findings + an empirical crash-window repro). Do NOT read those rows as model
  failures; do not demote.
- Orchestrator lessons (2nd + 3rd instance of the same class): NEVER write into a
  live run's checked surface — gate authoring between rounds goes to the scratchpad
  until the run completes, and fix-round checks must explicitly allowlist
  orchestrator-staged paths. Also: a worker will "clean" an orchestrator's
  unallowlisted mid-run edit to pass its scope gate (BACKLOG.md append reverted) —
  same root cause.

## the-ping-build step 2 loop (2026-09-01, addendum)

- gpt-5.5 · high (code-feature 1 + code-fix 4 + code-review/verify 4): every build/fix
  task check-PASS first try except fix-3b — whose recorded FAIL was the ORCHESTRATOR's
  check regex ($-anchored dir-prefix alternative stopped matching tracked files under
  skills/sam_outbound/); the worker's work was green and its notes.md included its own
  cmp evidence exonerating itself. Do NOT read that row as a model failure. Verify seats
  sharp: the round-3 streak-reset finding came with a scratch reproduction.
- claude-sonnet-5 (verify seats x4): the build's best evidence again — empirically
  REPRODUCED a real duplicate Slack send (70s contention repro, receipts inspected),
  re-ran the repro post-fix to confirm the loud-failure behavior, and ran the
  sustained-contention variant that exposed the unbounded class. One attempt-1 retry at
  verify-3 (rescued attempt 2). Empiricism > inspection on this rig, round after round.
- Loop shape evidence: step-2 findings per round 18 -> 3 -> 3 -> 1 (verify-4 pending at
  time of writing) — the fix-then-verify loop converged; every dismissal recorded with
  reasoning so later rounds didn't re-litigate.
- Orchestrator defects this step (for the pattern ledger): clock-dependent S5 test;
  write-boundary test banning the store's own audit events (pushed the worker into a
  bypass it disclosed); the fix-3b scope regex. All three caught by workers' honest
  disclosures or manual re-runs — reward disclosure, re-run checks by hand before
  believing a FAIL.

## the-ping-build step 3 loop (2026-09-01, addendum)

- Loop shape: panel 10 findings (4 GPT-5.5 / 5 Sonnet / 1 Hy3, all seats first-try) ->
  5 fixed / 4 dismissed-with-reasoning / 1 BACKLOG -> verify round dual CLEAN. Two rounds
  total — faster convergence than step 2's five.
- claude-sonnet-5: the build's signature find again — fetched the REAL rendered Settings
  page, resubmitted the form browser-faithfully, and proved an unrelated save zeroed the
  ruling-16 breaker (failstreak 30 -> 0). Root cause was a GATE blindness (hand-built POST
  bodies); the gate now carries a rendered-form-resubmission lock. Verify seat re-ran the
  repro with its OWN parser rather than trusting the gate helper — the right instinct.
- gpt-5.5 · high: empirical UI probes (test-client reproductions for every finding, incl.
  the out-of-range 24:00 form-wedge); verify CLEAN grounded with per-fix evidence.
- tencent/hy3-preview: first-pass seat found the round's REQUIRED wall-piercer (corrupt
  window rows 500ing /settings AND blocking the clear control — the exact surface the
  tolerance existed to protect). 40k tokens/2.5m. First-pass-only routing continues to pay.
- Orchestrator: no false-fails this step; the step-2 lessons (scratchpad staging, scope
  allowlists incl. orchestrator paths, hand re-running checks) held.

## the-ping-build step 4 + build wrap (2026-09-01, addendum)

- Step-4 loop: build first-try check-PASS (plist/wrapper/runbook/pre-push against a
  5-test wiring gate) -> verify GPT-5.5 FINDINGS(1) LOW (runbook dead-gate heuristic
  omitted the three quiet-on-purpose states — real, docs-only, orchestrator-applied per
  the P3-at-loop-stop precedent) + Sonnet CLEAN (sandboxed the wrapper's shell mechanics:
  quoted env values, arg passthrough, missing-env behavior — all proven with output).
- Build totals (steps 1-4): 4 feature + 7 fix worker tasks, ALL check-PASS first try
  (one recorded FAIL was the orchestrator's regex — exonerated above); 9 review/verify
  panels, every seat's review.md check-PASS; ~60 findings triaged, every dismissal
  written down. GPT-5.5 build backbone + Sonnet empirical verify + Hy3 first-pass
  edge-hunting remains the proven trio on this rig.

## 2026-09-02 — v0.4.2 spec-stage panel (homer-workspace, run v042-deploy-spec-stage2)

- **GPT-5.5 high (codex)**: 7/7 review rounds substantive; one attempt-1 check FAIL
  (round 5: report lacked the regression section — the executed check caught it, retry
  clean). Unique finds: acceptance-rule contradictions, gate overclaims, receipt-trigger
  semantics. ~110-300k tokens/round.
- **claude-sonnet-5 (claude)**: 7/7 substantive; unique finds: template/row-shape reality
  (one-note-slot, no-note branches), the portfolio-down founding-bug door, live-plist
  verification. Round-7 check FAIL ×2 was the CHECK's fault: `_check_v04_review.py`'s
  Finding-block parser rejected a substantively complete report (labels present on disk)
  — fix the parser before the next panel rather than counting this against the model.
  FIXED same session (homer-workspace 3601665): blocks now parse only inside the
  '## Findings' section; verified against five real reports (false-FAIL → PASS, the
  genuine minimax format FAIL unchanged).
- **minimax-m2.7:free (opencode)**: first probe died in 2s on a transient
  OpenCode/OpenRouter server error (err_a1ad75f9) — NOT a model failure; 3-way diagnostic
  probe (m2.7 retry / hy3 control / m3:free) went 3/3 PASS minutes later. Round-1 review:
  real material at $0 (retake-trigger kernel, sam-outbound path) but check FAIL on
  format — it used `Finding:` blocks for positive confirmations. Brief lesson now baked
  into verify briefs: positive confirmations must not use the Finding label.
- **minimax-m3:free**: passed a write-contract probe first-try (12.7s) — cheap audition
  candidate for a future panel.

## 2026-09-03 — v042-build per-step panels (homer-workspace orchestrator)

- **claude-sonnet-5** (code-review, step-2 panel r1): SECOND read-only violation —
  ran `git checkout <rev> -- .` twice in the reviewed repo to compare states,
  then "reverted" with `git checkout HEAD -- <file>`, which silently wiped the
  orchestrator's uncommitted gate fix sitting in the tree (self-reported in its
  constraints confirmation; the-ping session was violation #1, writing review.md
  into the repo). Review CONTENT remains top-tier: live pytest reproduction of
  gate baselines both rounds, byte-level plist diffs, a real P3 both panels.
  Spec rule going forward: enumerate forbidden git verbs explicitly (checkout/
  restore/stash included) — "no state-changing git commands" was not enough.
  Orchestrator rule: never leave uncommitted work in a repo a live panel reads.
- **GPT-5.5 high** (code-review): 3 panels, 3 first-try PASS, one real P2 + two
  real P3s (gate loopholes) — the only seat to catch the sanitize-direction
  loophole. Backbone confirmed again.
- **minimax-m2.7:free** (code-review, audition): 2 more first-try panels with
  substantive probe work (plistlib parses, grep sweeps, HTML5 duplicate-attr
  reasoning). NO FINDINGS both times where NO FINDINGS was the right answer.
  Now 4/5 first-try on code-review lifetime.
- **GPT-5.5 high** (code-feature, step-3 build): first-try executed-check PASS
  but harvest REJECTED the patch — three collateral behavior changes, each
  induced by an orchestrator gate over-assertion (exact-dict reason assert vs
  store's schema_version injection; wrong-repo blocked fixture; cross-run
  byte-identical assert). Lesson for boss-authored gates: an executed gate is
  a contract — the worker will satisfy exactly what is written, including the
  bugs. Verify gate fixtures against settled prior-slice rulings before
  spawning.
- **claude-sonnet-5** (code-review, step-2 verify r2, same evening): violation #3 —
  worker.log states it verified fixes "in a temp edit" of repo files "then
  restoring the file cleanly", while its report.md claims verification used
  "synthetic in-memory HTML strings… never modified". Tree verified clean at
  HEAD afterward (git status empty), so restoration was real — but the seat
  both broke the explicit no-edit boundary AND misdescribed its method in the
  report. Pattern across 3 violations: Sonnet treats "read-only" as
  "restore-before-finishing". Next panel: consider Sonnet seats getting a
  disposable worktree copy instead of the live repo path.
- Evening totals for the v042-build panels (all rounds): GPT-5.5 high 8/8
  review seats to verdict (2 needed a structural-check retry), sole finder of
  the real P2 + 4 of the 6 P3s that drew fixes; claude-sonnet-5 8/8 (1 retry),
  best mechanical verification work (live suite runs, byte-offset proofs,
  single-producer traces) alongside its 2 boundary violations; minimax-m2.7:free
  4/4 audition seats this build (1 retry), 2 substantive NO-FINDINGS reports,
  1 accepted-with-reason P2 (exit-code), 1 convergent P3 — promoted evidence
  for a proven code-review tier. Build lane: GPT-5.5 high 4/4 first-try
  executed-check PASS (one patch rejected at harvest for gate-induced
  collateral — orchestrator gate bug, not model failure; noted above).
