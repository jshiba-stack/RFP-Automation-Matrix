# Changelog

All notable changes to **ProSE** are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.5.0] — 2026-07-23

Row-level correctness and shared-library robustness: de-duplication hardened,
contacts de-duplicated, rows sized to their content, and the lock guard made to
actually fire.

### Added
- **Row auto-fit.** Every data row's height is computed from its Organization,
  Contact Name and Email cells against the *live* column widths — the library
  equivalent of double-clicking the row border, which Excel never does for rows
  written by a program. Deliberately not measured against Solicitation Title:
  fitting a long title makes every row tall and the sheet reads as empty space.
  Capped so one pathological cell can't take over the screen.
- **Conditional top alignment.** A wrapped cell whose text is taller than its row
  switches from centred to top-aligned so the overflow is clipped at the bottom
  only; cells that fit stay centred. Desktop Excel anchors overflow to the top
  while Excel Online/SharePoint honours centring literally and clips top *and*
  bottom, showing a band through the middle of the letters. Vertical alignment is
  the only property that controls this (`shrinkToFit` is ignored when `wrapText`
  is on), so the fix is per-cell rather than a column-wide setting.
- **Stale-lock failsafe.** `excel_lock_state()` classifies the workbook
  **free / open / stale** by testing whether any process still holds the workbook
  *or* its `~$` owner file (Windows denies sharing on both while Excel is open).
  A stale owner file — the leftover from an Excel crash, which would otherwise
  make every future scan skip forever — is deleted automatically before each
  write, in both local and shared mode, and reported in the log and banner.
  Deletion only ever touches a file no process holds, so it cannot disarm a live
  session.
- **Self-healing of existing rows** on every merge: duplicate rows collapse,
  same-person dual contacts fold to one line, and HTML entities decode. Rows for
  closed solicitations are never refreshed by a scan, so without this they would
  keep their original defects indefinitely.

### Fixed
- **Duplicate rows for one solicitation.** The HiePRO detail page returns the
  number with an amendment suffix (`"<number> version: 01"`), and the scan
  overwrote the de-dup key with it *after* de-duplication had already run — so
  every amendment appended a fresh row. The HANDS number is now the sole key and
  is never overwritten by a detail fetch. Pre-existing duplicates collapse on the
  next merge (keys normalised: markup stripped, amendment suffix removed,
  case-folded), with manual-column values folded in from *both* copies so nothing
  the user typed is lost regardless of which row carried it.
- **Markup leaking into the row key.** HANDS wraps the matched substring in
  `<span class="highlight">` in *whichever* field the query hit, including the
  solicitation number itself; only the title was being stripped, so that markup
  could become part of the key and spawn another duplicate. All text fields are
  stripped now.
- **The same person written twice.** When a notice lists one contact as both
  Specifications Contact and Buyer (common for a shared purchasing desk), both
  lines were recorded. Contacts are now compared on normalised values, so
  formatting differences between the two fields count as equal, and a single
  contact is written **once with no role tag** — the `(Specifications)`/`(Buyer)`
  tags appear only when there are genuinely two lines to tell apart.
- **HTML entities in cell text.** HANDS returns escaped text, so an apostrophe
  arrived as `&#x27;` and a slash as `&#x2F;`. Entities are decoded on the way in
  (after tag removal, so escaped angle brackets survive as text) and self-healed
  in ProSE-owned cells of older rows — never in the user's manual columns, where
  a literal `&amp;` may be intentional.
- **The shared-workbook lock guard never fired.** It relied on the save failing
  with a permission error, but a OneDrive/SharePoint file open with AutoSave
  co-authors through the sync client and takes **no exclusive OS lock**, so scans
  wrote silently into an open workbook. Detection now also checks Excel's `~$`
  owner file.
- **Row-height estimate over-counted long tokens**, charging a word that lands at
  the start of an empty line for a line break it did not need (a 35-character
  email in a 30-character column measured 3 lines instead of 2).

### Notes
- `~$` owner files are excluded from OneDrive/SharePoint sync, so the lock guard
  sees only the **local** Excel session. A remote co-author's open file is not
  detectable from the filesystem.
- **Deferred — post-scan sync verification.** A stale sign-in silently parks
  OneDrive uploads while ProSE still reports "scan complete" (observed this
  session: writes stopped reaching the library for ~2 hours until the account
  re-authenticated). A check that the workbook actually reached the library is
  the next safeguard; uploading via the Graph API instead of the sync client is
  the larger alternative.

## [0.4.0] — 2026-07-21

Shared-workbook collaboration: point ProSE at a SharePoint/OneDrive file that a
collaborator co-owns, guard the matching key, and capture both HANDS contacts.

### Added
- **Shared-workbook mode** (`shared_workbook`, dashboard → Workbook card). When
  on, a scan that finds the file open/locked (a collaborator editing it) is
  **skipped and retried next run** instead of dropping a timestamped sibling
  into the shared library. Scans re-query the source every run, so nothing is
  lost. The **workbook file path is now editable in the dashboard** (was
  config-only), so it can be pointed at a synced SharePoint/OneDrive location.
- **Solicitation # column lock** (`protect_solicitation_column`, dashboard
  toggle). Turns on Excel sheet protection with **only column B read-only** —
  every other column stays editable, and sorting/filtering/formatting still
  work. Prevents a collaborator from accidentally editing the key ProSE dedups
  on (which would cause a solicitation to re-append as "new"). Re-applied every
  run; openpyxl writes through protection so scans still refresh the column.
- **Dual-contact capture for HANDS notices.** HANDS notices carry both a
  **Specifications Contact** (the SME) and a **Buyer** (procurement officer);
  ProSE previously kept only one. It now records **both in the same cell**, one
  per line — specifications first, buyer second, each name tagged with its role
  — consistently across Name/Phone/Email. Single-contact notices yield a single
  line. Same-cell (not a new row) so dedup + expiry checkers are unaffected. The
  Phone column now wraps so both lines show.
- **Contact name casing** normalized to Title Case (`JANE DOE` / `john smith` →
  `Jane Doe` / `John Smith`); already-mixed-case names (`McCarthy`, `DeLuca`)
  are preserved, hyphens/apostrophes handled, emails left untouched.

### Notes
- All new toggles default **off**, so existing single-user setups are unchanged.

## [0.3.0] — 2026-07-14

Spreadsheet workflow upgrades: keyword provenance, expiry handling, and
respect for the user's own formatting.

### Added
- **"Keyword" column** (rightmost, column N). Each result records the
  keyword(s) it matched. Because a solicitation can surface under several
  keywords (dedup is by solicitation #), every matching keyword is accumulated
  into one comma-separated cell rather than only the first.
- **Expired-solicitation handling.** Rows whose Due Date is past the current
  local date/time are struck through and greyed, and sorted to the bottom of
  the sheet (active rows stay newest-first). Recomputed on every scan, so a row
  that lapses between runs drops and strikes automatically. Due dates parse
  `MM/DD/YYYY hh:mm AM/PM` (and a bare date = active through end of that day);
  unparseable dates are never hidden.

### Changed
- **User formatting is now preserved across scans.** The rewrite previously
  forced the program's own thin border and column widths onto every cell each
  run. It now detects and re-applies the *dominant* cell border already present
  (weight + colour), and only seeds a default column width for columns that
  have none yet — so manually applied black borders and adjusted column widths
  survive every scan and extend to newly-added rows. Falls back to the defaults
  on a fresh/blank sheet.

## [0.2.1] — 2026-07-02

Robustness fixes from the 2026-07-02 suite deep review
(`docs/audits/2026-07-02-01-suite-deep-review.md` at the repo root).

### Fixed
- **Scan results are never lost to an open workbook.** If the spreadsheet is
  open in Excel (Windows locks it), the merge now saves to a timestamped
  sibling file and says so in the dashboard banner/log, instead of failing the
  whole scan with `PermissionError`.
- **Duplicate Solicitation # rows no longer double-write.** A hand-added
  duplicate row is collapsed to the first occurrence on the next merge (its
  manual columns win), instead of being written twice.
- **Schedule registration failures are surfaced.** `schtasks /Create` errors
  now raise with the schtasks message: the Save button shows "Settings saved,
  but the schedule was NOT registered: …" instead of silently pretending, and
  a failure at dashboard startup lands in `last_error`.
- **Config/state writes are atomic** (temp file + `os.replace`), so the
  dashboard process and a Task Scheduler-spawned scan/email process can no
  longer see each other's half-written `config.json` / `.scan_state.json`.
- `__version__` had been left at 0.1.0 since the 0.2.0 release; corrected.

### Notes
- The test suite written during development was intentionally deleted after
  passing (space saving); there are currently no tests in the repo.

## [0.2.0] — 2026-06-27

Scheduling moves to Windows Task Scheduler so scans/emails run with the dashboard
closed, plus UI and lifecycle polish.

### Changed
- **Scheduling now uses Windows Task Scheduler** instead of an in-process
  scheduler. Saving settings registers/updates two tasks (`ProSE-Scan`,
  `ProSE-Email`) that call the new `run_task.bat`, so scans and emails fire even
  when the dashboard is closed and survive reboots. Task times use the PC's local
  time zone; the dashboard's next-run readouts come from Task Scheduler. The old
  APScheduler path is kept as a fallback on non-Windows platforms.

### Added
- `run_task.bat` — wrapper the scheduled tasks invoke to run a single
  `scan`/`email` job in the project's virtualenv.
- `prose/winsched.py` — registers, updates, and queries the Windows tasks.
- `python -m prose unschedule` — removes the scheduled tasks (a full kill switch
  for all background activity).

### Fixed
- Time pickers (Schedule 1/2) now use the app's teal theme instead of raw
  browser styling.
- Dashboard helper thread (browser auto-open) is now a daemon so it can never
  keep the process alive after the window is closed.

## [0.1.0] — 2026-06-27

Initial release. ProSE scans Hawaii procurement sources for active
professional-services solicitations, records them into a styled Excel
spreadsheet with full contact details, and emails it on a schedule — all driven
from a local web dashboard.

### Added

**Scanning**
- Keyword scanner built on the **HANDS** public opportunity API
  (`bidding-opportunities`) — a fast, stateless, rate-tolerant search that
  covers HiePRO *and* county/UH/agency postings in one call per keyword.
- Active-only filtering (`statuses: POSTED`) and de-duplication by Solicitation #
  across all keywords.
- 17 default keywords (editable in the dashboard).

**Contact enrichment**
- HiePRO-sourced solicitations: parsed from the static HiePRO detail page
  (`public-display-solicitation.html`, with `&resetCookie`).
- HANDS-native solicitations (county / University of Hawaii / agency): pulled
  from the public HANDS opportunity endpoint (`api/opportunity?id=`), which
  exposes buyer/contact name, phone, and email.
- Phone numbers normalized to a single `808-555-1234` format regardless of
  source, preserving extensions.

**Spreadsheet**
- Styled Excel output (`2026-2027 Scanned Professional Services.xlsx`): fixed
  13-column layout, frozen header, borders, banding, and a professional colour
  scheme applied automatically every run.
- New solicitations inserted at the **top** (newest first); existing rows
  refreshed in place. The 5 manual columns (Status, Pursue, Emailed, Status,
  Entered SF) are **never overwritten**, matched by Solicitation #.

**Scheduling**
- Schedule 1 — scan: **Daily** or **Every 12 hours** at a chosen time.
- Schedule 2 — email: any subset of weekdays at a chosen time.
- All triggers run in **Pacific/Honolulu (HST)** via APScheduler.

**Email**
- **Gmail API (OAuth2)** as the primary method — no App Password required.
  Includes a "Connect Gmail" dashboard flow and a `python -m prose auth-email` CLI.
- **SMTP + App Password** retained as a fallback.
- Sends the current spreadsheet as an attachment to a configurable recipient
  list.

**Dashboard & entry points**
- Local Flask dashboard (`http://127.0.0.1:5000`): edit keywords, both schedules
  (combined time pickers with AM/PM), and email settings; "Scan now" /
  "Send email now" actions; status panel with last/next run times.
- `start.bat` one-click Windows launcher (creates the virtualenv on first run).
- `python -m prose` entry point with `scan`, `email`, and `auth-email`
  subcommands for headless use.

### Security
- Secrets and personal data are git-ignored and never committed:
  `.env`, `credentials.json`, `token.json`, personal `config.json`, the original
  spec, and the generated spreadsheet (real contact data). A
  `config.example.json` template is provided instead.

[0.2.0]: https://semver.org/
[0.1.0]: https://semver.org/
