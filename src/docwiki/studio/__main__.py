"""``python -m docwiki.studio``: run DocWiki Studio.

In the container (``ca-studio``) it listens on 0.0.0.0:8080 behind Container Apps built-in
authentication and uses its managed identity. On a workstation, ``docwiki studio --local`` binds
127.0.0.1, skips the sign-in checks and uses your ``az login``: set ``DOCWIKI_MODE=azure`` and the
storage and Foundry variables of a deployed environment (``azd env get-values``).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence

from docwiki.logs import quiet_sdk_http_logs
from docwiki.orchestration.settings import SettingsError
from docwiki.studio.config import StudioConfigError

LOOPBACK = ("127.0.0.1", "localhost", "::1")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m docwiki.studio",
        description="DocWiki Studio: add documents, follow the pipeline, ask the agents.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument(
        "--local",
        action="store_true",
        help="no sign-in checks (for a workstation; binds the loopback interface only)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check storage and agent access with this identity, print JSON and exit (0 = ok)",
    )
    args = parser.parse_args(argv)
    if args.check:
        from docwiki.studio.wiring import check

        try:
            result = check()
        except (StudioConfigError, SettingsError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result))
        return 0 if result["ok"] else 1
    if args.local and args.host not in LOOPBACK:
        parser.error("--local only serves the loopback interface (--host 127.0.0.1)")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    quiet_sdk_http_logs(logging.INFO)
    from docwiki.orchestration.telemetry import configure_exporter, instrument_asgi
    from docwiki.studio.wiring import build_app

    # Uploads, questions and approval decisions are logged: with Application Insights configured
    # (the container's case) they become an audit trail next to the pipeline's spans.
    exporting = configure_exporter()
    try:
        app = build_app(local=args.local)
    except (StudioConfigError, SettingsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if exporting:
        app = instrument_asgi(app)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, server_header=False, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
