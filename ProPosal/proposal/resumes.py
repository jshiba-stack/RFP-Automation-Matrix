"""Cross-verify personnel against an attached resumes folder.

Updated resumes and new hires usually live in a separate folder (often synced
from OneDrive/SharePoint). This module matches the data store's ``personnel`` to
resume files in that folder by name, so a build/generate can flag:
  * a person with no resume on file (REVIEW -- did they leave, or is it missing?)
  * a resume file matching nobody in the store (REVIEW -- new hire to add?)
It never edits anything; it only reports.

When several files match one person (folders often hold long + one-page
versions, old drafts, per-client copies), the pick is heuristic: the **newest
one-page** file, falling back to the **newest overall** when no one-pager
exists (that fallback is flagged for review). A newest PDF that a desktop PDF
editor re-saved (mangled typography) yields to a clean same-generation
sibling. Non-chosen matches are reported as ``alternates`` -- superseded
copies, not "new hire?" orphans.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from . import pdfutil
from .flags import KIND_ADD, KIND_REVIEW, Report

RESUME_EXTS = {".docx", ".pdf", ".doc"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def scan_resumes(resumes_dir) -> list[Path]:
    """Every resume file under the folder, recursively.

    Folders are commonly organized one subfolder per person, so subfolders are
    scanned too. Hidden/temp entries are skipped, as is anything starting
    with "_" (the house resume template and other non-person files).
    """
    d = Path(resumes_dir)
    if not d.is_dir():
        return []
    out = []
    for p in d.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in RESUME_EXTS:
            continue
        rel_parts = p.relative_to(d).parts
        if any(part.startswith((".", "~$", "_")) for part in rel_parts):
            continue
        out.append(p)
    return sorted(out)


def _match_strength(name: str, stem: str) -> int:
    """0 = no match, 1 = last-name only, 2 = full-name match."""
    full = _slug(name)
    fstem = _slug(stem)
    if not full or not fstem:
        return 0
    if full in fstem or fstem in full:
        return 2
    last = _slug(name.split()[-1]) if name.split() else ""
    if last and len(last) >= 3 and last in fstem:
        return 1
    return 0


def _person_matches_file(name: str, stem: str) -> bool:
    return _match_strength(name, stem) > 0


def _path_strength(name: str, path: Path, root: Path) -> int:
    """Strongest match across the file name AND its containing folder names
    (per-person folders: 'Jordan Avery/Resume 2024.docx' matches by folder)."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = (path.name,)
    stems = [Path(parts[-1]).stem, *parts[:-1]]
    return max((_match_strength(name, s) for s in stems), default=0)


def page_count(path: Path) -> int | None:
    """Best-effort page count: pypdf for .pdf, docProps/app.xml for .docx
    (written by Word on save). None when unknowable (.doc, stripped props)."""
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            return len(PdfReader(str(path)).pages)
        if ext == ".docx":
            with zipfile.ZipFile(path) as z:
                xml = z.read("docProps/app.xml").decode("utf-8", "replace")
            m = re.search(r"<Pages>(\d+)</Pages>", xml)
            return int(m.group(1)) if m else None
    except Exception:  # noqa: BLE001 - corrupt/odd file -> just unknown
        return None
    return None


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _pick_resume(candidates: list[Path]) -> tuple[Path, str]:
    """Choose one file among several matching the same person.

    The submittal is assembled at the PDF level (each resume page in the real
    deliverable is the person's own PDF export), so preference order is:
    newest one-page **.pdf**, then newest one-page .docx (convertible via
    Word), then any newest one-pager, then newest overall. When the winner is
    a PDF that a desktop PDF editor re-saved (mangled typography -- see
    :func:`pdfutil.pdf_editor_rewrite`), a clean same-generation sibling (a
    straight Word export or a .docx no more than ~a month older) replaces it;
    an OLDER clean copy never does, because content freshness beats
    typography. Returns ``(path, note)``; the note explains a non-obvious
    pick ("" if unambiguous).
    """
    if len(candidates) == 1:
        return candidates[0], ""
    one_page = [p for p in candidates if page_count(p) == 1]
    one_page_pdf = [p for p in one_page if p.suffix.lower() == ".pdf"]
    one_page_docx = [p for p in one_page if p.suffix.lower() == ".docx"]
    if one_page_pdf:
        pool, kind = one_page_pdf, "newest 1-page .pdf"
    elif one_page_docx:
        pool, kind = one_page_docx, "newest 1-page .docx"
    elif one_page:
        pool, kind = one_page, "newest 1-page"
    else:
        pool, kind = candidates, "newest"
    best = max(pool, key=_mtime)
    editor = (pdfutil.pdf_editor_rewrite(best)
              if best.suffix.lower() == ".pdf" else None)
    if editor:
        cutoff = _mtime(best) - 30 * 86400
        clean = [p for p in one_page
                 if p != best and _mtime(p) >= cutoff
                 and (p.suffix.lower() == ".docx"
                      or (p.suffix.lower() == ".pdf"
                          and not pdfutil.pdf_editor_rewrite(p)))]
        if clean:
            best = max(clean, key=lambda p: (p.suffix.lower() == ".pdf", _mtime(p)))
            kind = (f"clean 1-page {best.suffix.lower()} (the newest .pdf was "
                    f"re-saved with {editor})")
    return best, f"{kind} of {len(candidates)} matching files"


def cross_check(personnel: list[dict], resumes_dir) -> dict:
    """Return ``{matched, missing, orphans, alternates, notes}`` for the folder.

    ``alternates`` are files that match a person but lost to a better copy;
    ``notes`` (by person name) explain any heuristic pick.
    """
    root = Path(resumes_dir)
    files = scan_resumes(resumes_dir)
    matched, missing = [], []
    notes: dict[str, str] = {}
    used: set[Path] = set()
    for person in personnel:
        name = str(person.get("name", "")).strip()
        # Full-name matches beat last-name-only ones, so people sharing a
        # surname can't steal each other's folders.
        strengths = {f: _path_strength(name, f, root) for f in files if f not in used}
        candidates = ([f for f, s in strengths.items() if s == 2]
                      or [f for f, s in strengths.items() if s == 1])
        if candidates:
            best, note = _pick_resume(candidates)
            used.add(best)
            matched.append((name, best))
            if note:
                notes[name] = note
        else:
            missing.append(name)

    orphans, alternates = [], []
    names = [str(p.get("name", "")).strip() for p in personnel]
    for f in files:
        if f in used:
            continue
        owner = max(names, key=lambda n: _path_strength(n, f, root), default=None)
        if owner and _path_strength(owner, f, root) > 0:
            alternates.append((f, owner))
        else:
            orphans.append(f)
    return {"matched": matched, "missing": missing, "orphans": orphans,
            "alternates": alternates, "notes": notes}


def group_orphans(orphans: list[Path], root) -> list[tuple[str, int]]:
    """Collapse orphan files to one entry per containing top-level folder
    (loose top-level files stay individual). Returns [(label, file_count)]."""
    root = Path(root)
    groups: dict[str, int] = {}
    for f in orphans:
        try:
            parts = f.relative_to(root).parts
        except ValueError:
            parts = (f.name,)
        label = parts[0] if len(parts) > 1 else f.name
        groups[label] = groups.get(label, 0) + 1
    return list(groups.items())


def add_resume_flags(report: Report, store: dict, resumes_dir) -> dict:
    """Run the cross-check and append REVIEW/ADD flags to ``report``."""
    personnel = store.get("personnel", [])
    if not resumes_dir or not Path(resumes_dir).is_dir():
        return {"matched": [], "missing": [], "orphans": [], "alternates": [],
                "notes": {}}
    res = cross_check(personnel, resumes_dir)
    for name in res["missing"]:
        report.flag("Resumes", f"No resume file found for '{name}' in the resumes folder.",
                    KIND_REVIEW, new=name)
    # One flag per orphan person-FOLDER, not per file (folders hold many copies).
    for group, count in group_orphans(res["orphans"], resumes_dir):
        what = f"'{group}' ({count} file(s))" if count > 1 else f"'{group}'"
        report.flag("Resumes", f"Resumes {what} match no one in the data store -- new hire to add?",
                    KIND_ADD, new=group)
    # A multi-candidate pick with no one-page version is the uncertain case.
    for name, hit in res["matched"]:
        note = res["notes"].get(name, "")
        if note.startswith("newest of"):
            pc = page_count(hit)
            pages = f"{pc} pages" if pc else "page count unknown"
            report.flag("Resumes",
                        f"Several files match '{name}' and none is one page; "
                        f"picked the newest ({hit.name}, {pages}) -- verify.",
                        KIND_REVIEW, new=hit.name)
    return res
