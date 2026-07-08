"""Local web dashboard for ProPosal (default http://127.0.0.1:5001; ProSE owns 5000).

Point it at your materials folder (typically your OneDrive folder); it discovers
your previous submittals and data stores and offers them as dropdowns. Pick a
version to update from (Draft from Version) or a template + store (Generate), and
review the flags + compliance + format checks inline with download links.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   send_from_directory, url_for)

from . import (__version__, config, discovery, forms, jobs, llm, notice,
               resumes, skills, storewrite)
from .flags import Report

# dashboard entry kinds -> store list keys
ENTRY_KEYS = {
    "categories": "categories",
    "personnel": "personnel",
    "pp": "past_performance",
    "capacity": "projects",
}

app = Flask(__name__)
app.secret_key = "proposal-local-dashboard"  # local-only; not security-sensitive

_lock = threading.Lock()
_status = {"running": False, "kind": None, "message": "", "ok": True}
_last_result: dict | None = None
_last_validation: dict | None = None
_last_classification: dict | None = None


def _set(running, kind, message, ok=True):
    with _lock:
        _status.update(running=running, kind=kind, message=message, ok=ok)


def _capture(kind: str, result: dict) -> None:
    global _last_result
    report = result.get("report")
    comp = result.get("compliance")
    fmt = result.get("format")
    out = result.get("output") or ""
    base = os.path.basename(out)
    stem = os.path.splitext(base)[0]
    # the flag report exists even when no output was produced (e.g. flat PDF)
    flags_md = result.get("flags_md") or (f"{stem}_flags.md" if base else "")
    flags = [(r.kind, r.location, r.summary, r.new) for r in (report.flags if report else [])]
    # group by flag kind, preserving first-appearance order (for the subtabs)
    grouped: dict[str, list] = {}
    for k, loc, summary, new in flags:
        grouped.setdefault(k, []).append((loc, summary, new))
    _last_result = {
        "kind": kind,
        "output_name": base,
        "submittal_name": os.path.basename(result.get("submittal") or ""),
        "flags_name": os.path.basename(flags_md) if flags_md else "",
        "checks_name": f"{stem}_checks.md" if (base and (comp or fmt)) else "",
        "applied": [(r.location, r.summary, r.old, r.new) for r in (report.applied_records if report else [])],
        "flags": flags,
        "flags_grouped": list(grouped.items()),
        "compliance": [(c.status, c.name, c.detail) for c in (comp.checks if comp else [])],
        "format": [(c.status, c.name, c.detail) for c in (fmt.checks if fmt else [])],
    }


def _run_in_thread(kind: str, func) -> None:
    def worker():
        _set(True, kind, f"{kind.capitalize()} in progress...")
        try:
            result = func()
            _capture(kind, result)
            n = result.get("flags", 0)
            _set(False, kind, f"{kind.capitalize()} complete -- {n} flag(s) to review.", ok=True)
        except Exception as exc:  # noqa: BLE001
            _set(False, kind, f"{kind.capitalize()} failed: {exc}", ok=False)

    threading.Thread(target=worker, daemon=True).start()


def _collect_entries(stores: list[dict]) -> dict:
    """Read every discovered store's personnel / pp / capacity records,
    annotated with the file they live in (for edit/delete/move targeting)."""
    out = {kind: [] for kind in ENTRY_KEYS}
    for s in stores:
        for kind, key in ENTRY_KEYS.items():
            for rec in storewrite.read_records(s["path"], key):
                rec = dict(rec)
                rec["_store"] = s["path"]
                rec["_store_name"] = s["name"]
                out[kind].append(rec)
    return out


def _resume_check(entries: dict, resumes_dir: str) -> dict | None:
    """Cross-reference personnel with the resumes folder for the dashboard."""
    if not resumes_dir or not Path(resumes_dir).is_dir():
        return None
    root = Path(resumes_dir)

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except ValueError:
            return p.name

    res = resumes.cross_check(entries["personnel"], resumes_dir)
    return {
        "matched": [(name, rel(p), res["notes"].get(name, ""))
                    for name, p in res["matched"]],
        "missing": res["missing"],
        "orphan_groups": resumes.group_orphans(res["orphans"], root),
        "alternates_count": len(res["alternates"]),
    }


@app.route("/")
def index():
    cfg = config.load_config()
    state = config.load_state()
    sources = cfg.get("sources", [])
    active = cfg.get("active_source", "") or (sources[0]["name"] if sources else "")
    workspace = config.active_workspace_path(cfg)
    found = (discovery.scan_folder(workspace) if workspace
             else {"docx": [], "stores": [], "error": None})
    notice_pdf = notice.find_notice_pdf(workspace) if workspace else None
    if not notice_pdf and config.notice_pdf_abspath(cfg).exists():
        notice_pdf = config.notice_pdf_abspath(cfg)
    entries = _collect_entries(found["stores"])
    resumes_dir = cfg.get("resumes_dir", "")
    with _lock:
        action = dict(_status)
    return render_template(
        "dashboard.html",
        version=__version__,
        cfg=cfg,
        state=state,
        action=action,
        result=_last_result,
        validation=_last_validation,
        classification=_last_classification,
        sources=sources,
        active=active,
        workspace=str(workspace) if workspace else "",
        suggestions=discovery.detect_sources(),
        docx=found["docx"],
        stores=found["stores"],
        scan_error=found["error"],
        resumes_dir=resumes_dir,
        entries=entries,
        resume_check=_resume_check(entries, resumes_dir),
        notice_pdf=str(notice_pdf) if notice_pdf else "",
        form_specs=[{"key": s.key, "name": s.name, "notes": s.notes}
                    for s in forms.FORMS.values()],
    )


@app.route("/add-source", methods=["POST"])
def add_source():
    cfg = config.load_config()
    path = request.form.get("path", "").strip().strip('"')
    name = request.form.get("name", "").strip() or (Path(path).name if path else "")
    if not path or not Path(path).is_dir():
        flash(f"Not a folder: {path or '(empty)'}", "error")
        return redirect(url_for("index"))
    sources = [s for s in cfg.get("sources", []) if s.get("path") != path]
    sources.append({"name": name, "path": path})
    cfg["sources"] = sources
    cfg["active_source"] = name
    config.save_config(cfg)
    flash(f"Source '{name}' added.", "success")
    return redirect(url_for("index"))


@app.route("/select-source")
def select_source():
    cfg = config.load_config()
    name = request.args.get("name", "")
    if any(s.get("name") == name for s in cfg.get("sources", [])):
        cfg["active_source"] = name
        config.save_config(cfg)
    return redirect(url_for("index"))


@app.route("/remove-source", methods=["POST"])
def remove_source():
    cfg = config.load_config()
    name = request.form.get("name", "")
    sources = [s for s in cfg.get("sources", []) if s.get("name") != name]
    cfg["sources"] = sources
    if cfg.get("active_source") == name:
        cfg["active_source"] = sources[0]["name"] if sources else ""
    config.save_config(cfg)
    flash(f"Source '{name}' removed.", "info")
    return redirect(url_for("index"))


@app.route("/api/browse")
def api_browse():
    return jsonify(discovery.list_dir(request.args.get("dir", "")))


@app.route("/build", methods=["POST"])
def build():
    """Build the draft + submittal PDF. `strict` rebuilds II/IV from the store
    (generate engine); default syncs in place (copy-update engine). The
    resumes folder comes from config (managed in the Personnel card)."""
    f = request.form
    base = f.get("base") or None
    stores = [s for s in f.getlist("store") if s] or None
    fy = _int(f.get("fy"), None)
    date = f.get("date", "").strip() or None
    name = f.get("name", "").strip() or None
    if f.get("strict"):
        _run_in_thread("build", lambda: jobs.run_generate(
            template_path=base, store_paths=stores, target_fy=fy, cover_date=date,
            out_name=name, log=_noop))
    else:
        _run_in_thread("build", lambda: jobs.run_build(
            base_path=base, store_paths=stores, target_fy=fy, cover_date=date,
            out_name=name, log=_noop))
    flash("Build started.", "info")
    return redirect(url_for("index"))


@app.route("/fill", methods=["POST"])
def fill():
    f = request.form
    form_key = f.get("form_key", "DPW-120")
    template = f.get("template", "").strip() or None
    stores = [s for s in f.getlist("store") if s] or None
    prev = f.get("prev_filled", "").strip() or None
    _run_in_thread("fill", lambda: jobs.run_fill(
        form_key=form_key, template_path=template, store_paths=stores,
        prev_filled=prev, log=_noop))
    flash(f"Filling {form_key}...", "info")
    return redirect(url_for("index"))


@app.route("/validate", methods=["POST"])
def validate():
    global _last_validation
    f = request.form
    stores = [s for s in f.getlist("store") if s] or None
    fy = _int(f.get("fy"), None)
    notice_pdf = f.get("notice_pdf", "").strip() or None
    try:
        out = jobs.run_validate(store_paths=stores, notice_pdf=notice_pdf, target_fy=fy, log=_noop)
        info, report = out["notice"], out["report"]
        _last_validation = {
            "pdf_name": os.path.basename(out["pdf"]),
            "fiscal_year": info.fiscal_year,
            "deadline": info.deadline,
            "email": info.submittal_email,
            "checks": [(c.status, c.name, c.detail) for c in report.checks],
        }
        flash(f"Validated against {os.path.basename(out['pdf'])}.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Validation failed: {exc}", "error")
    return redirect(url_for("index"))


class _FormError(ValueError):
    pass


def _entry_record(kind: str, f) -> dict:
    """Build (and validate) the store record for one dashboard entry form."""
    if kind == "categories":
        name = f.get("name", "").strip()
        if not name:
            raise _FormError("Professional Service Category (name) is required.")
        record = {"dit_number": f.get("dit_number", "").strip(), "name": name}
        desc = f.get("description", "").strip()
        if desc:
            record["description"] = desc
        return record

    if kind == "personnel":
        name = f.get("name", "").strip()
        if not name:
            raise _FormError("Resource (name) is required.")
        record = {"name": name}
        quals = f.get("qualifications", "").strip()
        if quals:
            record["qualifications"] = quals
        return record

    client = f.get("client", "").strip()
    project = f.get("project", "").strip()
    if not client or not project:
        raise _FormError("Client and Project are required.")
    record = {"client": client, "project": project}
    if kind == "pp":
        for fld in ("contact", "phone", "scope", "issue_resolution"):
            val = f.get(fld, "").strip()
            if val:
                record[fld] = val
        return record
    # capacity
    start = f.get("start_year", "").strip()
    if start:
        if not start.isdigit():
            raise _FormError("Start Date must be a year, e.g. 2015.")
        record["start_year"] = int(start)
    end = f.get("end", "").strip()
    if not end or end.lower() == "ongoing" or end.endswith("+"):
        record["end"] = "ongoing"   # '2025+' is the doc's rendering of ongoing
    elif end.isdigit():
        record["end"] = int(end)
    else:
        raise _FormError("End Date must be a year (e.g. 2024) or 'ongoing'.")
    return record


_ENTRY_LABEL = {"categories": "Section I category", "personnel": "Section II entry",
                "pp": "Section III entry", "capacity": "Section IV row"}
_ID_PREFIX = {"pp": "pp", "categories": "cat"}


@app.route("/add-entry", methods=["POST"])
def add_entry():
    """Commit a Section II / III / IV entry to a store (new, or edit-in-place)."""
    f = request.form
    kind = f.get("kind", "")
    key = ENTRY_KEYS.get(kind)
    if key is None:
        flash(f"Unknown entry kind: {kind}", "error")
        return redirect(url_for("index"))
    label = _ENTRY_LABEL[kind]

    try:
        record = _entry_record(kind, f)

        # Edit-in-place: the record names its own file, the sink select is ignored.
        edit_id = f.get("edit_id", "").strip()
        edit_store = f.get("edit_store", "").strip()
        if edit_id and edit_store:
            storewrite.update_record(edit_store, key, edit_id, record)
            flash(f"{label} '{edit_id}' updated in "
                  f"{os.path.basename(edit_store)}.", "success")
            return redirect(url_for("index"))

        store_path = f.get("store", "").strip()
        if store_path == "__new__":
            ws = config.active_workspace_path(config.load_config())
            if not ws:
                raise _FormError("Add a materials source first so the new store has a home.")
            store_path = str(Path(ws) / "store_additions.yaml")
        if not store_path:
            raise _FormError("Pick a data store to save into.")
        rid = storewrite.append_record(
            store_path, key, record, id_prefix=_ID_PREFIX.get(kind, ""))
        flash(f"{label} committed to {os.path.basename(store_path)} (id: {rid}).",
              "success")
    except _FormError as exc:
        flash(str(exc), "error")
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, file untouched
        flash(f"Could not save entry: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/entry/delete", methods=["POST"])
def entry_delete():
    f = request.form
    key = ENTRY_KEYS.get(f.get("kind", ""))
    try:
        if key is None:
            raise ValueError(f"unknown kind: {f.get('kind')}")
        storewrite.delete_record(f.get("store", ""), key, f.get("id", ""))
        flash(f"Deleted '{f.get('id')}' from {os.path.basename(f.get('store', ''))}.", "info")
    except Exception as exc:  # noqa: BLE001
        flash(f"Could not delete entry: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/entry/move", methods=["POST"])
def entry_move():
    f = request.form
    key = ENTRY_KEYS.get(f.get("kind", ""))
    try:
        if key is None:
            raise ValueError(f"unknown kind: {f.get('kind')}")
        offset = -1 if f.get("dir") == "up" else 1
        storewrite.move_record(f.get("store", ""), key, f.get("id", ""), offset)
    except Exception as exc:  # noqa: BLE001
        flash(f"Could not move entry: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/import-doc", methods=["POST"])
def import_doc():
    """Pull Sections II / III / IV out of a previous submittal into the editors.

    Writes (OVERWRITES) `store_imported.yaml` in the active source, which the
    entry lists and builds then pick up like any other store.
    """
    import datetime as _dt

    import yaml

    global _last_classification

    docx_path = request.form.get("docx", "").strip()
    if not docx_path or not Path(docx_path).exists():
        flash(f"Pick a document to import from (not found: {docx_path or '(empty)'}).", "error")
        return redirect(url_for("index"))
    ws = config.active_workspace_path(config.load_config())
    if not ws:
        flash("Add a materials source first — the imported store lives there.", "error")
        return redirect(url_for("index"))
    try:
        from .tools.extract_store import extract
        data = extract(docx_path)
        subset = {k: [dict(r) for r in data.get(k, [])]
                  for k in ("categories", "personnel", "past_performance", "projects")}
        target = Path(ws) / "store_imported.yaml"
        header = (
            f"# Imported by ProPosal from '{Path(docx_path).name}' on "
            f"{_dt.date.today()}.\n"
            "# Re-importing OVERWRITES this file (including dashboard edits to it).\n"
            "# Edit through the dashboard's step-2 cards.\n"
        )
        body = yaml.safe_dump(subset, sort_keys=False, allow_unicode=True, width=100)
        storewrite._atomic_write(target, header + body)
        _last_classification = None   # fresh import = clean slate; drop stale results
        flash(f"Imported {len(subset['categories'])} Section I categor(y/ies), "
              f"{len(subset['personnel'])} personnel, "
              f"{len(subset['past_performance'])} past-performance block(s), and "
              f"{len(subset['projects'])} project row(s) into {target.name}.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Import failed: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/settings", methods=["POST"])
def settings():
    """Save machine-local defaults from the Settings modal to instance/config.json."""
    cfg = config.load_config()
    f = request.form
    for key in ("base_docx_path", "template_docx_path", "notice_pdf_path",
                "output_dir", "resumes_dir", "resume_template_docx_path",
                "default_department"):
        if key in f:
            cfg[key] = f.get(key, "").strip().strip('"')
    cap = f.get("pdf_size_cap_mb", "").strip()
    if cap:
        try:
            cfg["pdf_size_cap_mb"] = float(cap)
        except ValueError:
            flash(f"PDF size cap must be a number: {cap}", "error")
    pl = f.get("page_limit", "").strip()
    if pl:
        try:
            cfg["page_limit"] = int(pl)
        except ValueError:
            flash(f"Page limit must be a whole number: {pl}", "error")
    cfg["auto_export_pdf"] = bool(f.get("auto_export_pdf"))
    # LLM (Section I classifier) settings — the block may not exist on older configs.
    llm = dict(cfg.get("llm") or {})
    if "llm.enabled" in f or "llm_present" in f:
        llm["enabled"] = bool(f.get("llm.enabled"))
    for lk in ("backend", "model", "host"):
        if f"llm.{lk}" in f:
            llm[lk] = f.get(f"llm.{lk}", "").strip()
    nc = f.get("llm.num_ctx", "").strip()
    if nc:
        try:
            llm["num_ctx"] = int(nc)
        except ValueError:
            flash(f"LLM context length must be a whole number: {nc}", "error")
    if llm:
        cfg["llm"] = llm
    # Data store paths: one per line (blank = keep existing).
    dsp = f.get("data_store_paths", "")
    paths = [ln.strip() for ln in dsp.replace(",", "\n").splitlines() if ln.strip()]
    if paths:
        cfg["data_store_paths"] = paths
    config.save_config(cfg)
    flash("Settings saved.", "success")
    return redirect(url_for("index"))


@app.route("/classify", methods=["POST"])
def classify():
    """Classify Section I skills against the current DIT taxonomy.

    Auto-applies (and persists) exact-match letter corrections; everything
    uncertain or duplicated is flagged for the human. Uses the local LLM when
    enabled, else deterministic keyword matching.
    """
    global _last_classification
    cfg = config.load_config()
    workspace = config.active_workspace_path(cfg)
    found = (discovery.scan_folder(workspace) if workspace
             else {"docx": [], "stores": [], "error": None})
    cats = _collect_entries(found["stores"])["categories"]
    if not cats:
        flash("No Section I categories to classify — import a submittal or add some first.", "error")
        return redirect(url_for("index"))

    backend = None
    try:
        backend = llm.get_backend(cfg)
        if backend is not None and not backend.available():
            flash("LLM enabled but the Ollama daemon isn't reachable — using keyword matching.", "info")
            backend = None
    except Exception as exc:  # noqa: BLE001
        flash(f"LLM backend error ({exc}); using keyword matching.", "info")
        backend = None

    report = Report()
    try:
        out = skills.classify_categories(cats, backend=backend, report=report, log=_noop)
    except Exception as exc:  # noqa: BLE001
        flash(f"Classification failed: {exc}", "error")
        return redirect(url_for("index"))

    persisted = 0
    for r in out["results"]:
        if not r["applied"]:
            continue
        cat = next((c for c in cats if c.get("id") == r["id"]), None)
        if cat and cat.get("_store"):
            try:
                storewrite.update_record(cat["_store"], "categories", cat["id"],
                                         {"dit_number": cat["dit_number"]})
                persisted += 1
            except Exception as exc:  # noqa: BLE001
                flash(f"Could not save '{cat.get('name', cat['id'])}': {exc}", "error")

    _last_classification = {
        "results": out["results"],
        "duplicates": out["duplicates"],
        "used_llm": out["used_llm"],
        "applied": out["applied"],
        "flag_count": len(report.flags),
    }
    engine = "local LLM" if out["used_llm"] else "keyword matching"
    flash(f"Classified {len(cats)} skill(s) via {engine}: {persisted} DIT # corrected, "
          f"{len(out['duplicates'])} possible duplicate group(s), "
          f"{len(report.flags)} flag(s) to review.", "success")
    return redirect(url_for("index"))


@app.route("/classify/accept", methods=["POST"])
def classify_accept():
    """Apply one flagged classification suggestion: set a category's DIT # letter."""
    f = request.form
    cid = f.get("id", "").strip()
    letter = f.get("letter", "").strip()
    cfg = config.load_config()
    workspace = config.active_workspace_path(cfg)
    found = (discovery.scan_folder(workspace) if workspace
             else {"docx": [], "stores": [], "error": None})
    cats = _collect_entries(found["stores"])["categories"]
    cat = next((c for c in cats if str(c.get("id")) == cid), None)
    if not cat or not cat.get("_store"):
        flash("Could not find that category to update (re-run Classify?).", "error")
        return redirect(url_for("index"))
    try:
        storewrite.update_record(cat["_store"], "categories", cid, {"dit_number": letter})
        # mark applied but KEEP the original "current" so the row still reads
        # old -> new (the arrow) instead of new -> new after the reload
        if _last_classification:
            for r in _last_classification["results"]:
                if str(r["id"]) == cid:
                    r["applied"] = True
        flash(f"Set DIT # for '{cat.get('name', cid)}' to '{letter}'.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Could not update category: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/classify/accept-all", methods=["POST"])
def classify_accept_all():
    """Apply every pending (not-yet-applied) classification suggestion at once."""
    if not _last_classification:
        flash("Nothing to accept — run Classify first.", "error")
        return redirect(url_for("index"))
    cfg = config.load_config()
    workspace = config.active_workspace_path(cfg)
    found = (discovery.scan_folder(workspace) if workspace
             else {"docx": [], "stores": [], "error": None})
    by_id = {str(c.get("id")): c for c in _collect_entries(found["stores"])["categories"]}
    applied = 0
    for r in _last_classification["results"]:
        if r["applied"] or not (r["suggested"] and r["suggested"] != r["current"]):
            continue
        cat = by_id.get(str(r["id"]))
        if not cat or not cat.get("_store"):
            continue
        try:
            storewrite.update_record(cat["_store"], "categories", str(r["id"]),
                                     {"dit_number": r["suggested"]})
            r["applied"] = True   # keep original "current" for the old -> new arrow
            applied += 1
        except Exception as exc:  # noqa: BLE001
            flash(f"Could not update '{cat.get('name', r['id'])}': {exc}", "error")
    flash(f"Accepted {applied} suggested change(s)." if applied
          else "No pending suggestions to accept.", "success" if applied else "info")
    return redirect(url_for("index"))


@app.route("/download/<path:name>")
def download(name):
    cfg = config.load_config()
    return send_from_directory(config.output_dir_abspath(cfg), name, as_attachment=True)


@app.route("/status.json")
def status_json():
    with _lock:
        return dict(_status)


def _noop(*_a, **_k):
    pass


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
