"""Git integration: tracked/untracked files, tracked-but-ignored files and full history."""

from __future__ import annotations

import re
import subprocess
import threading
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .model import ConfigError

_ZERO_SHA = re.compile(r"^0+$")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_COMMIT_MARK = "\x1eLGCOMMIT "
_MSG_MARK = "\x1fLGMSG"
_END_MARK = "\x1fLGEND"
_LOG_FORMAT = "%x1eLGCOMMIT %H%n%an%n%ae%n%cn%n%ce%n%x1fLGMSG%n%B%x1fLGEND"


def _git(root: Path, args: Sequence[str], stdin: bytes | None = None) -> bytes:
    command = ["git", "-C", str(root), "-c", "core.quotePath=false", *args]
    try:
        completed = subprocess.run(command, input=stdin, capture_output=True, check=False)
    except FileNotFoundError:
        raise ConfigError("git is not installed or not on PATH") from None
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise ConfigError(f"git {args[0]} failed: {detail[0] if detail else 'unknown error'}")
    return completed.stdout


def _split_nul(output: bytes) -> list[str]:
    return [item.decode("utf-8", errors="replace") for item in output.split(b"\0") if item]


def repo_toplevel(root: Path) -> Path:
    try:
        output = _git(root, ["rev-parse", "--show-toplevel"])
    except ConfigError:
        raise ConfigError(f"--root {root} is not inside a git work tree") from None
    return Path(output.decode("utf-8").strip())


def tracked_files(root: Path) -> list[str]:
    return _split_nul(_git(root, ["ls-files", "-z", "--full-name"]))


def untracked_files(root: Path) -> list[str]:
    args = ["ls-files", "-z", "--full-name", "--others", "--exclude-standard"]
    return _split_nul(_git(root, args))


def tracked_but_ignored(root: Path) -> list[str]:
    return _split_nul(
        _git(root, ["ls-files", "-z", "--full-name", "--cached", "--ignored", "--exclude-standard"])
    )


@dataclass(slots=True)
class HistoryFile:
    path: str
    lines: list[tuple[int, str]] = field(default_factory=list)
    blob: str | None = None
    binary: bool = False


@dataclass(slots=True)
class HistoryCommit:
    sha: str
    author_name: str = ""
    author_email: str = ""
    committer_name: str = ""
    committer_email: str = ""
    message: str = ""
    files: dict[str, HistoryFile] = field(default_factory=dict)


@dataclass(slots=True)
class TagRecord:
    name: str
    tagger_name: str
    tagger_email: str
    message: str


def _diff_path(line: str) -> str:
    """Path from ``diff --git a/<p> b/<p>`` (renames are disabled so both sides are equal)."""
    rest = line[len("diff --git ") :]
    if rest.startswith('"'):
        match = re.match(r'"a/((?:[^"\\]|\\.)*)"', rest)
        return match.group(1) if match else rest
    if rest.startswith("a/"):
        size = (len(rest) - 5) // 2
        if size > 0 and rest[2 + size : 5 + size] == " b/":
            return rest[2 : 2 + size]
        return rest[2:].partition(" b/")[0]
    return rest


def iter_history(root: Path, commits: Sequence[str] | None = None) -> Iterator[HistoryCommit]:
    """Commits with their added lines (``git log -p``) and changed binary blobs.

    ``commits=None`` walks every ref (``--all``); otherwise only the listed commits.
    """
    args = [
        "git", "-C", str(root), "-c", "core.quotePath=false", "log", "-p", "--raw",
        "--no-abbrev", "--no-renames", "--no-color", "--no-ext-diff", "--no-textconv",
        "--diff-merges=first-parent", f"--format={_LOG_FORMAT}",
    ]
    stdin_data: bytes | None = None
    if commits is None:
        args.append("--all")
    else:
        if not commits:
            return
        args.extend(["--no-walk=unsorted", "--stdin"])
        stdin_data = ("\n".join(commits) + "\n").encode("ascii")
    try:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        raise ConfigError("git is not installed or not on PATH") from None
    assert process.stdout is not None and process.stderr is not None
    errors: list[bytes] = []
    stderr = process.stderr
    drain = threading.Thread(target=lambda: errors.append(stderr.read()), daemon=True)
    drain.start()
    finished = False
    try:
        if stdin_data is not None and process.stdin is not None:
            process.stdin.write(stdin_data)
            process.stdin.close()
        lines = (raw.decode("utf-8", errors="replace").rstrip("\r\n") for raw in process.stdout)
        yield from parse_log(lines)
        finished = True
    finally:
        if not finished and process.poll() is None:
            process.kill()
        process.stdout.close()
        status = process.wait()
        drain.join(timeout=10)
    if status != 0:
        detail = b"".join(errors).decode("utf-8", errors="replace").strip().splitlines()
        raise ConfigError(f"git log failed: {detail[0] if detail else 'unknown error'}")


def parse_log(lines: Iterable[str]) -> Iterator[HistoryCommit]:
    """Parse ``git log -p --raw`` output produced with ``_LOG_FORMAT``."""
    commit: HistoryCommit | None = None
    state = "none"
    header: list[str] = []
    message: list[str] = []
    raw_blobs: dict[str, str] = {}
    section_path = ""
    current: HistoryFile | None = None
    new_line = 0
    remaining_old = remaining_new = 0

    for line in lines:
        if line.startswith(_COMMIT_MARK):
            if commit is not None:
                yield commit
            commit = HistoryCommit(sha=line[len(_COMMIT_MARK) :].strip())
            state, header, message, raw_blobs = "header", [], [], {}
            current, remaining_old, remaining_new = None, 0, 0
            continue
        if commit is None:
            continue
        if state == "header":
            if line == _MSG_MARK:
                fields = [*header, "", "", "", ""]
                commit.author_name, commit.author_email = fields[0], fields[1]
                commit.committer_name, commit.committer_email = fields[2], fields[3]
                state = "message"
            else:
                header.append(line)
            continue
        if state == "message":
            if line.endswith(_END_MARK):
                message.append(line[: -len(_END_MARK)])
                commit.message = "\n".join(message).strip("\n")
                state = "raw"
            else:
                message.append(line)
            continue
        if remaining_old > 0 or remaining_new > 0:
            if current is not None and line.startswith("+"):
                current.lines.append((new_line, line[1:]))
            if line.startswith("+"):
                new_line += 1
                remaining_new -= 1
            elif line.startswith("-"):
                remaining_old -= 1
            elif not line.startswith("\\"):
                new_line += 1
                remaining_new -= 1
                remaining_old -= 1
            continue
        if state == "raw" and line.startswith(":"):
            meta, _, path = line.partition("\t")
            parts = meta.split()
            if len(parts) >= 4 and not _ZERO_SHA.match(parts[3]):
                raw_blobs[path] = parts[3]
            continue
        if line.startswith("diff --git "):
            state = "diff"
            section_path = _diff_path(line)
            current = None
            continue
        if state != "diff":
            continue
        if line.startswith("Binary files ") and line.endswith(" differ"):
            blob = raw_blobs.get(section_path)
            if blob and not line.endswith("/dev/null differ"):
                commit.files[section_path] = HistoryFile(section_path, blob=blob, binary=True)
            continue
        if line.startswith("+++ "):
            target = line[4:]
            if target == "/dev/null":
                current = None
            else:
                path = target[2:] if target.startswith("b/") else target.strip('"')[2:]
                current = commit.files.setdefault(path, HistoryFile(path))
            continue
        hunk = _HUNK_RE.match(line)
        if hunk:
            remaining_old = int(hunk.group(1)) if hunk.group(1) is not None else 1
            new_line = int(hunk.group(2))
            remaining_new = int(hunk.group(3)) if hunk.group(3) is not None else 1
    if commit is not None:
        yield commit


def read_blobs(root: Path, shas: Sequence[str]) -> dict[str, bytes]:
    """Contents of blobs by SHA (``git cat-file --batch``)."""
    blobs: dict[str, bytes] = {}
    for start in range(0, len(shas), 64):
        batch = shas[start : start + 64]
        output = _git(root, ["cat-file", "--batch"], ("\n".join(batch) + "\n").encode("ascii"))
        position = 0
        while position < len(output):
            end = output.index(b"\n", position)
            header = output[position:end].decode("ascii", errors="replace").split()
            position = end + 1
            if len(header) < 3 or header[1] == "missing":
                continue
            size = int(header[2])
            blobs[header[0]] = output[position : position + size]
            position += size + 1
    return blobs


def _split_words(output: bytes) -> list[str]:
    return output.decode("ascii", errors="replace").split()


def reachable_commits(root: Path, commits: Sequence[str] | None) -> list[str]:
    """Commits reachable from ``commits`` and from ``HEAD`` (from every ref when ``None``)."""
    if commits is None:
        return _split_words(_git(root, ["rev-list", "--all"]))
    revisions = list(commits)
    try:
        _git(root, ["rev-parse", "--verify", "--quiet", "HEAD"])
        revisions.append("HEAD")
    except ConfigError:
        pass  # no commit yet: only the listed commits count
    if not revisions:
        return []
    request = ("\n".join(revisions) + "\n").encode("ascii")
    return _split_words(_git(root, ["rev-list", "--stdin"], request))


def file_versions(
    root: Path, commits: Sequence[str], paths: Sequence[str]
) -> dict[str, list[bytes]]:
    """Every distinct version of each path over ``commits``, as ``{path: [content, ...]}``.

    A commit where the path does not exist contributes nothing; identical versions are returned
    once. Versions of a path are in the order of ``commits`` (``git rev-list``: newest first).
    """
    versions: dict[str, list[bytes]] = {path: [] for path in paths}
    if not commits or not paths:
        return versions
    pairs = [(commit, path) for commit in commits for path in paths]
    request = "".join(f"{commit}:{path}\n" for commit, path in pairs).encode("utf-8")
    answers = _git(root, ["cat-file", "--batch-check"], request).decode("utf-8", errors="replace")
    lines = answers.splitlines()
    if len(lines) != len(pairs):
        raise ConfigError("git cat-file --batch-check returned an unexpected answer")
    blob_shas: dict[str, list[str]] = {path: [] for path in paths}
    for (_, path), line in zip(pairs, lines, strict=True):
        parts = line.split()
        if len(parts) == 3 and parts[1] == "blob" and parts[0] not in blob_shas[path]:
            blob_shas[path].append(parts[0])
    contents = read_blobs(root, sorted({sha for shas in blob_shas.values() for sha in shas}))
    for path, shas in blob_shas.items():
        versions[path] = [contents[sha] for sha in shas if sha in contents]
    return versions


def annotated_tags(root: Path) -> list[TagRecord]:
    output = _git(
        root,
        [
            "for-each-ref",
            "refs/tags",
            "--format=%(objecttype)%1f%(refname:short)%1f%(taggername)%1f%(taggeremail)"
            "%1f%(contents)%1e",
        ],
    )
    records: list[TagRecord] = []
    for record in output.decode("utf-8", errors="replace").split("\x1e"):
        parts = record.strip("\n").split("\x1f")
        if len(parts) == 5 and parts[0] == "tag":
            records.append(TagRecord(parts[1], parts[2], parts[3].strip("<>"), parts[4]))
    return records


def head_blob_shas(root: Path) -> set[str]:
    """Blob SHAs of the index (already covered by the working-tree scan)."""
    output = _git(root, ["ls-files", "-s", "-z"])
    shas: set[str] = set()
    for entry in output.split(b"\0"):
        parts = entry.decode("utf-8", errors="replace").split()
        if len(parts) >= 2:
            shas.add(parts[1])
    return shas
