"""Scan orchestration: file sets, extraction, rules, de-duplication and suppression."""

from __future__ import annotations

import os
import re
from bisect import bisect_right
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from . import gitsource
from .closedworld import Vocabulary, find_candidates
from .config import (
    DEFAULT_ALLOWED_DOMAINS,
    DEFAULT_ALLOWED_GUIDS,
    DEFAULT_ALLOWLIST,
    DEFAULT_COMMON_WORDS,
    DEFAULT_IGNORE,
    DEFAULT_SITE_VENDOR,
    DEFAULT_TECH_ALLOWLIST,
    load_allowed_domains,
    load_allowed_guids,
    load_denylist,
    load_ignore,
    load_site_vendor,
    load_termset,
    merge_termsets,
    parse_termset,
)
from .extract import (
    CELL_EXTS,
    MARKDOWN_EXTS,
    PYTHON_EXTS,
    extract_bytes,
    line_chunks,
    suffix_of,
    unescape_text,
    with_unescaped,
)
from .model import Chunk, ConfigError, Extraction, Finding, Notice, Severity, finding_id
from .rules import (
    Hit,
    deny_hits,
    identifier_hits,
    is_lock_or_registry_file,
    metadata_issues,
    policy_violation,
)

MAX_FILE_BYTES = 256 * 1024 * 1024
HISTORY_PATH = "git-history"
# Repository paths of the word lists (the fiction allowlist is added from the scanner settings):
# every version of them found in the scanned history also counts when history is judged.
_COMMON_WORDS_REPO_PATH = "tools/leakguard/common_words.txt"
_TECH_ALLOWLIST_REPO_PATH = "tools/leakguard/tech_allowlist.txt"
# File types whose added lines in history are checked by the closed-world rule.
_HISTORY_PROSE_EXTS = MARKDOWN_EXTS | CELL_EXTS | {
    ".txt", ".json", ".jsonl", ".yaml", ".yml", ".eml", ".vtt", ".srt", ""
}
_PY_LITERAL_RE = re.compile(r"#(.*)$|\"([^\"]*)\"|'([^']*)'")
# Tool-generated commit trailers whose value is a random session/change identifier, not a
# private resource ID. The whole trailer line is skipped by the history scan.
_TOOL_TRAILER_RE = re.compile(
    r"^\s*(?:Copilot-Session|Change-Id)\s*:\s*[0-9A-Fa-f][0-9A-Fa-f-]{7,63}\s*$",
    re.IGNORECASE,
)
_PROSE_HINT_RE = re.compile(
    r"\b(?:the|and|of|to|is|are|with|for|in|on|le|la|les|des|et|est|pour|der|die|das|und|ist"
    r"|mit|für)\b",
    re.IGNORECASE,
)
_UNSUPPRESSIBLE = ("deny:", "denylist-missing")


@dataclass(slots=True)
class ScanOptions:
    root: Path = Path(".")
    history: bool = False
    commits: list[str] | None = None
    include_untracked: bool = False
    sites: list[Path] = field(default_factory=list)
    denylist: Path | None = None
    allowlist: Path | None = None
    ignore_file: Path | None = None
    site_vendor: Path | None = None
    strict: bool = False
    redact: bool = False


@dataclass(slots=True)
class ScanReport:
    findings: list[Finding]
    notices: list[Notice]
    suppressed: list[Finding]
    stats: dict[str, int]
    strict: bool
    redact: bool

    @property
    def errors(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "warning")

    @property
    def exit_code(self) -> int:
        if self.errors or (self.strict and self.warnings):
            return 1
        return 0


class Scanner:
    def __init__(self, options: ScanOptions) -> None:
        self.options = options
        self.scan_root = options.root.resolve()
        self.root = gitsource.repo_toplevel(self.scan_root).resolve()
        self.deny_path = self._resolve_denylist()
        self.deny = load_denylist(self.deny_path) if self.deny_path else []
        self.allowed_guids = load_allowed_guids(DEFAULT_ALLOWED_GUIDS)
        self.domains = load_allowed_domains(DEFAULT_ALLOWED_DOMAINS)
        tech = load_termset(DEFAULT_TECH_ALLOWLIST, "technology allowlist", required=True)
        common = load_termset(DEFAULT_COMMON_WORDS, "common-word list", required=True)
        if options.allowlist is not None:
            allowlist_path = options.allowlist
            if not allowlist_path.is_absolute():
                allowlist_path = Path.cwd() / allowlist_path
            allow = load_termset(allowlist_path, "fiction allowlist", required=True)
        else:
            allowlist_path = self.root / DEFAULT_ALLOWLIST
            allow = load_termset(allowlist_path, "fiction allowlist", required=False)
        self.allowlist_rel = self._relative(allowlist_path)
        self.allow_present = allow.present
        self.vocabulary = Vocabulary(allow, tech, common)
        if options.ignore_file is not None and not options.ignore_file.is_file():
            raise ConfigError(f"ignore file not found: {options.ignore_file}")
        self.ignore = load_ignore(options.ignore_file or DEFAULT_IGNORE)
        self.site_vendor = load_site_vendor(
            options.site_vendor or DEFAULT_SITE_VENDOR, required=options.site_vendor is not None
        )

        self.findings: list[Finding] = []
        self.notices: list[Notice] = []
        self.stats: Counter[str] = Counter()
        self._seen: set[tuple[str, str, str, str, str, str]] = set()
        self._closed_world: list[tuple[str, str, Chunk, Severity, str | None]] = []
        self._history_vocabulary: Vocabulary | None = None

    # ---------------------------------------------------------------------------------------
    # configuration helpers

    def _resolve_denylist(self) -> Path | None:
        path = self.options.denylist
        if path is None and os.environ.get("DOCWIKI_DENYLIST"):
            path = Path(os.environ["DOCWIKI_DENYLIST"])
        if path is None:
            return None
        path = path.expanduser()
        if not path.is_file():
            raise ConfigError("deny-list file not found (path from --denylist or DOCWIKI_DENYLIST)")
        resolved = path.resolve()
        if resolved.is_relative_to(self.root):
            raise ConfigError("the deny-list must live outside the repository")
        return resolved

    def _relative(self, path: Path) -> str | None:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return None

    def _vocabulary_for(self, source: str) -> Vocabulary:
        """The vocabulary a closed-world candidate is judged against.

        The working tree and the site folders use the current word lists. History is judged
        against the current lists and against every version of the word lists found in the
        scanned commits (built once, only when history is scanned): a name that was valid in the
        sample world of its time is not reported again after the world has been replaced.
        """
        if source != "history":
            return self.vocabulary
        if self._history_vocabulary is None:
            self._history_vocabulary = self._build_history_vocabulary()
        return self._history_vocabulary

    def _build_history_vocabulary(self) -> Vocabulary:
        current = {
            "allow": self.vocabulary.allow,
            "tech": self.vocabulary.tech,
            "common": self.vocabulary.common,
        }
        role_of = {DEFAULT_ALLOWLIST.as_posix(): "allow"}
        if self.allowlist_rel is not None:
            role_of[self.allowlist_rel] = "allow"
        role_of[_COMMON_WORDS_REPO_PATH] = "common"
        role_of[_TECH_ALLOWLIST_REPO_PATH] = "tech"
        commits = gitsource.reachable_commits(self.root, self.options.commits)
        versions = gitsource.file_versions(self.root, commits, list(role_of))
        sets = {role: [terms] for role, terms in current.items()}
        for path, contents in versions.items():
            role = role_of[path]
            for number, data in enumerate(contents, start=1):
                origin = f"{path} (version {number} in history)"
                text = data.decode("utf-8", errors="replace")
                try:
                    terms = parse_termset(text, current[role].name, origin)
                except ConfigError as exc:
                    self.notices.append(Notice(path, "config", f"word list version skipped: {exc}"))
                    continue
                sets[role].append(terms)
                self.stats["history_word_list_versions"] += 1
        return Vocabulary(
            merge_termsets(current["allow"].name, sets["allow"]),
            merge_termsets(current["tech"].name, sets["tech"]),
            merge_termsets(current["common"].name, sets["common"]),
            learned=self.vocabulary.learned,
        )

    # ---------------------------------------------------------------------------------------
    # entry point

    def run(self) -> ScanReport:
        self._check_denylist()
        self._scan_worktree()
        for site in self.options.sites:
            self._scan_site(site)
        if self.options.history or self.options.commits is not None:
            self._scan_history(self.options.commits)
        self._run_closed_world()
        findings = self._deduplicate(self.findings)
        kept: list[Finding] = []
        suppressed: list[Finding] = []
        for finding in findings:
            if finding.id in self.ignore and not finding.rule.startswith(_UNSUPPRESSIBLE):
                suppressed.append(finding)
            else:
                kept.append(finding)
        kept.sort(key=Finding.sort_key)
        return ScanReport(
            findings=kept,
            notices=self.notices,
            suppressed=suppressed,
            stats=dict(self.stats),
            strict=self.options.strict,
            redact=self.options.redact,
        )

    def _check_denylist(self) -> None:
        if self.deny:
            self.stats["denylist_patterns"] = len(self.deny)
            return
        if self.deny_path is None:
            message = "no private deny-list configured (set DOCWIKI_DENYLIST or --denylist)"
        else:
            message = "the private deny-list contains no patterns"
        severity: Severity = "error" if self.options.strict else "warning"
        self.findings.append(
            Finding(
                rule="denylist-missing",
                severity=severity,
                path="-",
                location="configuration",
                message=message,
                id=finding_id("denylist-missing", "-", ""),
                source="config",
            )
        )

    # ---------------------------------------------------------------------------------------
    # working tree and site folders

    def _scan_worktree(self) -> None:
        tracked = gitsource.tracked_files(self.scan_root)
        untracked = (
            gitsource.untracked_files(self.scan_root) if self.options.include_untracked else []
        )
        ignored = set(gitsource.tracked_but_ignored(self.scan_root))
        for source, paths in (("worktree", tracked), ("untracked", untracked)):
            for path in paths:
                self._check_policy(path, source, tracked_ignored=path in ignored)
                self._scan_path(path, self.root / path, source)

    def _scan_site(self, site: Path) -> None:
        base = site if site.is_absolute() else Path.cwd() / site
        if not base.is_dir():
            raise ConfigError(f"--site {site} is not a directory")
        label = site.as_posix().rstrip("/")
        for file in sorted(base.rglob("*")):
            if file.is_file() or file.is_symlink():
                relative = file.relative_to(base).as_posix()
                display = f"{label}/{relative}"
                self._check_policy(relative, "site", tracked_ignored=False, display=display)
                vendor = self.site_vendor.is_vendor(relative)
                self._scan_path(display, file, "site", path_text=relative, vendor=vendor)

    def _check_policy(
        self, path: str, source: str, *, tracked_ignored: bool, display: str | None = None
    ) -> None:
        reason = policy_violation(path)
        if reason is None and tracked_ignored:
            reason = "tracked file matches a .gitignore pattern (ignored by policy); untrack it"
        if reason is not None:
            shown = display or path
            self._add(Finding(rule="policy-file", severity="error", path=shown, location="path",
                              message=reason, id=finding_id("policy-file", shown, shown),
                              source=source, key=shown))

    def _scan_path(
        self,
        path: str,
        full: Path,
        source: str,
        path_text: str | None = None,
        *,
        vendor: bool = False,
    ) -> None:
        self.stats[f"files_{source}"] += 1
        if full.is_symlink():
            target = os.readlink(full)
            extraction = Extraction(
                kind="symlink", chunks=[Chunk(target, "symlink target", closed_world=False)]
            )
        elif not full.is_file():
            self.notices.append(Notice(path, "skipped", "not a regular file in the working tree"))
            return
        else:
            size = full.stat().st_size
            if size > MAX_FILE_BYTES:
                self._add(Finding(rule="scan-error", severity="warning", path=path,
                                  location="file", message="file too large to scan",
                                  id=finding_id("scan-error", path, "size"), source=source))
                return
            self.stats["bytes"] += size
            extraction = extract_bytes(full.read_bytes(), path, path_on_disk=full)
        self._apply(path, extraction, source, path_text=path_text, vendor=vendor)

    # ---------------------------------------------------------------------------------------
    # rules applied to one extracted file

    def _closed_world_severity(self, path: str, source: str) -> Severity | None:
        if path == self.allowlist_rel:
            return None
        if source == "site":
            return "warning"
        if path.startswith("samples/"):
            return "error"
        if path.startswith("evals/golden/"):
            return "warning"
        return None

    def _apply(
        self,
        path: str,
        extraction: Extraction,
        source: str,
        commit: str | None = None,
        *,
        path_text: str | None = None,
        vendor: bool = False,
    ) -> None:
        """Apply every rule to one extracted file. ``path_text`` is the part of the path that
        belongs to the scanned content (site folders: the path inside the site)."""
        in_samples = path.startswith("samples/")
        own_path = path_text if path_text is not None else path
        self._text_rules(path, [Chunk(own_path, "path", kind="path", closed_world=False)], source,
                         commit)
        identifier_chunks = [chunk for chunk in extraction.chunks if chunk.identifiers]
        self._text_rules(path, identifier_chunks, source, commit, vendor=vendor,
                         lockfile=is_lock_or_registry_file(path))
        for issue in metadata_issues(
            extraction.metadata,
            in_samples=in_samples,
            known_word=self._vocabulary_for(source).knows,
        ):
            self._add(Finding(rule=issue.rule, severity=issue.severity, path=path,
                              location=issue.location, message=issue.message,
                              id=finding_id(issue.rule, path, issue.location + issue.value),
                              match=issue.value or "(empty)", source=source, commit=commit,
                              key=issue.location + issue.value))
        for location in extraction.exif:
            self._add(Finding(rule="metadata-exif", severity="error", path=path,
                              location=location, message="image carries EXIF metadata; strip it",
                              id=finding_id("metadata-exif", path, location), source=source,
                              commit=commit, key=location))
        for problem in extraction.problems:
            self._add(Finding(rule="scan-error", severity="warning", path=path, location="file",
                              message=f"not fully scanned: {problem}",
                              id=finding_id("scan-error", path, problem), source=source,
                              commit=commit, key=problem))
        if extraction.unknown_binary:
            self._add(Finding(rule="unscanned-binary", severity="warning", path=path,
                              location="file",
                              message="unknown binary format: only printable strings were scanned",
                              id=finding_id("unscanned-binary", path, ""), source=source,
                              commit=commit))
        if source != "history":
            for notice in extraction.notices:
                kind = "unscanned" if notice.startswith("unscanned") else "partial"
                self.notices.append(Notice(path, kind, notice))
        severity = self._closed_world_severity(path, source)
        if severity is None:
            return
        words = re.sub(r"[/\\.]+", " ", own_path)
        self._closed_world.append(
            (path, source, Chunk(words, "path", sentence_start=False, identifiers=False),
             severity, commit)
        )
        for chunk in extraction.chunks:
            if not chunk.closed_world:
                continue
            self._closed_world.append((path, source, chunk, severity, commit))
            if chunk.kind not in {"path", "metadata"} and _looks_like_prose(chunk.text):
                self.vocabulary.learn(chunk.text)

    def _text_rules(
        self,
        path: str,
        chunks: Sequence[Chunk],
        source: str,
        commit: str | None,
        *,
        lockfile: bool = False,
        vendor: bool = False,
    ) -> None:
        if not chunks:
            return
        starts: list[int] = []
        position = 0
        for chunk in chunks:
            starts.append(position)
            position += len(chunk.text) + 1
        joined = "\n".join(chunk.text for chunk in chunks)
        hits = deny_hits(joined, self.deny)
        hits.extend(
            identifier_hits(
                joined, allowed_guids=self.allowed_guids, domains=self.domains, lockfile=lockfile
            )
        )
        located: list[tuple[Hit, Chunk, str, int | None]] = []
        for hit in hits:
            index = bisect_right(starts, hit.start) - 1
            chunk = chunks[index]
            line = chunk.line
            location = chunk.location
            if line is not None and not chunk.decoded:
                line += joined.count("\n", starts[index], hit.start)
                if location.endswith(f"line {chunk.line}"):
                    location = location[: -len(f"line {chunk.line}")] + f"line {line}"
            located.append((hit, chunk, location, line))
        # A decoded copy (escapes resolved) only adds matches the escaped original did not have.
        reported = {
            (hit.rule, location, unescape_text(hit.raw))
            for hit, chunk, location, _ in located
            if not chunk.decoded
        }
        for hit, chunk, location, line in located:
            if chunk.decoded and (hit.rule, location, hit.raw) in reported:
                continue
            if vendor and not hit.sensitive and self.site_vendor.allows(hit.rule, hit.raw):
                self.stats["site_vendor_exempted"] += 1
                continue
            self._add(self._finding_from_hit(hit, path, location, line, source, commit))

    def _finding_from_hit(
        self, hit: Hit, path: str, location: str, line: int | None, source: str,
        commit: str | None,
    ) -> Finding:
        key = hit.raw.casefold() if hit.sensitive else hit.raw
        identifier = finding_id(hit.rule, path, location if hit.sensitive else hit.raw)
        return Finding(
            rule=hit.rule,
            severity=hit.severity,
            path=path,
            location=location,
            message=hit.message,
            id=identifier,
            line=line,
            match=hit.display,
            source=source,
            commit=commit,
            sensitive=hit.sensitive,
            key=key,
        )

    def _add(self, finding: Finding) -> None:
        marker = (
            finding.rule, finding.path, finding.location, finding.key, finding.source,
            finding.commit or "",
        )
        if marker in self._seen:
            return
        self._seen.add(marker)
        self.findings.append(finding)

    # ---------------------------------------------------------------------------------------
    # history

    def _scan_history(self, commits: list[str] | None) -> None:
        index_blobs = gitsource.head_blob_shas(self.root)
        binaries: dict[str, tuple[str, str]] = {}
        for commit in gitsource.iter_history(self.root, commits):
            self.stats["history_commits"] += 1
            for role, name, mail in (
                ("author", commit.author_name, commit.author_email),
                ("committer", commit.committer_name, commit.committer_email),
            ):
                identity = Chunk(f"{name} <{mail}>", f"commit {role}", kind="metadata",
                                 closed_world=False)
                self._text_rules(HISTORY_PATH, [identity], "history", commit.sha)
            message = [
                chunk
                for chunk in line_chunks(commit.message, closed_world=False,
                                         location_prefix="commit message ")
                if not _TOOL_TRAILER_RE.match(chunk.text)
            ]
            self._text_rules(HISTORY_PATH, message, "history", commit.sha)
            for item in commit.files.values():
                self._check_history_policy(item.path, commit.sha)
                path_chunk = Chunk(item.path, "path", kind="path", closed_world=False)
                self._text_rules(item.path, [path_chunk], "history", commit.sha)
                if item.binary and item.blob:
                    if item.blob not in index_blobs:
                        binaries.setdefault(item.blob, (item.path, commit.sha))
                    continue
                if not item.lines:
                    continue
                chunks = _history_chunks(item.path, item.lines)
                self._text_rules(item.path, [c for c in chunks if c.identifiers], "history",
                                 commit.sha, lockfile=is_lock_or_registry_file(item.path))
                severity = self._closed_world_severity(item.path, "history")
                if severity is not None:
                    for chunk in chunks:
                        if chunk.closed_world:
                            self._closed_world.append(
                                (item.path, "history", chunk, severity, commit.sha)
                            )
        for tag in gitsource.annotated_tags(self.root):
            self.stats["history_tags"] += 1
            chunks = [
                Chunk(f"{tag.tagger_name} <{tag.tagger_email}>", f"tag {tag.name} tagger",
                      kind="metadata", closed_world=False),
                *line_chunks(tag.message, closed_world=False,
                             location_prefix=f"tag {tag.name} message "),
            ]
            self._text_rules(HISTORY_PATH, chunks, "history", None)
        blobs = gitsource.read_blobs(self.root, list(binaries))
        for sha, data in blobs.items():
            path, commit_sha = binaries[sha]
            self.stats["history_blobs"] += 1
            self._apply(path, extract_bytes(data, path), "history", commit_sha)

    def _check_history_policy(self, path: str, commit: str) -> None:
        reason = policy_violation(path)
        if reason is not None:
            self._add(Finding(rule="policy-file", severity="error", path=path,
                              location="path", message=f"present in history: {reason}",
                              id=finding_id("policy-file", path, path), source="history",
                              commit=commit, key=path))

    # ---------------------------------------------------------------------------------------
    # closed world and de-duplication

    def _run_closed_world(self) -> None:
        aggregated: dict[tuple[str, str, str], Finding] = {}
        for path, source, chunk, severity, commit in self._closed_world:
            vocabulary = self._vocabulary_for(source)
            for candidate in find_candidates(chunk.text, chunk.sentence_start, vocabulary):
                term_key = candidate.term.casefold()
                group = "history" if source == "history" else source
                marker = (path, group, term_key)
                if marker in aggregated:
                    aggregated[marker].count += 1
                    continue
                aggregated[marker] = Finding(
                    rule="closed-world",
                    severity=severity,
                    path=path,
                    location=chunk.location,
                    message="proper noun not in the fiction allowlist, technology allowlist "
                    "or common words",
                    id=finding_id("closed-world", path, term_key),
                    line=chunk.line,
                    match=candidate.term,
                    detail=candidate.context if candidate.context != candidate.term else None,
                    source=source,
                    commit=commit,
                    key=term_key,
                )
        self.findings.extend(aggregated.values())
        if aggregated and not self.allow_present:
            self.notices.append(
                Notice("-", "config", "fiction allowlist not found; every name was reported")
            )

    def _deduplicate(self, findings: list[Finding]) -> list[Finding]:
        """Merge repeated history findings and drop history findings already in the tree."""
        current = {
            (finding.rule, finding.path, finding.key)
            for finding in findings
            if finding.source != "history"
        }
        merged: dict[tuple[str, str, str], Finding] = {}
        result: list[Finding] = []
        for finding in findings:
            if finding.source != "history":
                result.append(finding)
                continue
            marker = (finding.rule, finding.path, finding.key)
            if marker in current:
                continue
            if marker in merged:
                merged[marker].count += finding.count
                continue
            merged[marker] = finding
            result.append(finding)
        return result


def _looks_like_prose(text: str) -> bool:
    return len(text.split()) >= 6 and _PROSE_HINT_RE.search(text) is not None


def _history_chunks(path: str, lines: list[tuple[int, str]]) -> list[Chunk]:
    ext = suffix_of(path)
    chunks: list[Chunk] = []
    prose = ext in _HISTORY_PROSE_EXTS
    for number, text in lines:
        chunks.append(Chunk(text, f"line {number}", number, closed_world=prose,
                            sentence_start=ext not in CELL_EXTS))
        if ext in PYTHON_EXTS:
            for match in _PY_LITERAL_RE.finditer(text):
                value = next(group for group in match.groups() if group is not None)
                if value.strip():
                    chunks.append(Chunk(value, f"line {number}", number, identifiers=False,
                                        kind="literal"))
    return with_unescaped(chunks)
