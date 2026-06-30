"""Local web dashboard for ProPosal (default http://127.0.0.1:5000).

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

from . import __version__, config, discovery, forms, jobs, notice

app = Flask(__name__)
app.secret_key = "proposal-local-dashboard"  # local-only; not security-sensitive

_lock = threading.Lock()
_status = {"running": False, "kind": None, "message": "", "ok": True}
_last_result: dict | None = None
_last_validation: dict | None = None


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
    _last_result = {
        "kind": kind,
        "output_name": base,
        "flags_name": f"{stem}_flags.md" if base else "",
        "checks_name": f"{stem}_checks.md" if (base and (comp or fmt)) else "",
        "applied": [(r.location, r.summary, r.old, r.new) for r in (report.applied_records if report else [])],
        "flags": [(r.kind, r.location, r.summary, r.new) for r in (report.flags if report else [])],
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
    with _lock:
        action = dict(_status)
    return render_template(
        "dashboard.html",
        version=__version__,
        state=state,
        action=action,
        result=_last_result,
        validation=_last_validation,
        sources=sources,
        active=active,
        workspace=str(workspace) if workspace else "",
        suggestions=discovery.detect_sources(),
        docx=found["docx"],
        stores=found["stores"],
        scan_error=found["error"],
        resumes_dir=cfg.get("resumes_dir", ""),
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


def _remember_resumes(resumes):
    """Persist the chosen resumes folder so it's prefilled next time."""
    if resumes:
        cfg = config.load_config()
        cfg["resumes_dir"] = resumes
        config.save_config(cfg)


@app.route("/build", methods=["POST"])
def build():
    f = request.form
    base = f.get("base") or None
    stores = [s for s in f.getlist("store") if s] or None
    fy = _int(f.get("fy"), None)
    date = f.get("date", "").strip() or None
    resumes = f.get("resumes_dir", "").strip() or None
    _remember_resumes(resumes)
    _run_in_thread("build", lambda: jobs.run_build(
        base_path=base, store_paths=stores, target_fy=fy, cover_date=date,
        resumes_dir=resumes, log=_noop))
    flash("Build started.", "info")
    return redirect(url_for("index"))


@app.route("/generate", methods=["POST"])
def generate():
    f = request.form
    template = f.get("template") or None
    stores = [s for s in f.getlist("store") if s] or None
    fy = _int(f.get("fy"), None)
    date = f.get("date", "").strip() or None
    resumes = f.get("resumes_dir", "").strip() or None
    _remember_resumes(resumes)
    _run_in_thread("generate", lambda: jobs.run_generate(
        template_path=template, store_paths=stores, target_fy=fy, cover_date=date,
        resumes_dir=resumes, log=_noop))
    flash("Generate started.", "info")
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
