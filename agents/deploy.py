"""Deploy the DocWiki Foundry agents defined in this folder (see agents/README.md).

    uv run python agents/deploy.py --dry-run          # exact request bodies, no Azure call
    uv run python agents/deploy.py                    # new agent versions only when changed
    uv run python agents/deploy.py --routine enable   # also the daily Librarian routine

The implementation lives in ``docwiki.agents_client.deploy`` so that it is tested with the package.
"""

from __future__ import annotations

import sys
from pathlib import Path

from docwiki.agents_client.deploy import main

if __name__ == "__main__":
    sys.exit(main(agents_dir=Path(__file__).resolve().parent))
