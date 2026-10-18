"""DocWiki Studio: a signed-in web app to add documents, follow the pipeline and work with the
Researcher and Librarian agents (``python -m docwiki.studio``, ``docwiki studio``)."""

from docwiki.studio.app import create_app
from docwiki.studio.config import StudioConfig, StudioConfigError
from docwiki.studio.wiring import build_app

__all__ = ["StudioConfig", "StudioConfigError", "build_app", "create_app"]
