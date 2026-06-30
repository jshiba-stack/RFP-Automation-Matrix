"""ProPosal CLI.

Usage:
    python -m proposal build [--base <docx>] [--store <yaml> ...]
                             [--fy <year>] [--date <YYYY-MM-DD|"Month D, YYYY">]
    python -m proposal generate [--template <docx>] [--store <yaml> ...] [--fy <year>]
    python -m proposal check <docx> [--store <yaml>] [--pdf <pdf>]
    python -m proposal validate [--store <yaml>] [--notice <pdf>] [--fy <year>]
    python -m proposal dashboard
    python -m proposal inspect <docx> [--runs]
"""

from __future__ import annotations

import argparse
import sys

from . import config, forms, jobs


def _cmd_build(args) -> int:
    cfg = config.load_config()
    jobs.run_build(
        cfg,
        base_path=args.base,
        store_paths=args.store or None,
        target_fy=args.fy,
        cover_date=args.date,
    )
    return 0


def _cmd_generate(args) -> int:
    cfg = config.load_config()
    jobs.run_generate(
        cfg,
        template_path=args.template,
        store_paths=args.store or None,
        target_fy=args.fy,
        cover_date=args.date,
    )
    return 0


def _cmd_check(args) -> int:
    cfg = config.load_config()
    jobs.run_check(
        cfg,
        docx_path=args.docx,
        store_paths=args.store or None,
        pdf_path=args.pdf,
        template_path=args.template,
    )
    return 0


def _cmd_form(args) -> int:
    cfg = config.load_config()
    jobs.run_fill(
        cfg,
        form_key=args.type,
        template_path=args.template,
        store_paths=args.store or None,
        prev_filled=args.prev,
    )
    return 0


def _cmd_validate(args) -> int:
    cfg = config.load_config()
    jobs.run_validate(
        cfg,
        store_paths=args.store or None,
        notice_pdf=args.notice,
        target_fy=args.fy,
    )
    return 0


def _cmd_dashboard(args) -> int:
    from .app import app

    host, port = args.host, args.port
    url = f"http://{('127.0.0.1' if host in ('0.0.0.0', '127.0.0.1') else host)}:{port}"
    print(f"ProPosal dashboard running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        import threading
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=False)
    return 0


def _cmd_inspect(args) -> int:
    from .tools import inspect_docx

    sys.argv = ["inspect_docx", args.docx] + (["--runs"] if args.runs else [])
    return inspect_docx.main()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="proposal", description=__doc__)
    sub = parser.add_subparsers(dest="cmd")

    b = sub.add_parser("build", help="smart copy-and-update from a previous FINAL")
    b.add_argument("--base", help="path to the previous FINAL .docx")
    b.add_argument("--store", action="append", help="data store path (repeatable)")
    b.add_argument("--fy", type=int, help="target fiscal year (default: detected + 1)")
    b.add_argument("--date", help="cover date (default: today)")
    b.set_defaults(func=_cmd_build)

    g = sub.add_parser("generate", help="assemble a fresh draft from a template + data store")
    g.add_argument("--template", help="path to the template .docx (default: config/base FINAL)")
    g.add_argument("--store", action="append", help="data store path (repeatable)")
    g.add_argument("--fy", type=int, help="target fiscal year")
    g.add_argument("--date", help="cover date (default: today)")
    g.set_defaults(func=_cmd_generate)

    c = sub.add_parser("check", help="run the compliance checklist + format check on a .docx")
    c.add_argument("docx")
    c.add_argument("--store", action="append", help="data store path (repeatable)")
    c.add_argument("--pdf", help="exported PDF to measure (default: companion .pdf)")
    c.add_argument("--template", help="template .docx to compare styles against")
    c.set_defaults(func=_cmd_check)

    fm = sub.add_parser("form", help="fill a PDF form (DPW-120 etc.) from the data store")
    fm.add_argument("--type", required=True, choices=list(forms.FORMS))
    fm.add_argument("--template", help="override the default blank template PDF")
    fm.add_argument("--store", action="append", help="data store path (repeatable)")
    fm.add_argument("--prev", help="a previously-filled copy to carry values forward from")
    fm.set_defaults(func=_cmd_form)

    v = sub.add_parser("validate", help="validate the store against the City annual notice PDF")
    v.add_argument("--store", action="append", help="data store path (repeatable)")
    v.add_argument("--notice", help="path to the annual notice/ad PDF")
    v.add_argument("--fy", type=int, help="target fiscal year to check against the notice")
    v.set_defaults(func=_cmd_validate)

    d = sub.add_parser("dashboard", help="launch the local web dashboard (default)")
    d.add_argument("--host", default="127.0.0.1")
    d.add_argument("--port", type=int, default=5000)
    d.add_argument("--no-browser", action="store_true", help="don't auto-open a browser")
    d.set_defaults(func=_cmd_dashboard)

    ins = sub.add_parser("inspect", help="dump a .docx structure (Phase-0 probe)")
    ins.add_argument("docx")
    ins.add_argument("--runs", action="store_true")
    ins.set_defaults(func=_cmd_inspect)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        # No subcommand -> launch the dashboard (double-click friendly).
        return _cmd_dashboard(argparse.Namespace(host="127.0.0.1", port=5000, no_browser=False))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
