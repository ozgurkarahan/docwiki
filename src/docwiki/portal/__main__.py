"""``python -m docwiki.portal``: run the portal (or preview a built site locally).

Storage selection follows the shared settings: ``DOCWIKI_MODE=local`` reads releases from the
folder storage at ``DOCWIKI_WORK_DIR`` (``--storage-root`` overrides it); ``DOCWIKI_MODE=azure``
uses ``docwiki.storage.storage_from_settings()`` provided by the engine (Blob Storage with
managed identity). ``--site-dir`` serves an already built site without any storage.

``DOCWIKI_LIVE_ASK=1`` (with ``DOCWIKI_FOUNDRY_PROJECT_ENDPOINT``) turns on the visitors'
questions to the Researcher agent (``docs/live-ask.md``).
"""

from __future__ import annotations

import argparse
import importlib
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.settings import SETTINGS_DEFAULTS, SettingsKeys
from docwiki.contracts.storage import FolderStorage, Storage
from docwiki.logs import quiet_sdk_http_logs
from docwiki.orchestration.telemetry import configure_exporter, instrument_asgi
from docwiki.portal.app import create_app
from docwiki.portal.live_ask import LiveAsk
from docwiki.portal.sync import SiteSync


def storage_from_env(env: Mapping[str, str]) -> Storage:
    mode = env.get(SettingsKeys.MODE, SETTINGS_DEFAULTS[SettingsKeys.MODE])
    if mode == "local":
        root = env.get(SettingsKeys.WORK_DIR, SETTINGS_DEFAULTS[SettingsKeys.WORK_DIR])
        return FolderStorage(Path(root), fsync=False)
    if mode == "azure":
        try:
            factory = importlib.import_module("docwiki.storage").storage_from_settings
        except (ImportError, AttributeError) as exc:
            raise SystemExit(
                "DOCWIKI_MODE=azure needs docwiki.storage.storage_from_settings() "
                "(engine lane) and the azure extra"
            ) from exc
        return factory()
    raise SystemExit(f"unknown {SettingsKeys.MODE}: {mode!r} (expected local or azure)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m docwiki.portal",
        description="Serve the current DocWiki release's site with security headers.",
    )
    parser.add_argument("--site-dir", type=Path, help="serve this built site (no storage)")
    parser.add_argument("--storage-root", type=Path, help="folder storage root (local mode)")
    parser.add_argument("--prefix", default=StorageKeys.RELEASES, help="releases prefix")
    parser.add_argument(
        "--cache-dir", type=Path, help="local copies of the site (default: .local/portal-cache)"
    )
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)

    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    quiet_sdk_http_logs(logging.INFO)
    # With Application Insights configured (the container's case) every page and /api/ask call
    # becomes a request, and the live-ask logs and the agent calls are correlated with it.
    exporting = configure_exporter()
    live_ask = LiveAsk.from_env(os.environ)
    if live_ask is not None:
        logging.getLogger("docwiki.portal").info("live ask is on (DOCWIKI_LIVE_ASK=1)")
    if args.site_dir is not None:
        app = create_app(site_dir=args.site_dir, live_ask=live_ask)
    else:
        storage = (
            FolderStorage(args.storage_root, fsync=False)
            if args.storage_root
            else storage_from_env(os.environ)
        )
        cache_dir = args.cache_dir or Path(".local") / "portal-cache"
        app = create_app(
            SiteSync(storage, cache_dir, prefix=args.prefix),
            poll_seconds=args.poll_seconds,
            live_ask=live_ask,
        )
    if exporting:
        app = instrument_asgi(app)
    uvicorn.run(app, host=args.host, port=args.port, server_header=False, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
