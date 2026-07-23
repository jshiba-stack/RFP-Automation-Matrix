# Engineering Case Studies: ProSE (Professional Services Extractor)

Curated, sanitized narratives of the hardest problems solved in **ProSE**, the
scheduled scanner that extracts public procurement opportunities into a shared
spreadsheet. Written STAR-style (Situation, Task, Action, Result) in the
author-owned voice described in the [highlights README](../README.md). Metrics
are marked `(measured)` or `(est.)`. No real client, firm, or personnel data
appears here.

For the document-assembly program, see [ProPosal case studies](../proposal/case-studies.md).

---

## 1. Automation that runs safely alongside a human collaborator

**Situation.** A scanning tool refreshes a shared Excel workbook of procurement
opportunities on a schedule. The same workbook is edited by hand: a collaborator
fills in status and action columns, applies their own cell borders, and adjusts
column widths. Naive automation would either overwrite that human work or corrupt
the file when both parties touched it at once.

**Task.** Let the automated refresh and a human collaborator share one workbook as
a single source of truth, without the machine ever destroying the human's work or
producing duplicate rows.

**Action.** I designed the refresh to be strictly non-destructive: it fills only
the data columns, never touches the human's action columns, and deduplicates by a
stable solicitation key so a re-seen opportunity updates in place instead of
appending a copy. To survive concurrent editing on a synced drive, I added a
shared-workbook mode that skips and retries a scan when the file is locked open,
rather than dropping a sibling copy into the shared folder. I preserved the
collaborator's own cell borders and column widths across every scan and extended
them to new rows, and added an opt-in lock on just the dedup-key column through
sheet protection, so the key that prevents duplicates cannot be edited by
accident.

**Result.** The tool and a human now edit one document safely. Human formatting
and action columns survive every refresh, duplicates collapse, and a locked file
no longer produces a lost scan or a litter of copies.

- Human action columns and formatting preserved across every scan `(measured)`
- Duplicate rows collapsed by stable key; lock-aware scan skips and retries `(measured)`
- Replaces about 2 hours of manual portal-checking and data entry per scan, run unattended `(est.)`
- Runs with zero LLM inference (deterministic extraction), avoiding roughly 70,000 tokens of model processing per scan (about 480,000 per week) `(est.; basis in resume-bullets.md)`

**Demonstrates:** building automation around a human workflow, concurrency and
data-integrity thinking, treating the user's work as a first-class constraint.

**Evidence:** [ProSE README](../../../ProSE/README.md), [ProSE CHANGELOG](../../../ProSE/CHANGELOG.md).

---

## 2. A de-duplication key that quietly changed under the de-duplicator

**Situation.** Solicitations began appearing twice in the shared workbook, as
exact-looking duplicate rows. The de-duplication logic was correct and provably
ran, and querying the upstream source confirmed only one record existed. The
second row also stranded any status the collaborator had typed on the first.

**Task.** Find why a correct de-duplicator produced duplicates, stop it
permanently, and remove the duplicates already sitting in a live shared file
without discarding anything a human had typed into either copy.

**Action.** Rather than special-casing the symptom, I traced the row's life
through the pipeline and found an ordering defect. Records are de-duplicated on
the identifier returned by the search API, then each unique record is enriched
from a per-record detail page. That detail page returns the same solicitation
with an amendment suffix appended to its number, and the enrichment step
overwrote every field, including the identifier the de-duplication had just been
performed on. So the key mutated *after* the grouping that depended on it, and
every amendment issued upstream minted a brand-new row. Fetching the live detail
page confirmed the suffix directly rather than by inference. While reading that
response I found a second, latent source of the same class of bug: the search API
wraps whatever field matched the query in highlight markup, including the
identifier itself, so a query matching inside a solicitation number would also
have produced a corrupted key. I made the search-side identifier immutable for
the rest of the pipeline, stripped markup from every field rather than just the
display title, and normalized keys on read (markup removed, amendment suffix
stripped, case-folded). For the rows already in the live file, I made the merge
self-healing: duplicates collapse on the next run, and because I could not know
which copy the human had typed into, non-empty manual values are folded in from
*both* copies rather than keeping the first.

**Result.** Duplicates stopped being created and the existing ones collapsed on
the next scheduled scan, with no manual cleanup and no lost human input. The same
self-healing approach was then reused for two later defects (a contact recorded
twice, and undecoded HTML entities) in rows that no scan would ever refresh again.

- Live workbook collapsed 55 rows to 53 with zero duplicate keys remaining `(measured)`
- Manual values verified preserved from both copies of a duplicated row, tested by typing a different value into each `(measured)`
- Previously the amendment suffix appended one new row per amendment, indefinitely `(measured)`

**Demonstrates:** root-cause tracing across pipeline stages, spotting a latent
second instance of the same bug class, designing an irreversible data fix to be
conservative, verification against a real workbook rather than a synthetic one.

**Evidence:** [ProSE CHANGELOG v0.5.0](../../../ProSE/CHANGELOG.md),
`ProSE/prose/scanner.py`, `ProSE/prose/spreadsheet.py`.

---

## 3. A concurrency guard that never fired, and a failsafe that had to not misfire

**Situation.** The scanner had a guard meant to prevent it from writing to the
shared workbook while a collaborator had it open. In practice a scan wrote
straight into an open file and reported success. The guard inferred "someone has
this open" from the write failing with a permission error, which is sound for a
local file.

**Task.** Detect a genuinely open workbook on a cloud-synced shared folder, and
add a failsafe for the case where the detection signal itself gets left behind,
without the failsafe ever disabling the guard it protects.

**Action.** I tested the assumption instead of trusting it, and found the premise
was wrong for the deployment that mattered: a cloud-synced file opened with
autosave co-authors through the sync client and takes no exclusive OS lock, so
the write succeeds and silently races the other copy. I rebuilt detection around
the lock file the spreadsheet application drops beside an open workbook, and
classified state as free, open, or stale by probing whether any process still
holds the workbook or that lock file, checking both so a live session is caught
even if a future application version shares one of them more permissively. The
user then raised the obvious operational risk: a crash leaves the lock file
behind and every future scan skips forever. Their proposed fix was to delete
stale lock files before each scan. I pushed back on the naive form, because
deleting unconditionally disarms the guard in exactly the situation it exists
for, and instead gated deletion on a liveness probe: the file is removed only
when no process holds it, which is precisely the state a crash leaves and is
unreachable while a session is alive. I verified both directions, driving a real
spreadsheet session through automation for the live case rather than simulating
it.

**Result.** An open workbook is now detected and the scan skips and retries; a
crash leftover is cleared automatically and reported rather than wedging the
schedule. Nothing is silent in either direction.

- Crash leftover: state classified stale, cleared, scan wrote all 53 rows `(measured)`
- Live session: state classified open, scan skipped, lock file left untouched `(measured)`
- Documented blind spot: these lock files are excluded from cloud sync, so a remote collaborator's open file is not detectable from the filesystem `(measured)`

**Demonstrates:** testing an assumption instead of inheriting it, distinguishing
a signal's absence from its meaning, refusing a plausible fix that would defeat
its own purpose, stating a known limitation rather than implying full coverage.

**Evidence:** [ProSE CHANGELOG v0.5.0](../../../ProSE/CHANGELOG.md),
`ProSE/prose/spreadsheet.py`.
