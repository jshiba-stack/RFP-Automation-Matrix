"""Cross-verify personnel against an attached resumes folder.

Updated resumes and new hires usually live in a separate folder (often synced
from OneDrive/SharePoint). This module matches the data store's ``personnel`` to
resume files in that folder by name, so a build/generate can flag:
  * a person with no resume on file (REVIEW -- did they leave, or is it missing?)
  * a resume file matching nobody in the store (REVIEW -- new hire to add?)
It never edits anything; it only reports.
"""

from __future__ import annotations

import re
from pathlib import Path

from .flags import KIND_ADD, KIND_REVIEW, Report

RESUME_EXTS = {".docx", ".pdf", ".doc"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def scan_resumes(resumes_dir) -> list[Path]:
    d = Path(resumes_dir)
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in RESUME_EXTS)


def _person_matches_file(name: str, stem: str) -> bool:
    full = _slug(name)
    fstem = _slug(stem)
    if not full or not fstem:
        return False
    if full in fstem or fstem in full:
        return True
    last = _slug(name.split()[-1]) if name.split() else ""
    return bool(last) and len(last) >= 3 and last in fstem


def cross_check(personnel: list[dict], resumes_dir) -> dict:
    """Return ``{matched, missing, orphans}`` lists for the given folder."""
    files = scan_resumes(resumes_dir)
    matched, missing = [], []
    used: set[Path] = set()
    for person in personnel:
        name = str(person.get("name", "")).strip()
        hit = next((f for f in files if f not in used and _person_matches_file(name, f.stem)), None)
        if hit:
            used.add(hit)
            matched.append((name, hit))
        else:
            missing.append(name)
    orphans = [f for f in files if f not in used]
    return {"matched": matched, "missing": missing, "orphans": orphans}


def add_resume_flags(report: Report, store: dict, resumes_dir) -> dict:
    """Run the cross-check and append REVIEW/ADD flags to ``report``."""
    personnel = store.get("personnel", [])
    if not resumes_dir or not Path(resumes_dir).is_dir():
        return {"matched": [], "missing": [], "orphans": []}
    res = cross_check(personnel, resumes_dir)
    for name in res["missing"]:
        report.flag("Resumes", f"No resume file found for '{name}' in the resumes folder.",
                    KIND_REVIEW, new=name)
    for f in res["orphans"]:
        report.flag("Resumes", f"Resume '{f.name}' matches no one in the data store -- new hire to add?",
                    KIND_ADD, new=f.name)
    return res
