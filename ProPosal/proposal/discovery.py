"""Discover proposal materials in a folder (typically your OneDrive folder).

OneDrive on Windows syncs to an ordinary folder on the PC (usually
``C:\\Users\\<you>\\OneDrive``). So "linking OneDrive" just means pointing ProPosal
at that folder -- no API, no login. We scan it (shallow) for previous submittals
(.docx) and data stores (.yaml/.yml/.json) and classify them, so the dashboard
can offer dropdowns instead of asking for typed paths.
"""

from __future__ import annotations

import os
from pathlib import Path

DOCX_EXT = ".docx"
STORE_EXTS = {".yaml", ".yml", ".json"}
_SKIP_DIRS = {".venv", "__pycache__", "node_modules", ".git", "output", "instance"}

# preferred order for the "version to update from" dropdown
_KIND_ORDER = {"signed": 0, "final": 1, "draft": 2, "master": 3, "other": 4, "template": 5}


def detect_onedrive() -> Path | None:
    """Best-effort path to the local OneDrive folder, if any."""
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        v = os.environ.get(var)
        if v and Path(v).is_dir():
            return Path(v)
    home = Path.home()
    for name in ("OneDrive", "OneDrive - Personal"):
        p = home / name
        if p.is_dir():
            return p
    return None


def detect_sources() -> list[dict]:
    """Suggest candidate materials folders (NOT saved or selected automatically).

    Returns ``[{"kind", "name", "path"}]`` for the personal OneDrive, the
    business/SharePoint root (``OneDrive - <Org>``), and any sibling
    ``OneDrive - *`` folders -- which is where a SharePoint library appears once
    you click **Sync** / **Add shortcut to OneDrive** on it. These are shown only
    as quick picks when the user adds a source.
    """
    seen: set[str] = set()
    out: list[dict] = []

    def _add(kind, name, path):
        rp = str(path)
        if rp and rp not in seen and Path(rp).is_dir():
            seen.add(rp)
            out.append({"kind": kind, "name": name, "path": rp})

    personal = os.environ.get("OneDriveConsumer") or os.environ.get("OneDrive")
    if personal:
        _add("onedrive", "OneDrive (personal)", personal)
    biz = os.environ.get("OneDriveCommercial")
    if biz:
        _add("sharepoint", Path(biz).name, biz)
    # Sibling 'OneDrive - <Org>' folders in the user profile (SharePoint syncs).
    try:
        for child in Path.home().iterdir():
            if child.is_dir() and child.name.startswith("OneDrive -"):
                _add("sharepoint", child.name, str(child))
    except OSError:
        pass
    return out


def classify_docx(name: str) -> str:
    n = name.lower()
    if "signed" in n:
        return "signed"
    if "final" in n:
        return "final"
    if "template" in n:
        return "template"
    if "master" in n:
        return "master"
    if "draft" in n:
        return "draft"
    return "other"


def _rec(base: Path, p: Path, kind: str | None = None) -> dict:
    try:
        mtime = p.stat().st_mtime
    except OSError:
        mtime = 0
    return {
        "path": str(p),
        "name": p.name,
        "rel": str(p.relative_to(base)) if str(p).startswith(str(base)) else p.name,
        "kind": kind,
        "mtime": mtime,
    }


def scan_folder(folder, *, max_depth: int = 3, limit: int = 800) -> dict:
    """Find .docx submittals and data-store files under ``folder``.

    Returns ``{"docx": [...], "stores": [...], "error": str|None}``. Each docx
    record carries a ``kind`` (signed/final/draft/master/template/other). The
    docx list is ordered signed->final->draft->..., newest first within a kind.
    """
    base = Path(folder)
    if not base.is_dir():
        return {"docx": [], "stores": [], "error": f"Not a folder: {folder}"}

    docx, stores = [], []
    count = 0
    for root, dirs, files in os.walk(base):
        rel_parts = Path(root).relative_to(base).parts
        if len(rel_parts) >= max_depth:
            dirs[:] = []
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith((".", "~$"))]
        for f in files:
            if f.startswith("~$"):
                continue
            ext = Path(f).suffix.lower()
            if ext != DOCX_EXT and ext not in STORE_EXTS:
                continue
            count += 1
            if count > limit:
                break
            p = Path(root) / f
            if ext == DOCX_EXT:
                docx.append(_rec(base, p, classify_docx(f)))
            else:
                stores.append(_rec(base, p))

    docx.sort(key=lambda r: (_KIND_ORDER.get(r["kind"], 9), -r["mtime"]))
    stores.sort(key=lambda r: -r["mtime"])
    return {"docx": docx, "stores": stores, "error": None}


def list_dir(path) -> dict:
    """List immediate sub-folders of ``path`` for the folder browser.

    Returns ``{"dir", "parent", "folders": [...], "error"}``. With an empty path
    on Windows, returns the drive letters as folders.
    """
    if not path:
        drives = _windows_drives()
        if drives:
            return {"dir": "", "parent": None, "folders": drives, "error": None}
        path = str(Path.home())
    p = Path(path)
    try:
        entries = sorted(
            (e for e in p.iterdir() if e.is_dir() and not e.name.startswith((".", "~$"))
             and e.name not in _SKIP_DIRS),
            key=lambda e: e.name.lower(),
        )
    except OSError as exc:
        return {"dir": str(p), "parent": str(p.parent), "folders": [], "error": str(exc)}
    folders = [{"name": e.name, "path": str(e)} for e in entries]
    parent = str(p.parent) if p.parent != p else ""
    return {"dir": str(p), "parent": parent, "folders": folders, "error": None}


def _windows_drives() -> list[dict]:
    if os.name != "nt":
        return []
    out = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        if Path(root).exists():
            out.append({"name": root, "path": root})
    return out
