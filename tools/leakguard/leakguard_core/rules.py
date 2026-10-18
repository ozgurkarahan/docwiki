"""Detection rules: deny-list, identifiers, secrets, hosts, package mirrors, policy files and
document metadata."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from .config import DenyPattern, DomainPolicy
from .model import GENERATOR_AUTHOR, MetaField, Severity
from .words import WORD_RE, is_capitalised

_GUID = r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
GUID_RE = re.compile(rf"(?<![0-9A-Fa-f]){_GUID}(?![0-9A-Fa-f])")
RESOURCE_ID_RE = re.compile(
    rf"/subscriptions/(?P<guid>{_GUID})(?![0-9A-Fa-f])(?:/[^\s\"'<>`]*)?", re.IGNORECASE
)
EMAIL_RE = re.compile(
    r"(?<![\w.%+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@"
    r"(?P<domain>(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63})(?![\w-])"
)
WINDOWS_HOME_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:(?:\\{1,2}|/)(?:Users|Documents and Settings)(?:\\{1,2}|/)"
    r"(?P<user>[^\\/\s\"'<>|:*?]+)",
    re.IGNORECASE,
)
UNIX_HOME_RE = re.compile(r"(?<![\w.~-])/(?:home|Users)/(?P<user>[A-Za-z0-9._-]+)")
PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:[A-Z0-9]+ ){0,3}PRIVATE KEY(?: BLOCK)?-----|PuTTY-User-Key-File-\d+:"
)
GITHUB_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b"
)
AZURE_KEY_RE = re.compile(
    r"\b(?P<key>AccountKey|SharedAccessKey|SharedSecretValue|PrimaryKey|SecondaryKey)"
    r"\s*=\s*(?P<value>[A-Za-z0-9+/]{20,}={0,2})",
    re.IGNORECASE,
)
SAS_SIG_RE = re.compile(r"(?:[?&;]|\b)sig=(?P<value>[A-Za-z0-9%+/_-]{30,}(?:=|%3D){0,2})")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]*")
OTHER_TOKEN_RE = re.compile(
    r"\b(?:AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|xox[abposr]-[A-Za-z0-9-]{10,}"
    r"|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|npm_[A-Za-z0-9]{36})\b"
)
NPM_AUTH_RE = re.compile(r"_auth(?:Token)?\s*=\s*(?P<value>[^\s\"']{8,})")
SECRET_ASSIGN_RE = re.compile(
    r"(?P<key>\b(?:api[_-]?key|apikey|client[_-]?secret|access[_-]?token|auth[_-]?token"
    r"|secret[_-]?key|private[_-]?key|password|passwd)\b)[\"']?\s*(?::=|=>|:|=)\s*"
    r"(?P<q>[\"'])(?P<value>[^\"'\s]{8,})(?P=q)",
    re.IGNORECASE,
)
SECRET_ENV_RE = re.compile(
    r"^[ \t]*(?:export[ \t]+)?(?P<key>[A-Z0-9_]*(?:API_KEY|APIKEY|CLIENT_SECRET|ACCESS_TOKEN"
    r"|AUTH_TOKEN|SECRET_KEY|PASSWORD|PASSWD|_TOKEN|_SECRET))[ \t]*=[ \t]*"
    r"(?P<value>[^\s\"'#]{8,})[ \t]*$",
    re.MULTILINE,
)
URL_CREDENTIALS_RE = re.compile(
    r"\b[a-z][a-z0-9+.-]*://(?P<user>[^\s/:@\"'<>]+):(?P<value>[^\s/@\"'<>]+)@[^\s/\"'<>]+",
    re.IGNORECASE,
)
URL_RE = re.compile(r"\b(?:https?|git\+https|sftp|ftp)://[^\s\"'<>`)\]}|\\]+", re.IGNORECASE)
URL_HOST_RE = re.compile(
    r"\b[a-z][a-z0-9+.-]*://(?:[^\s/@\"'<>]*@)?"
    r"(?P<host>[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*)",
    re.IGNORECASE,
)
UNC_HOST_RE = re.compile(r"(?<![\w\\])\\\\(?P<host>[A-Za-z0-9][A-Za-z0-9.-]*)\\[^\s\\]")
BARE_HOST_RE = re.compile(
    r"(?<![\w.@/:-])(?P<host>(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.){1,8}[a-z][a-z0-9-]*[a-z0-9])"
    r"(?![\w-]|\.[a-z0-9])",
    re.IGNORECASE,
)

_FILE_TLDS = frozenset(
    {
        "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "pdf", "css", "js", "mjs", "json",
        "md", "html", "htm", "txt", "xml", "yaml", "yml", "py", "ts", "tsx", "jsx", "zip", "gz",
        "lock", "toml", "csv", "xlsx", "docx", "pptx", "eml", "vtt", "map", "woff", "woff2",
    }
)
_GENERIC_USERS = frozenset(
    {
        "user", "username", "users", "me", "you", "yourname", "your-name", "your_name",
        "youruser", "your-user", "name", "runner", "ubuntu", "vscode", "codespace", "node",
        "app", "docker", "root", "ci", "default", "public", "shared", "guest", "admin",
        "administrator", "example", "someone", "all users", "default user", "dev", "developer",
        "<user>", "...", "x",
    }
)
_PLACEHOLDER_RE = re.compile(
    r"^(?:\$|<|\{|%|\[|\*{3,}|x{4,}|\.{3}|your|example|placeholder|change[-_]?me|dummy|fake"
    r"|redacted|replace|todo|none|null|true|false|secret|password|passw0rd|test|sample|xxx"
    r"|env[.:(]|os\.environ|process\.env|secrets\.)",
    re.IGNORECASE,
)
INTERNAL_TLDS = frozenset({"internal", "lan", "corp", "intranet", "intra", "localdomain"})
URL_ONLY_INTERNAL_TLDS = frozenset({"local", "home", "private"})
INTERNAL_LABELS = frozenset({"corp", "intranet", "intra", "internal"})
_ALLOWED_HOSTS = frozenset(
    {
        "localhost", "host.docker.internal", "gateway.docker.internal",
        "metadata.google.internal", "kubernetes.docker.internal",
    }
)
_RESERVED_SUFFIXES = (".example", ".test", ".invalid", ".localhost", ".cluster.local")
_CODE_RECEIVERS = frozenset(
    {
        "self", "cls", "this", "os", "sys", "ctx", "config", "settings", "args", "opts",
        "options", "threading", "obj", "request", "req", "response", "resp", "app", "env",
        "module", "pkg", "super", "window", "document", "event", "props", "state",
    }
)
# Common public top-level domains: a bare (non-URL) host must end with one to be considered.
_PUBLIC_TLDS = frozenset(
    {
        "com", "net", "org", "io", "dev", "app", "cloud", "ai", "co", "biz", "info", "eu", "uk",
        "de", "fr", "nl", "be", "ch", "at", "it", "es", "pt", "se", "no", "dk", "fi", "pl", "cz",
        "ie", "us", "ca", "au", "nz", "jp", "cn", "in", "br", "mx", "za", "sg", "hk", "kr", "tw",
        "ru", "tr", "gr", "hu", "ro", "sk", "si", "lu", "lt", "lv", "ee", "is", "global", "tech",
        "site", "online", "systems", "solutions", "energy", "industries", "group", "company",
    }
)

PUBLIC_REGISTRY_HOSTS = frozenset({"pypi.org", "files.pythonhosted.org", "registry.npmjs.org"})
_PUBLIC_REGISTRY_SUFFIXES = (".pypi.org",)
# Documentation websites of the public registries (not package indexes).
_REGISTRY_WEBSITES = frozenset(
    {"npmjs.com", "www.npmjs.com", "docs.npmjs.com", "npmjs.org", "pypi.python.org"}
)
_MIRROR_HOST_LABELS = frozenset({"pypi", "npm", "pypimirror", "npmregistry"})
_MIRROR_HOST_MARKERS = (
    "artifactory", "nexus", "devpi", "jfrog", "npmmirror", "cloudsmith", "gemfury", "verdaccio",
    "proget", "packagecloud", "pkgs.dev.azure.com", "pkgs.visualstudio.com", "mirror",
)
_MIRROR_PATH_RE = re.compile(
    r"(?:^|/)(?:simple|_packaging|api/pypi|api/npm|pypi/simple|repository/(?:pypi|npm)[^/]*"
    r"|npm/registry)(?:/|$)",
    re.IGNORECASE,
)
_MIRROR_CONTEXT_RE = re.compile(
    r"index[-_]url|extra[-_]index|find[-_]links|registry\s*=|registry:|tool\.uv\.index"
    r"|UV_INDEX|PIP_INDEX|npm_config_registry|\bindex\s*=|\[\[\s*index\s*\]\]",
    re.IGNORECASE,
)

LOCK_FILES = frozenset(
    {
        "uv.lock", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
        "poetry.lock", "pipfile.lock", "bun.lockb", "pdm.lock",
    }
)
_REGISTRY_CONFIG_FILES = frozenset(
    {".npmrc", ".yarnrc", ".yarnrc.yml", "pip.conf", "pip.ini", "uv.toml", ".pypirc"}
)
LOCK_PUBLIC_HOSTS = PUBLIC_REGISTRY_HOSTS | {"github.com", "codeload.github.com"}
_KEY_FILE_EXTS = frozenset({".pem", ".key", ".pfx", ".p12", ".jks", ".keystore", ".ppk"})
_KEY_FILE_NAMES = frozenset(
    {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".pypirc", ".netrc", ".git-credentials"}
)
KNOWN_TOOL_AUTHORS = frozenset(
    {
        "", GENERATOR_AUTHOR.lower(), "python-docx", "openpyxl", "python-pptx", "fpdf2", "fpdf",
        "docwiki", "unknown", "author",
    }
)


@dataclass(frozen=True, slots=True)
class Hit:
    """A rule match inside a text."""

    rule: str
    severity: Severity
    start: int
    end: int
    raw: str
    display: str | None
    message: str
    sensitive: bool = False
    priority: int = 50


def mask_secret(value: str) -> str:
    return f"{value[:4]}... ({len(value)} chars)"


def is_placeholder(value: str) -> bool:
    if _PLACEHOLDER_RE.match(value):
        return True
    if len(set(value)) <= 2:
        return True
    return "{{" in value or "}}" in value or "${" in value


def deny_hits(text: str, patterns: Iterable[DenyPattern]) -> list[Hit]:
    hits: list[Hit] = []
    for pattern in patterns:
        for match in pattern.regex.finditer(text):
            if match.end() == match.start():
                continue
            hits.append(
                Hit(
                    rule=pattern.rule,
                    severity="error",
                    start=match.start(),
                    end=match.end(),
                    raw=match.group(),
                    display=match.group(),
                    message="private deny-list term",
                    sensitive=True,
                    priority=100,
                )
            )
    return hits


def _context_before(text: str, position: int, width: int = 80) -> str:
    """Text just before ``position`` on the same line (a bounded window: minified bundles have
    lines of hundreds of kilobytes, whose unrelated words must not count as context)."""
    start = max(text.rfind("\n", 0, position) + 1, position - width)
    return text[start:position]


def identifier_hits(
    text: str,
    *,
    allowed_guids: set[str] | dict[str, str],
    domains: DomainPolicy,
    lockfile: bool = False,
) -> list[Hit]:
    """All identifier, secret, host and mirror matches in ``text`` (overlaps resolved)."""
    hits: list[Hit] = []
    add = hits.append

    for match in PRIVATE_KEY_RE.finditer(text):
        add(Hit("private-key", "error", match.start(), match.end(), match.group(),
                "private key block", "private key material", priority=95))
    for match in GITHUB_TOKEN_RE.finditer(text):
        add(Hit("secret-github-token", "error", match.start(), match.end(), match.group(),
                mask_secret(match.group()), "GitHub token", priority=90))
    for match in OTHER_TOKEN_RE.finditer(text):
        add(Hit("secret-token", "error", match.start(), match.end(), match.group(),
                mask_secret(match.group()), "access token or API key", priority=90))
    for match in AZURE_KEY_RE.finditer(text):
        value = match.group("value")
        if not is_placeholder(value):
            add(Hit("secret-azure-key", "error", match.start(), match.end(), match.group(),
                    f"{match.group('key')}={mask_secret(value)}",
                    "Azure storage/service key", priority=90))
    for match in SAS_SIG_RE.finditer(text):
        value = match.group("value")
        if (
            re.search(r"[A-Z]", value)
            and re.search(r"[a-z]", value)
            and re.search(r"[0-9%]", value)
            and not is_placeholder(value)
        ):
            add(Hit("secret-azure-sas", "error", match.start(), match.end(), match.group(),
                    f"sig={mask_secret(value)}", "Azure SAS signature", priority=90))
    for match in JWT_RE.finditer(text):
        add(Hit("secret-jwt", "error", match.start(), match.end(), match.group(),
                mask_secret(match.group()), "JSON Web Token", priority=90))
    for match in NPM_AUTH_RE.finditer(text):
        value = match.group("value")
        if not is_placeholder(value):
            add(Hit("secret-token", "error", match.start(), match.end(), match.group(),
                    mask_secret(value), "npm registry credential", priority=90))
    for regex in (SECRET_ASSIGN_RE, SECRET_ENV_RE):
        for match in regex.finditer(text):
            value = match.group("value")
            if is_placeholder(value):
                continue
            add(Hit("secret-assignment", "error", match.start("value"), match.end("value"),
                    value, f"{match.group('key')}={mask_secret(value)}",
                    "hard-coded secret value", priority=80))
    for match in URL_CREDENTIALS_RE.finditer(text):
        value = match.group("value")
        if len(value) >= 6 and not is_placeholder(value):
            add(Hit("secret-url-credentials", "error", match.start(), match.end(), match.group(),
                    f"{match.group('user')}:{mask_secret(value)}@...",
                    "credentials embedded in a URL", priority=85))

    for match in RESOURCE_ID_RE.finditer(text):
        if match.group("guid").lower() in allowed_guids:
            continue
        add(Hit("azure-resource-id", "error", match.start(), match.end(), match.group(),
                match.group(), "Azure subscription resource ID", priority=70))
    for match in GUID_RE.finditer(text):
        if match.group().lower() in allowed_guids:
            continue
        add(Hit("guid", "error", match.start(), match.end(), match.group(), match.group(),
                "GUID (subscription, tenant, object or resource identifier?)", priority=60))

    for match in EMAIL_RE.finditer(text):
        address = match.group()
        domain = match.group("domain").lower()
        if domain.rsplit(".", 1)[-1] in _FILE_TLDS or domains.allows_address(address):
            continue
        add(Hit("email", "error", match.start(), match.end(), address, address,
                "e-mail address", priority=65))

    for regex in (WINDOWS_HOME_RE, UNIX_HOME_RE):
        for match in regex.finditer(text):
            user = match.group("user").strip().lower()
            if user in _GENERIC_USERS or user[:1] in "{$%<[(" or user.startswith("your"):
                continue
            add(Hit("home-path", "error", match.start(), match.end(), match.group(),
                    match.group(), "home-directory path (local machine path)", priority=55))

    hits.extend(_host_hits(text, domains))
    if lockfile:
        hits.extend(_lockfile_hits(text))
    else:
        hits.extend(_mirror_hits(text))
    return _resolve_overlaps(hits)


def _host_allowed(host: str, domains: DomainPolicy) -> bool:
    host = host.lower().rstrip(".")
    if host in _ALLOWED_HOSTS or host.endswith(_RESERVED_SUFFIXES):
        return True
    return domains.allows_domain(host)


def _is_internal_host(host: str, *, in_url: bool) -> bool:
    labels = host.lower().split(".")
    tld = labels[-1]
    if len(labels) == 1:
        return in_url and host.lower() != "localhost"
    if tld in INTERNAL_TLDS:
        return in_url or len(labels) >= 3 or tld != "internal"
    if in_url and tld in URL_ONLY_INTERNAL_TLDS:
        return True
    inner = labels[:-1]
    if any(label in INTERNAL_LABELS for label in inner) or any(
        "intranet" in label.split("-") for label in labels
    ):
        return in_url or tld in _PUBLIC_TLDS or tld in INTERNAL_TLDS
    return False


def _host_hits(text: str, domains: DomainPolicy) -> list[Hit]:
    hits: list[Hit] = []
    url_spans: list[tuple[int, int]] = []
    for regex in (URL_HOST_RE, UNC_HOST_RE):
        for match in regex.finditer(text):
            host = match.group("host")
            url_spans.append((match.start("host"), match.end("host")))
            if _host_allowed(host, domains) or not _is_internal_host(host, in_url=True):
                continue
            hits.append(Hit("internal-host", "error", match.start("host"), match.end("host"),
                            host, host, "internal-looking host name", priority=50))
    for match in BARE_HOST_RE.finditer(text):
        start, end = match.start("host"), match.end("host")
        if any(s <= start < e for s, e in url_spans):
            continue
        host = match.group("host")
        labels = host.lower().split(".")
        if labels[0] in _CODE_RECEIVERS or _host_allowed(host, domains):
            continue
        if _is_internal_host(host, in_url=False):
            hits.append(Hit("internal-host", "error", start, end, host, host,
                            "internal-looking host name", priority=50))
    return hits


def _url_host(url: str) -> tuple[str, str]:
    try:
        parts = urlsplit(url)
    except ValueError:
        return "", ""
    return (parts.hostname or "").lower(), parts.path or ""


def is_public_registry(host: str) -> bool:
    return host in PUBLIC_REGISTRY_HOSTS or host.endswith(_PUBLIC_REGISTRY_SUFFIXES)


def _looks_like_mirror(host: str, path: str) -> bool:
    if any(marker in host for marker in _MIRROR_HOST_MARKERS):
        return True
    if any(label in _MIRROR_HOST_LABELS for label in re.split(r"[.-]", host)):
        return True
    return bool(_MIRROR_PATH_RE.search(path))


def _mirror_hits(text: str) -> list[Hit]:
    hits: list[Hit] = []
    for match in URL_RE.finditer(text):
        url = match.group().rstrip(".,;:")
        host, path = _url_host(url)
        if not host or is_public_registry(host) or host in _REGISTRY_WEBSITES:
            continue
        if host.endswith(_RESERVED_SUFFIXES) or host in {"example.com", "example.org"}:
            continue
        context = _MIRROR_CONTEXT_RE.search(_context_before(text, match.start())) is not None
        if context or _looks_like_mirror(host, path):
            hits.append(Hit("package-mirror", "error", match.start(), match.start() + len(url),
                            url, url, "URL of a non-public package index or mirror",
                            priority=45))
    return hits


def _lockfile_hits(text: str) -> list[Hit]:
    hits: list[Hit] = []
    seen: set[str] = set()
    for match in URL_RE.finditer(text):
        host, _ = _url_host(match.group())
        if not host or host in LOCK_PUBLIC_HOSTS or host.endswith(_PUBLIC_REGISTRY_SUFFIXES):
            continue
        if host in seen:
            continue
        seen.add(host)
        hits.append(Hit("lockfile-mirror", "error", match.start(), match.end(), host, host,
                        "lock or registry file resolves packages from a non-public host",
                        priority=45))
    return hits


def _resolve_overlaps(hits: list[Hit]) -> list[Hit]:
    """Keep the highest-priority hit where hits overlap (e.g. a GUID inside a resource ID)."""
    kept: list[Hit] = []
    for hit in sorted(hits, key=lambda h: (-h.priority, h.start)):
        if hit.sensitive or not any(
            not other.sensitive and hit.start < other.end and other.start < hit.end
            for other in kept
        ):
            kept.append(hit)
    return sorted(kept, key=lambda h: (h.start, -h.priority))


# --------------------------------------------------------------------------------------------
# Path policy


def is_lock_or_registry_file(path: str) -> bool:
    name = PurePosixPath(path).name.lower()
    if name in LOCK_FILES or name in _REGISTRY_CONFIG_FILES:
        return True
    return bool(re.fullmatch(r"(?:.*[-_.])?requirements(?:[-_.].*)?\.(?:txt|in)", name))


def policy_violation(path: str) -> str | None:
    """Reason why a path must never be committed, or ``None``."""
    pure = PurePosixPath(path)
    name = pure.name.lower()
    if name in LOCK_FILES:
        return "lock file (may embed private package-mirror URLs); never commit it"
    if name == ".env" or name.startswith(".env."):
        return "environment file (.env*); never commit it"
    if name in _KEY_FILE_NAMES:
        return "credential or key file; never commit it"
    if pure.suffix.lower() in _KEY_FILE_EXTS:
        return "key or certificate container file; never commit it"
    return None


# --------------------------------------------------------------------------------------------
# Metadata


@dataclass(frozen=True, slots=True)
class MetaIssue:
    rule: str
    severity: Severity
    location: str
    message: str
    value: str


def _personal_hint(value: str, known_word: object) -> bool:
    """Heuristic: does a tool/creator string contain a personal name or a user name?"""
    if "@" in value or re.search(r"\b[\w.-]+\\[\w.-]+\b", value):
        return True
    if WINDOWS_HOME_RE.search(value) or UNIX_HOME_RE.search(value):
        return True
    for word in WORD_RE.findall(value):
        if len(word) > 1 and is_capitalised(word) and not known_word(word):  # type: ignore[operator]
            return True
    return False


def metadata_issues(
    metadata: Iterable[MetaField], *, in_samples: bool, known_word: object
) -> list[MetaIssue]:
    issues: list[MetaIssue] = []
    for meta in metadata:
        value = meta.value.strip()
        person_field = (meta.fmt == "office" and meta.name in {"creator", "lastModifiedBy"}) or (
            meta.fmt == "pdf" and meta.name == "Author"
        )
        label = f"Office {meta.name}" if meta.fmt == "office" else f"PDF {meta.name}"
        rule = "metadata-office-author" if meta.fmt == "office" else "metadata-pdf"
        if person_field:
            if in_samples and value not in ("", GENERATOR_AUTHOR):
                message = f"{label} must be '{GENERATOR_AUTHOR}' or empty in samples/"
                issues.append(MetaIssue(rule, "error", meta.location, message, value))
            elif not in_samples and value.lower() not in KNOWN_TOOL_AUTHORS:
                message = f"{label} metadata may be a personal name"
                issues.append(MetaIssue(rule, "warning", meta.location, message, value))
        elif (
            meta.fmt == "pdf"
            and meta.name in {"Creator", "Producer"}
            and value
            and value != GENERATOR_AUTHOR
            and _personal_hint(value, known_word)
        ):
            message = f"{label} metadata looks like it contains a personal or user name"
            severity: Severity = "error" if in_samples else "warning"
            issues.append(MetaIssue(rule, severity, meta.location, message, value))
    return issues
