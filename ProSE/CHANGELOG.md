# Changelog

All notable changes to **ProSE** are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

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
