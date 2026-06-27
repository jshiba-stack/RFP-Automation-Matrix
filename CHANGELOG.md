# Changelog — RFP Automation Matrix

Suite-level milestones (programs added, retired, or significantly changed).
Each program keeps its own detailed changelog in its folder.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## 2026-06-27

### Added
- **ProSE** (Professional Services Extractor) **v0.1.0** — scans Hawaii
  procurement sources (HANDS + HiePRO) for active solicitations, extracts full
  contact details into a styled Excel spreadsheet, and emails it on a schedule
  via a local dashboard. See [ProSE/CHANGELOG.md](ProSE/CHANGELOG.md).
- Established the suite structure and conventions (one folder per program; each
  with its own README, CHANGELOG, and version; secrets and generated data kept
  local and never committed).
