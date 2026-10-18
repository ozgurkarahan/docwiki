"""``python -m docwiki.mcp`` runs the MCP server (same flags as ``docwiki.mcp.server``)."""

import sys

from docwiki.mcp.server import main

sys.exit(main())
