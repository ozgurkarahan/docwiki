"""Configuration files: allowlists, deny-list, reviewed identifiers and the ignore list."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from .model import ConfigError, sha_hex
from .words import WORD_RE, keys

TOOL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ALLOWED_GUIDS = TOOL_DIR / "allowed_guids.txt"
DEFAULT_ALLOWED_DOMAINS = TOOL_DIR / "allowed_domains.txt"
DEFAULT_TECH_ALLOWLIST = TOOL_DIR / "tech_allowlist.txt"
DEFAULT_COMMON_WORDS = TOOL_DIR / "common_words.txt"
DEFAULT_IGNORE = TOOL_DIR / "ignore.txt"
DEFAULT_SITE_VENDOR = TOOL_DIR / "site_vendor.txt"
DEFAULT_ALLOWLIST = Path("samples/fiction/allowlist.txt")

GUID_TEXT = r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
FINDING_ID_RE = re.compile(r"LG-[0-9a-f]{10}")

# Always allowed for e-mail addresses (spec: GitHub noreply author, example.com, example.org).
BUILTIN_EMAIL_DOMAINS = frozenset({"users.noreply.github.com", "example.com", "example.org"})


def read_entries(path: Path) -> list[tuple[int, str]]:
    """Non-blank lines that are not full-line ``#`` comments, with 1-based line numbers."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError(f"file not found: {path}") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from None
    entries: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        entries.append((number, line))
    return entries


def split_comment(line: str) -> tuple[str, str]:
    value, sep, comment = line.partition("#")
    return value.strip(), comment.strip() if sep else ""


@dataclass(slots=True)
class TermSet:
    """Allowed words (case- and accent-insensitive) and ``re:`` full-match patterns."""

    name: str
    words: set[str] = field(default_factory=set)
    regexes: list[re.Pattern[str]] = field(default_factory=list)
    entries: int = 0
    present: bool = True

    def add_term(self, term: str) -> None:
        for word in WORD_RE.findall(term):
            self.words.update(keys(word))
            if "-" in word:
                for part in word.split("-"):
                    self.words.update(keys(part))
        self.entries += 1

    def knows(self, word_keys: tuple[str, str]) -> bool:
        return word_keys[0] in self.words or word_keys[1] in self.words

    def regex_match(self, text: str) -> bool:
        return any(regex.fullmatch(text) for regex in self.regexes)


def load_termset(path: Path, name: str, *, required: bool) -> TermSet:
    """Load an allowlist file: one term per line, ``# comments``, ``re:<regex>`` patterns."""
    if not path.is_file():
        if required:
            raise ConfigError(f"{name} not found: {path}")
        return TermSet(name=name, present=False)
    terms = TermSet(name=name)
    for number, line in read_entries(path):
        if line.startswith("re:"):
            try:
                terms.regexes.append(re.compile(line[3:].strip(), re.IGNORECASE))
            except re.error as exc:
                message = f"{path} line {number}: invalid regular expression: {exc}"
                raise ConfigError(message) from None
            terms.entries += 1
            continue
        value, _ = split_comment(line)
        if value:
            terms.add_term(value)
    return terms


@dataclass(frozen=True, slots=True)
class DenyPattern:
    """One private deny-list pattern. ``rule`` is ``deny:<sha256(pattern)[:8]>``."""

    rule: str
    regex: re.Pattern[str]
    line_no: int


def deny_rule_id(pattern: str) -> str:
    return f"deny:{sha_hex(pattern, 8)}"


def load_denylist(path: Path) -> list[DenyPattern]:
    """One case-insensitive regex per line; full-line ``#`` comments; surrounding blanks ignored.

    Error messages never include the pattern text (the deny-list is private).
    """
    patterns: list[DenyPattern] = []
    for number, line in read_entries(path):
        try:
            regex = re.compile(line, re.IGNORECASE)
        except re.error as exc:
            raise ConfigError(
                f"deny-list line {number}: invalid regular expression ({exc.msg} at position "
                f"{exc.pos}); the pattern is not shown"
            ) from None
        patterns.append(DenyPattern(deny_rule_id(line), regex, number))
    return patterns


def load_allowed_guids(path: Path) -> dict[str, str]:
    """Reviewed public GUIDs. Every line is ``<guid>  # why it is public``."""
    allowed: dict[str, str] = {}
    if not path.is_file():
        raise ConfigError(f"allowed GUID list not found: {path}")
    for number, line in read_entries(path):
        value, comment = split_comment(line)
        if not re.fullmatch(GUID_TEXT, value):
            raise ConfigError(f"{path.name} line {number}: expected '<guid>  # comment'")
        if not comment:
            raise ConfigError(
                f"{path.name} line {number}: every allowed GUID needs a '# comment' saying "
                "why it is public"
            )
        allowed[value.lower()] = comment
    return allowed


@dataclass(slots=True)
class DomainPolicy:
    """Allowed e-mail / host domains: exact domains (and their subdomains), ``.suffix`` entries
    and exact e-mail addresses."""

    domains: set[str] = field(default_factory=lambda: set(BUILTIN_EMAIL_DOMAINS))
    suffixes: set[str] = field(default_factory=set)
    addresses: set[str] = field(default_factory=set)

    def allows_domain(self, domain: str) -> bool:
        domain = domain.lower().rstrip(".")
        if any(domain == item or domain.endswith("." + item) for item in self.domains):
            return True
        return any(domain.endswith(suffix) for suffix in self.suffixes)

    def allows_address(self, address: str) -> bool:
        address = address.lower()
        if address in self.addresses:
            return True
        return self.allows_domain(address.rpartition("@")[2])


def load_allowed_domains(path: Path) -> DomainPolicy:
    policy = DomainPolicy()
    if not path.is_file():
        raise ConfigError(f"allowed domain list not found: {path}")
    for number, line in read_entries(path):
        value, _ = split_comment(line)
        value = value.lower()
        if not value:
            continue
        if "@" in value:
            policy.addresses.add(value)
        elif value.startswith("."):
            policy.suffixes.add(value)
        elif re.fullmatch(r"[a-z0-9.-]+\.[a-z0-9-]+", value):
            policy.domains.add(value)
        else:
            raise ConfigError(f"{path.name} line {number}: expected a domain, .suffix or address")
    return policy


def load_ignore(path: Path) -> dict[str, str]:
    """Reviewed false positives: ``LG-xxxxxxxxxx  # reason`` per line (reason mandatory)."""
    if not path.is_file():
        return {}
    ignored: dict[str, str] = {}
    for number, line in read_entries(path):
        value, reason = split_comment(line)
        if not FINDING_ID_RE.fullmatch(value):
            raise ConfigError(f"{path.name} line {number}: expected 'LG-<10 hex>  # reason'")
        if not reason:
            raise ConfigError(f"{path.name} line {number}: an ignored finding needs a reason")
        ignored[value] = reason
    return ignored


_VENDOR_LINE_RE = re.compile(r"^(?P<value>.*?)(?:\s+#\s*(?P<reason>.*))?$")


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Path glob: ``**/`` any folders, ``*`` and ``?`` within one path segment."""
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(parts), re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class VendorAllowance:
    rule: str
    regex: re.Pattern[str] | None
    sha256: str | None
    reason: str

    def matches(self, rule: str, text: str) -> bool:
        if rule != self.rule:
            return False
        if self.regex is not None:
            return self.regex.fullmatch(text) is not None
        digest = hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()
        return self.sha256 is not None and digest.startswith(self.sha256)


@dataclass(slots=True)
class SiteVendorPolicy:
    """Reviewed exemptions for third-party bundles of a built site (``site_vendor.txt``)."""

    globs: list[re.Pattern[str]] = field(default_factory=list)
    allowances: list[VendorAllowance] = field(default_factory=list)

    def is_vendor(self, relative_path: str) -> bool:
        return any(glob.fullmatch(relative_path) for glob in self.globs)

    def allows(self, rule: str, text: str) -> bool:
        return any(allowance.matches(rule, text) for allowance in self.allowances)


def load_site_vendor(path: Path, *, required: bool = False) -> SiteVendorPolicy:
    """``file <glob>`` and ``allow <rule> re:<regex>|sha256:<hex>  # reason`` lines."""
    policy = SiteVendorPolicy()
    if not path.is_file():
        if required:
            raise ConfigError(f"site vendor list not found: {path}")
        return policy
    for number, line in read_entries(path):
        match = _VENDOR_LINE_RE.match(line)
        value = (match.group("value") if match else line).strip()
        reason = ((match.group("reason") if match else "") or "").strip()
        kind, _, rest = value.partition(" ")
        rest = rest.strip()
        where = f"{path.name} line {number}"
        if kind == "file" and rest:
            policy.globs.append(glob_to_regex(rest))
            continue
        if kind != "allow":
            raise ConfigError(f"{where}: expected 'file <glob>' or 'allow <rule> <pattern>'")
        rule, _, spec = rest.partition(" ")
        spec = spec.strip()
        if not reason:
            raise ConfigError(f"{where}: an allow entry needs a '# reason'")
        if rule.startswith("deny") or not rule:
            raise ConfigError(f"{where}: deny-list findings can never be exempted")
        if spec.startswith("re:"):
            try:
                regex = re.compile(spec[3:])
            except re.error as exc:
                raise ConfigError(f"{where}: invalid regular expression: {exc}") from None
            policy.allowances.append(VendorAllowance(rule, regex, None, reason))
        elif re.fullmatch(r"sha256:[0-9a-f]{16,64}", spec):
            policy.allowances.append(VendorAllowance(rule, None, spec[7:], reason))
        else:
            raise ConfigError(f"{where}: expected 're:<regex>' or 'sha256:<16-64 hex>'")
    return policy
