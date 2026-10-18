"""``python -m docwiki.agents_client "<question>" [--agent researcher|librarian]``.

Same behaviour as ``docwiki ask``: prints the answer with its sources and a receipt line. MCP calls
that need approval are asked on the console when stdin is a terminal and denied otherwise.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from docwiki.agents_client.client import ask, format_answer, prompt_approval
from docwiki.agents_client.errors import AgentsClientError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m docwiki.agents_client",
        description="Ask a deployed DocWiki agent (Foundry Responses API).",
    )
    parser.add_argument("question")
    parser.add_argument("--agent", default="researcher", help="researcher, librarian or a name")
    parser.add_argument("--conversation", help="continue this conversation id")
    parser.add_argument("--version", help="pin an agent version (default: latest)")
    parser.add_argument(
        "--approve",
        choices=("prompt", "deny"),
        help="approval of MCP calls (default: prompt in a terminal, deny otherwise)",
    )
    parser.add_argument("--json", action="store_true", help="print the full AgentAnswer as JSON")
    args = parser.parse_args(argv)
    interactive = args.approve == "prompt" or (args.approve is None and sys.stdin.isatty())
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None and (sys.stdout.encoding or "").lower() not in ("utf-8", "utf8"):
        reconfigure(encoding="utf-8")
    try:
        answer = asyncio.run(
            ask(
                args.question,
                agent=args.agent,
                conversation_id=args.conversation,
                approve=prompt_approval if interactive else None,
                version=args.version,
            )
        )
    except AgentsClientError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(answer.model_dump_json(indent=2) if args.json else format_answer(answer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
