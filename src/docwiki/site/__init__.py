"""Human view of a release: the Quartz site, its link checker and its security scan (site.md).

``docwiki.site.build_site(release_root, out_dir, *, base_url=None) -> Path`` is the entry point
used by the pipeline's ``site`` stage; ``python -m docwiki.site`` is its command line. It accepts
release folders (staged or published) and portable wiki folders (``.docwiki/manifest.json``).
"""

from docwiki.site.build import (
    DEFAULT_BANNER,
    PORTABLE_DIR,
    ReleaseView,
    SiteBuildError,
    apply_overlay,
    assemble_content,
    build_site,
    default_cache_dir,
    default_overlay_dir,
    detect_fictional,
    ensure_quartz,
    is_portable_wiki,
    normalize_base_url,
    open_release,
    read_quartz_version,
    site_settings,
)
from docwiki.site.linkcheck import LinkProblem, LinkReport, check_links, resolve_site_path
from docwiki.site.security import REPO_URL, SiteFinding, default_allowed_hosts, scan_site

__all__ = [
    "DEFAULT_BANNER",
    "PORTABLE_DIR",
    "REPO_URL",
    "LinkProblem",
    "LinkReport",
    "ReleaseView",
    "SiteBuildError",
    "SiteFinding",
    "apply_overlay",
    "assemble_content",
    "build_site",
    "check_links",
    "default_allowed_hosts",
    "default_cache_dir",
    "default_overlay_dir",
    "detect_fictional",
    "ensure_quartz",
    "is_portable_wiki",
    "normalize_base_url",
    "open_release",
    "read_quartz_version",
    "resolve_site_path",
    "scan_site",
    "site_settings",
]
