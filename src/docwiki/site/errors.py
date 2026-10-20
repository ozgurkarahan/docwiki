"""Errors of the site build, shared by :mod:`docwiki.site.build` and :mod:`docwiki.site.answers`."""

from __future__ import annotations

__all__ = ["SiteBuildError"]


class SiteBuildError(RuntimeError):
    """The site could not be built, or the built site failed its checks."""
