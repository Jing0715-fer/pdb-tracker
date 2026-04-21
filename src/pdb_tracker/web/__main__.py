#!/usr/bin/env python3
"""PDB Tracker Web UI — entry point.

Usage:
    python -m pdb_tracker.web
    pdb-tracker-web          # after install

All paths can be overridden via environment variables (see config.py).
"""

from pdb_tracker import config
from pdb_tracker.web.app import (
    app,
    write_js,
    _copy_html_template,
    init_eval_db,
    init_weekly_reports_db,
    paths,
)


def main():
    config.ensure_dirs()
    _copy_html_template()
    write_js()

    p = paths()
    print(f"Database  : {p['db']}")
    print(f"Web UI    : http://localhost:{config.WEB_PORT}")
    print(f"Script dir: {p['script_dir']}")
    print(f"Reports   : {p['weekly_reports']}")
    print(f"Evals     : {p['evaluations']}")

    init_eval_db()
    init_weekly_reports_db()
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=config.WEB_DEBUG)


if __name__ == "__main__":
    main()
