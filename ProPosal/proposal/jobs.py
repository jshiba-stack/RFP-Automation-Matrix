"""High-level operations shared by the CLI and (later) the dashboard."""

from __future__ import annotations

import datetime as _dt
import re
import shutil
import tempfile
from pathlib import Path

from . import (compliance, config, datastore, formatcheck, formfill, forms,
               generator, notice, pdfutil, proofread, resume_rebuild, resumes,
               updater)
from .flags import KIND_ADD, KIND_MISSING, KIND_REVIEW


_ILLEGAL_STEM = re.compile(r'[\\/:*?"<>|]')


def _safe_stem(name) -> str | None:
    """Sanitize a user-supplied output name into a bare filename stem.

    Strips surrounding quotes/whitespace, drops a trailing ``.docx``/``.pdf``,
    and removes filesystem-illegal characters. Returns ``None`` when nothing
    usable is left, so callers can fall back to the default stem.
    """
    if not name:
        return None
    stem = str(name).strip().strip('"').strip()
    for ext in (".docx", ".pdf"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    stem = _ILLEGAL_STEM.sub("", stem).strip().rstrip(".")
    return stem or None


def _now_iso() -> str:
    return _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _assemble_submittal(store, out_docx: Path, resumes_dir, report, log,
                        cfg=None) -> str | None:
    """Assemble the deliverable PDF the way the real submittals are built:
    the exported body PDF + each person's one-page resume PDF, in Section II
    order. (Resumes never live in the .docx -- see the FY2026 references.)

    Returns the assembled PDF's path, or None when it can't be built (each
    reason is flagged).
    """
    personnel = store.get("personnel") or []
    if not personnel:
        return None

    # Body PDF: export via Word; else use a PDF the user exported themselves.
    body_pdf = pdfutil.export_pdf(out_docx, out_docx.with_suffix(".pdf"))
    if body_pdf is None:
        body_pdf = pdfutil.find_companion_pdf(out_docx)
    if body_pdf is None:
        report.flag("Submittal PDF",
                    "Couldn't export the draft to PDF (Word unavailable?). Export it "
                    "from Word next to the draft and rebuild to assemble.", KIND_MISSING)
        return None

    parts: list[Path] = [Path(body_pdf)]
    resume_pages: list[tuple[str, Path]] = []   # letterhead pass runs on these
    tmpdir: Path | None = None
    if resumes_dir and Path(resumes_dir).is_dir():
        res = resumes.cross_check(personnel, resumes_dir)
        for name, path in res["matched"]:
            ext = path.suffix.lower()
            if ext == ".pdf":
                # Typography lint: a bad source PDF (stretched text, missing
                # fonts) merges verbatim into the deliverable. When the house
                # resume template is configured, re-typeset the page instead.
                issues = pdfutil.resume_pdf_issues(path)
                use = path
                template = config.resume_template_abspath(cfg or {})
                if issues and template and template.is_file():
                    firm = store.get("firm") or {}
                    rb = resume_rebuild.rebuild(
                        path, template, out_docx.parent / "resumes_rebuilt",
                        firm_names=[firm.get("dba"), firm.get("legal_name")])
                    if rb["ok"]:
                        use = Path(rb["pdf"])
                        report.flag("Submittal PDF",
                                    f"{name}'s resume PDF was damaged "
                                    f"({'; '.join(issues)}) and was REBUILT onto "
                                    "the house template -- proofread the rebuilt "
                                    "page against the original before submitting.",
                                    KIND_REVIEW, new=use.name)
                        for n in rb["notes"]:
                            report.applied("Submittal PDF", f"{name}: {n}")
                        issues = []
                    else:
                        report.flag("Submittal PDF",
                                    f"couldn't rebuild {name}'s damaged resume "
                                    f"({rb['error']}); using the original.",
                                    KIND_REVIEW, new=path.name)
                resume_pages.append((name, Path(use)))
                label = ("resume page (rebuilt): " if use is not path
                         else "resume page: ")
                report.applied("Submittal PDF", label + name, new=use.name)
                for issue in issues:
                    report.flag("Submittal PDF",
                                f"{name}'s resume PDF {issue}; re-export it from "
                                "the Word original so the page isn't distorted.",
                                KIND_REVIEW, new=path.name)
            elif ext == ".docx":
                tmpdir = tmpdir or Path(tempfile.mkdtemp(prefix="proposal_resume_"))
                conv = pdfutil.export_pdf(path, tmpdir / f"{path.stem}.pdf")
                if conv:
                    resume_pages.append((name, Path(conv)))
                    report.applied("Submittal PDF",
                                   f"resume page (converted from .docx): {name}", new=path.name)
                else:
                    report.flag("Submittal PDF",
                                f"couldn't convert {name}'s .docx resume to PDF -- "
                                "export it manually.", KIND_ADD, new=path.name)
            else:
                report.flag("Submittal PDF",
                            f"resume for {name} is {ext} ({path.name}); provide a PDF "
                            "or .docx.", KIND_ADD, new=path.name)
    else:
        report.flag("Submittal PDF",
                    "No resumes folder attached -- assembled the body only.", KIND_ADD)

    # Letterhead standard: every resume page gets the BODY's letterhead block
    # (identical text, size, color, position) stamped over its own drifting
    # copy, so the whole deliverable carries one consistent header.
    stamp = None
    body_logo = None
    if resume_pages:
        stamp = pdfutil.build_letterhead_stamp(
            body_pdf, out_docx.parent / "resumes_rebuilt" / "_letterhead_stamp.pdf")
        if stamp is None:
            report.flag("Submittal PDF",
                        "couldn't build the letterhead stamp (no letterhead in the "
                        "body, or Word unavailable); resume letterheads left as-is.",
                        KIND_REVIEW)
        else:
            spec = pdfutil.letterhead_spec(body_pdf) or {}
            body_logo = spec.get("logo_top")
    for name, page_pdf in resume_pages:
        use = page_pdf
        if stamp is not None:
            # Vertical standard: the body's block sits a fixed distance below
            # its logo's top edge; resume logos render lower, so shift the
            # stamp by this page's logo offset to keep the same relationship.
            dy = 0.0
            if body_logo is not None:
                page_logo = pdfutil.logo_top(page_pdf)
                if page_logo is not None:
                    dy = max(-12.0, min(30.0, page_logo - body_logo))
            tmpdir = tmpdir or Path(tempfile.mkdtemp(prefix="proposal_resume_"))
            stamped, why = pdfutil.stamp_letterhead(
                page_pdf, stamp, tmpdir / f"{page_pdf.stem} (LETTERHEAD).pdf",
                dy=dy)
            if stamped:
                use = stamped
                report.applied("Submittal PDF",
                               f"letterhead standardized: {name}")
            else:
                report.flag("Submittal PDF",
                            f"couldn't standardize {name}'s letterhead ({why}); "
                            "page left as-is.", KIND_REVIEW, new=page_pdf.name)
        parts.append(use)

    try:
        merged = pdfutil.merge_pdfs(parts)
    finally:
        if tmpdir is not None:
            shutil.rmtree(tmpdir, ignore_errors=True)
    sub = out_docx.with_name(f"{out_docx.stem} (SUBMITTAL).pdf")
    sub.write_bytes(merged)
    report.applied("Submittal PDF",
                   f"assembled body + {len(parts) - 1} resume page(s) -> {sub.name}")
    log(f"Assembled submittal PDF -> {sub}")
    return str(sub)


def _run_checks(doc, store, cfg, out_docx: Path, template, log, pdf_path=None) -> dict:
    """Run the compliance checklist + format check; print and persist them."""
    pdf = Path(pdf_path) if pdf_path else None
    if pdf is None and cfg.get("auto_export_pdf"):
        pdf = pdfutil.export_pdf(out_docx)
        if pdf:
            log(f"Exported measurement PDF: {pdf}")
    checklist = compliance.run_checklist(doc, store, cfg, pdf_path=pdf)
    fmt = formatcheck.check_format(doc, template)
    log("\n" + checklist.to_console())
    log("\n" + fmt.to_console())
    md = out_docx.with_name(out_docx.stem + "_checks.md")
    md.write_text(checklist.to_markdown() + "\n" + fmt.to_markdown(), encoding="utf-8")
    log(f"Checks report -> {md}")
    return {"compliance": checklist, "format": fmt, "checks_md": str(md)}


def _output_stem(base_path: Path, target_fy) -> str:
    today = _dt.date.today().strftime("%Y-%m-%d")
    fy = f"FY{target_fy}" if target_fy else "draft"
    return f"Professional Services Submittal {fy}_DRAFT_{today}"


def run_build(
    cfg: dict | None = None,
    *,
    base_path=None,
    store_paths=None,
    target_fy: int | None = None,
    cover_date=None,
    resumes_dir=None,
    out_name=None,
    log=print,
) -> dict:
    """Smart copy-and-update: produce a new draft + a flag report."""
    cfg = cfg or config.load_config()
    base = Path(base_path) if base_path else config.base_docx_abspath(cfg)
    stores = store_paths or config.data_store_abspaths(cfg)
    store = datastore.load(stores)
    if store:
        log(f"Loaded data store(s): {', '.join(str(s) for s in stores)}")
    else:
        log("No data store found -- using anchor-only updates.")
    resumes_dir = resumes_dir or config.resumes_dir_abspath(cfg)

    doc, report = updater.build(
        base, store, target_fy=target_fy, cover_date=cover_date,
        resumes_dir=resumes_dir, log=log
    )
    proofread.proofread_document(doc, report, log=log)

    out_dir = config.output_dir_abspath(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    eff_fy = target_fy or (store.get("opportunity", {}) or {}).get("fiscal_year")
    stem = _safe_stem(out_name) or _output_stem(base, eff_fy)
    out_docx = out_dir / f"{stem}.docx"
    out_flags = out_dir / f"{stem}_flags.md"

    doc.save(str(out_docx))
    report.output = str(out_docx)
    submittal = _assemble_submittal(store, out_docx, resumes_dir, report, log,
                                    cfg=cfg)
    out_flags.write_text(report.to_markdown(), encoding="utf-8")

    config.update_state(
        last_build=_now_iso(),
        last_output=str(out_docx),
        last_flags=len(report.flags),
        last_error=None,
    )
    log(report.to_console())
    log(f"\nSaved draft -> {out_docx}")
    log(f"Flag report -> {out_flags}")
    checks = _run_checks(doc, store, cfg, out_docx, base, log, pdf_path=submittal)
    return {"output": str(out_docx), "flags": len(report.flags), "report": report,
            "submittal": submittal, **checks}


def run_generate(
    cfg: dict | None = None,
    *,
    template_path=None,
    store_paths=None,
    target_fy: int | None = None,
    cover_date=None,
    resumes_dir=None,
    out_name=None,
    log=print,
) -> dict:
    """Generate-from-data-store: assemble a fresh draft from a template + store."""
    cfg = cfg or config.load_config()
    template = Path(template_path) if template_path else config.template_docx_abspath(cfg)
    if not template.exists():
        # Fall back to the configured base FINAL as the template.
        template = config.base_docx_abspath(cfg)
        log(f"Template not found; using base as template: {template}")
    stores = store_paths or config.data_store_abspaths(cfg)
    store = datastore.load(stores)
    log(f"Loaded data store(s): {', '.join(str(s) for s in stores)}" if store
        else "No data store found -- nothing to generate from.")
    resumes_dir = resumes_dir or config.resumes_dir_abspath(cfg)

    doc, report = generator.generate(
        template, store, target_fy=target_fy, cover_date=cover_date,
        resumes_dir=resumes_dir, log=log
    )
    proofread.proofread_document(doc, report, log=log)

    out_dir = config.output_dir_abspath(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    eff_fy = target_fy or (store.get("opportunity", {}) or {}).get("fiscal_year")
    stem = _safe_stem(out_name) or _output_stem(template, eff_fy).replace("_DRAFT_", "_GENERATED_")
    out_docx = out_dir / f"{stem}.docx"
    out_flags = out_dir / f"{stem}_flags.md"

    doc.save(str(out_docx))
    report.output = str(out_docx)
    submittal = _assemble_submittal(store, out_docx, resumes_dir, report, log,
                                    cfg=cfg)
    out_flags.write_text(report.to_markdown(), encoding="utf-8")

    config.update_state(
        last_build=_now_iso(),
        last_output=str(out_docx),
        last_flags=len(report.flags),
        last_error=None,
    )
    log(report.to_console())
    log(f"\nSaved generated draft -> {out_docx}")
    log(f"Flag report -> {out_flags}")
    checks = _run_checks(doc, store, cfg, out_docx, template, log, pdf_path=submittal)
    return {"output": str(out_docx), "flags": len(report.flags), "report": report,
            "submittal": submittal, **checks}


def run_check(
    cfg: dict | None = None,
    *,
    docx_path,
    store_paths=None,
    pdf_path=None,
    template_path=None,
    log=print,
) -> dict:
    """Run the compliance checklist + format check on an existing .docx."""
    cfg = cfg or config.load_config()
    store = datastore.load(store_paths or config.data_store_abspaths(cfg))
    template = template_path or (config.base_docx_abspath(cfg) if config.base_docx_abspath(cfg).exists() else None)
    if pdf_path is None:
        pdf_path = pdfutil.find_companion_pdf(docx_path)
    checklist = compliance.run_checklist(docx_path, store, cfg, pdf_path=pdf_path)
    fmt = formatcheck.check_format(docx_path, template)
    log(checklist.to_console())
    log("\n" + fmt.to_console())
    return {"compliance": checklist, "format": fmt}


def run_validate(
    cfg: dict | None = None,
    *,
    store_paths=None,
    notice_pdf=None,
    target_fy: int | None = None,
    log=print,
) -> dict:
    """Validate the store/opportunity against the City annual notice PDF."""
    cfg = cfg or config.load_config()
    store = datastore.load(store_paths or config.data_store_abspaths(cfg))
    # find the notice PDF: explicit -> active source folder -> config default.
    pdf = notice_pdf
    if not pdf:
        ws = config.active_workspace_path(cfg)
        pdf = (notice.find_notice_pdf(ws) if ws else None) or config.notice_pdf_abspath(cfg)
    info = notice.parse_notice(pdf)
    report = notice.validate(info, store, target_fy=target_fy)
    log(f"Notice: {pdf}")
    log(report.to_console())
    return {"notice": info, "report": report, "pdf": str(pdf)}


def run_fill(
    cfg: dict | None = None,
    *,
    form_key: str,
    template_path=None,
    store_paths=None,
    prev_filled=None,
    log=print,
) -> dict:
    """Fill a fillable PDF form (DPW-120 etc.) from the data store."""
    cfg = cfg or config.load_config()
    spec = forms.FORMS.get(form_key)
    if spec is None:
        raise ValueError(f"Unknown form: {form_key}")
    template = Path(template_path) if template_path else (config.ROOT / spec.default_template)
    store = datastore.load(store_paths or config.data_store_abspaths(cfg))
    log(f"Filling {form_key} from template: {template}")

    pdf_bytes, report = formfill.fill(template, spec.field_map, store, prev_filled=prev_filled)

    out_dir = config.output_dir_abspath(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{form_key}_FILLED_{_dt.date.today():%Y-%m-%d}"
    out_pdf = out_dir / f"{stem}.pdf"
    out_flags = out_dir / f"{stem}_flags.md"

    output = None
    if pdf_bytes:
        out_pdf.write_bytes(pdf_bytes)
        report.output = str(out_pdf)
        output = str(out_pdf)
        log(f"Saved filled form -> {out_pdf}")
    else:
        log("Template is not fillable -- no PDF produced.")
    out_flags.write_text(report.to_markdown(), encoding="utf-8")
    log(report.to_console())
    return {"output": output, "flags": len(report.flags), "report": report,
            "flags_md": str(out_flags)}
