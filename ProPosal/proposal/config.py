"""Configuration + runtime state for ProPosal.

Adapted from ProSE's config module: the same ROOT/INSTANCE layout, deep-merged
JSON config, and tiny state file. Private machine-local files live in the
git-ignored ``instance/`` folder; generated drafts live under ``data/output/``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTANCE = ROOT / "instance"
CONFIG_PATH = INSTANCE / "config.json"
STATE_PATH = INSTANCE / ".propose_state.json"

DEFAULT_CONFIG = {
    # Named materials sources, each a LOCAL folder (a SharePoint library synced
    # via OneDrive, your OneDrive, or any folder). Nothing is added automatically
    # -- the user adds sources explicitly, so no personal path is baked in.
    # e.g. {"name": "Honolulu RFPs", "path": "C:\\Users\\you\\OneDrive - Acme\\..."}
    "sources": [],
    "active_source": "",
    # Data store(s): read and deep-merged in order (later overrides earlier;
    # lists like `projects` concat + de-dupe by id). Keep a stable firm file and
    # a per-year opportunity file; one may live in OneDrive.
    "data_store_paths": ["data/stores/store.yaml"],
    # The previous FINAL submittal used as the base for smart copy-and-update.
    # Point this at your own previous FINAL (usually set via the dashboard).
    "base_docx_path": "assets/refs/Previous Submittal (FINAL).docx",
    # Token-based template for generate-from-data-store mode (Phase 2).
    "template_docx_path": "assets/templates/base_template.docx",
    "output_dir": "data/output",
    # Folder of per-person resume files (often synced from OneDrive/SharePoint).
    # Used to cross-verify personnel and to append resumes in generate mode.
    "resumes_dir": "",
    "default_department": "DIT",
    # Annual notice PDF, for the optional notice-validation pass (Phase 5).
    "notice_pdf_path": "assets/refs/Professional-Services-Annual-Ad-Fiscal-Year-2026.pdf",
    # Compliance caps (City & County FY26: 3.0 MB per attachment).
    "pdf_size_cap_mb": 3.0,
    "page_limit": 30,
    # Optional: auto-export docx -> pdf via Word (Windows only) just to MEASURE.
    "auto_export_pdf": False,
}

DEFAULT_STATE = {
    "last_build": None,
    "last_output": None,
    "last_flags": 0,
    "last_error": None,
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = json.loads(json.dumps(base))
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key].update(val)
        else:
            out[key] = val
    return out


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            user = json.load(fh)
        return _deep_merge(DEFAULT_CONFIG, user)
    save_config(DEFAULT_CONFIG)
    return json.loads(json.dumps(DEFAULT_CONFIG))


def _atomic_json_write(path: Path, data: dict) -> None:
    """Write JSON via temp-file + replace so a reader never sees a half file."""
    INSTANCE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def save_config(cfg: dict) -> None:
    _atomic_json_write(CONFIG_PATH, cfg)


def load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            return _deep_merge(DEFAULT_STATE, json.load(fh))
    return json.loads(json.dumps(DEFAULT_STATE))


def save_state(state: dict) -> None:
    _atomic_json_write(STATE_PATH, state)


def update_state(**fields) -> dict:
    state = load_state()
    state.update(fields)
    save_state(state)
    return state


def _abspath(value: str | Path) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def base_docx_abspath(cfg: dict) -> Path:
    return _abspath(cfg["base_docx_path"])


def template_docx_abspath(cfg: dict) -> Path:
    return _abspath(cfg["template_docx_path"])


def output_dir_abspath(cfg: dict) -> Path:
    return _abspath(cfg["output_dir"])


def notice_pdf_abspath(cfg: dict) -> Path:
    return _abspath(cfg["notice_pdf_path"])


def data_store_abspaths(cfg: dict) -> list[Path]:
    return [_abspath(p) for p in cfg.get("data_store_paths", [])]


def resumes_dir_abspath(cfg: dict) -> Path | None:
    val = (cfg.get("resumes_dir") or "").strip()
    return _abspath(val) if val else None


def active_workspace_path(cfg: dict) -> Path | None:
    """Resolve the active source's folder, or None if no source is set.

    Never auto-detects a personal folder -- returns None until the user adds and
    selects a source, so nothing private is assumed or displayed by default.
    """
    sources = cfg.get("sources", [])
    if not sources:
        return None
    name = cfg.get("active_source", "")
    chosen = next((s for s in sources if s.get("name") == name), sources[0])
    path = chosen.get("path", "")
    return _abspath(path) if path else None
