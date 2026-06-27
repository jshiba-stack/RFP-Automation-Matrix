# ProSE — Professional Services Extractor

*Part of the [RFP Automation Matrix](../README.md).*

A local app that scans Hawaii's procurement sources (**HANDS** + **HiePRO**) for
**active** solicitations matching your keywords, records the relevant ones —
with full contact details — into a styled Excel spreadsheet
(`2026-2027 Scanned Professional Services`), and emails that spreadsheet on a
weekly schedule. A professional local dashboard lets you adjust keywords,
schedules, and email settings.

## Quick start

1. Make sure **Python 3.11+** is installed.
2. Double-click **`start.bat`** (Windows). On first run it creates a virtual
   environment, installs dependencies, and launches the dashboard at
   <http://127.0.0.1:5000>.

   Or manually:
   ```
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   .venv\Scripts\python -m prose
   ```
3. In the dashboard, set your **sender Gmail** and **App Password**, confirm the
   keywords/schedules, and click **Save settings**.

## How it works

| Step | What happens |
|------|--------------|
| **Scan** (Schedule 1) | For each keyword, searches the **HANDS** opportunity API for *active* solicitations (fast, covers HiePRO and related systems), then pulls full contact details for each — from the **HiePRO** detail page for HiePRO-sourced ones, or the public **HANDS** opportunity endpoint for county/UH/agency ones — and updates the spreadsheet. Runs **Daily** or **Every 12 hours** at the time you set (HST). |
| **Spreadsheet** | New solicitations are inserted at the **top** (newest first), de-duplicated by Solicitation #. The app fills only the 8 data columns; your manual columns (Status, Pursue, Emailed, Entered SF) are **never overwritten**. Styling is applied automatically — no manual formatting needed. |
| **Email** (Schedule 2) | On the weekday(s) and time you choose, emails the spreadsheet to your recipient list via Gmail. |

You can also trigger **Scan now** / **Send email now** from the dashboard.

### Automatic scheduling (Windows Task Scheduler)

When you click **Save settings**, ProSE registers two **Windows Task Scheduler**
jobs from your schedules:

- `ProSE-Scan` → `run_task.bat scan`
- `ProSE-Email` → `run_task.bat email`

This means scans and emails fire **even when the dashboard is closed**, and they
survive reboots — you do **not** need to leave anything running. The PC just
needs to be powered on (and this Windows user logged in) at the scheduled time.
Schedule times use the **PC's local time zone**. The dashboard's *Next scan /
Next email* readouts come straight from Task Scheduler.

> The tasks run for the current user and only when that user is logged on (no
> admin rights needed). To run while logged off, edit the two tasks in Task
> Scheduler and set *"Run whether user is logged on or not"* (Windows will ask
> for your password). On non-Windows machines, scheduling falls back to an
> in-process scheduler that only runs while the dashboard is open.

**Closing the dashboard leaves nothing running.** On Windows the dashboard has no
background threads — closing the window/terminal exits the process completely.
The only thing left is the two *dormant* scheduled tasks, which consume no
resources until their scheduled time, run for a few seconds, and exit. To stop
those too (a complete kill switch), run `python -m prose unschedule`.

## Email setup (Gmail OAuth — recommended)

ProSE sends via the **Gmail API using OAuth2**, so you do **not** need an App
Password. Sending happens from whichever Gmail account you connect.

1. **Create a Google OAuth client** (one-time): in the Google Cloud Console,
   enable the **Gmail API**, then create an **OAuth client ID → Desktop app**,
   download it, and save it as `instance/credentials.json` (the `instance/`
   folder is created on first run).
2. In the dashboard, set the **Sender Gmail address** (the account to send from).
3. Click **Connect Gmail** (or run `python -m prose auth-email`). A browser opens;
   **sign in as the sender account** and approve access. An
   `instance/token.json` is saved locally and reused thereafter.

The Gmail API always sends *from the account you authorize*, so the connected
account must match the Sender address.

> If your OAuth consent screen is in **Testing** mode, add the sender account as
> a **Test user** (`APIs & Services → OAuth consent screen → Test users`),
> otherwise Google blocks sign-in. `instance/credentials.json` and
> `instance/token.json` are git-ignored and never committed.

### SMTP + App Password (fallback)

If you prefer SMTP, switch **Sending method** to *SMTP + App Password* in the
dashboard, then provide a 16-char Gmail App Password
(<https://myaccount.google.com/apppasswords>, requires 2-Step Verification). It
is stored locally in `instance/.env`, never in `config.json`.

## Files

```
start.bat         One-click Windows launcher
run_task.bat      Wrapper the Windows scheduled tasks call (scan / email)
requirements.txt  Python dependencies
README.md         This file
CHANGELOG.md      Version history
prose/            Application code + entry point (run via `python -m prose`)
docs/             Templates: config.example.json, .env.example
instance/         Your private config, OAuth keys, and runtime state (git-ignored)
data/             The generated spreadsheet (git-ignored)
```

Entry point: `python -m prose` (started for you by `start.bat`). Subcommands:
`python -m prose scan`, `python -m prose email`, `python -m prose auth-email`,
`python -m prose unschedule` (removes the scheduled tasks — a full kill switch).

## Notes

- **Sites:** HANDS is the search engine (a fast, rate-tolerant JSON API that
  indexes HiePRO and related systems). Contact details are pulled from the
  HiePRO detail page for HiePRO-sourced solicitations, or the public HANDS
  opportunity endpoint for county/UH/agency ones — so every row gets contact
  info where the source provides it.
- **Keyword tip:** very short/common keywords match a lot. For example `AI` and
  `Web` match many unrelated notices; prefer specific phrases (e.g.
  `Artificial Intelligence`, `Oracle`, `Microsoft Fabric`) to keep the sheet
  focused. Edit the list anytime in the dashboard.
- **Spreadsheet columns (left→right):** Status · Solicitation # · Organization ·
  Solicitation Title · Published · Due Date · Pursue · Emailed · Status ·
  Entered SF · Contact Name · Phone · Email. The app fills Solicitation #,
  Organization, Title, Published, Due Date, Contact Name, Phone, Email.
- On Windows the dashboard does **not** need to stay open — scheduling is handled
  by Windows Task Scheduler (registered on Save). See *Automatic scheduling* above.
- `python -m prose scan` / `python -m prose email` run a single job and exit. The
  scheduled tasks use these via `run_task.bat`; you can also run them by hand.
