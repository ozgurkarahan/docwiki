"""French-canonical site with an English mirror: aliases and language negotiation (ADR 0012)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

from docwiki.portal import SECURITY_HEADERS, create_app

ENGLISH = {"accept-language": "en-GB,en;q=0.9"}
FRENCH = {"accept-language": "fr-FR,fr;q=0.9,en;q=0.8"}

PAGES = (
    "index.html",
    "404.html",
    "sources/x.html",
    "sources/only-fr.html",
    "pipeline.html",
    "documents.html",
    "evidence/src-1/index.html",
    "en/index.html",
    "en/sources/x.html",
    "en/pipeline.html",
    "en/documents.html",
    "en/evidence/src-1/index.html",
)


def build_site(root: Path, languages: tuple[str, ...] | None = ("fr", "en")) -> Path:
    for rel in PAGES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"<!DOCTYPE html><title>{rel}</title>", encoding="utf-8")
    for rel, text in {
        "static/app.js": "console.log(1)",
        "en/static/app.js": "console.log(1)",
        "static/contentIndex.json": "{}",
        "en/static/contentIndex.json": "{}",
    }.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    if languages is not None:
        payload = {"schema": 1, "canonical": languages[0], "languages": list(languages)}
        (root / "static" / "docwiki" / "languages.json").parent.mkdir(parents=True, exist_ok=True)
        (root / "static" / "docwiki" / "languages.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
    return root


@pytest.fixture
def client(tmp_path: Path):
    with TestClient(create_app(site_dir=build_site(tmp_path / "site"))) as test_client:
        yield test_client


def get(client: TestClient, path: str, **headers: str) -> httpx.Response:
    return client.get(path, headers=headers, follow_redirects=False)


@pytest.mark.parametrize(
    ("path", "location"),
    [
        ("/", "/en/"),
        ("/sources/x", "/en/sources/x"),
        ("/sources/x?ref=1", "/en/sources/x?ref=1"),
        ("/pipeline", "/en/pipeline"),
        ("/documents?doc=a", "/en/documents?doc=a"),
    ],
)
def test_english_browser_goes_to_the_mirror(client: TestClient, path: str, location: str) -> None:
    response = get(client, path, **ENGLISH)
    assert response.status_code == 302
    assert response.headers["location"] == location
    assert response.headers["vary"] == "Accept-Language, Cookie"
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value
    assert client.head(path, headers=ENGLISH, follow_redirects=False).status_code == 302
    assert get(client, location, **ENGLISH).status_code == 200


@pytest.mark.parametrize(
    "accept",
    [
        "fr-FR,fr;q=0.9,en;q=0.8",
        "fr,en;q=0.9",
        "en;q=0.5,fr;q=0.5",
        "fr-CA",
        "de-DE,de;q=0.9",
        "*",
        "",
        ";;;,,,q=abc",
        "en;q=2,fr;q=0.1",
        "en;q=nan",
        "en;q=-1",
        "en_US",
        "fr;q=0.9," + "x" * 2000 + ",en",
    ],
)
def test_other_readers_stay_on_the_canonical_page(client: TestClient, accept: str) -> None:
    response = get(client, "/sources/x", **{"accept-language": accept})
    assert response.status_code == 200
    assert response.headers["vary"] == "Accept-Language, Cookie"


@pytest.mark.parametrize(
    "accept", ["en", "en-US", "en-US,fr;q=0.5", "de,en;q=0.8,fr;q=0.7", "*,fr;q=0.2"]
)
def test_accept_language_preferring_english(client: TestClient, accept: str) -> None:
    response = get(client, "/pipeline", **{"accept-language": accept})
    assert response.status_code == 302 and response.headers["location"] == "/en/pipeline"


def test_without_accept_language_nothing_moves(client: TestClient) -> None:
    assert get(client, "/pipeline").status_code == 200


def test_the_language_cookie_wins(client: TestClient) -> None:
    client.cookies.set("docwiki_lang", "fr")
    assert get(client, "/sources/x", **ENGLISH).status_code == 200
    client.cookies.set("docwiki_lang", "en")
    moved = get(client, "/sources/x", **FRENCH)
    assert moved.status_code == 302 and moved.headers["location"] == "/en/sources/x"
    assert get(client, "/en/sources/x", **FRENCH).status_code == 200  # never sent back
    client.cookies.set("docwiki_lang", "de")  # not a site language: Accept-Language decides
    assert get(client, "/sources/x", **FRENCH).status_code == 200
    assert get(client, "/sources/x", **ENGLISH).status_code == 302


@pytest.mark.parametrize(
    "path",
    [
        "/evidence/src-1/",
        "/evidence/src-1/index.html",
        "/static/app.js",
        "/static/contentIndex.json",
        "/static/docwiki/languages.json",
        "/404",
        "/sources/only-fr",
        "/en/",
        "/en/sources/x",
        "/en/pipeline",
        "/missing",
    ],
)
def test_never_negotiated(client: TestClient, path: str) -> None:
    client.cookies.set("docwiki_lang", "en")
    response = get(client, path, **ENGLISH)
    assert response.status_code in (200, 404)
    assert "location" not in response.headers


def test_page_without_twin_is_canonical_html(client: TestClient) -> None:
    response = get(client, "/sources/only-fr", **ENGLISH)
    assert response.status_code == 200 and response.headers["vary"] == "Accept-Language, Cookie"
    assert "vary" not in get(client, "/static/app.js", **ENGLISH).headers
    assert "vary" not in get(client, "/en/sources/x", **ENGLISH).headers


def test_api_routes_are_not_negotiated(client: TestClient) -> None:
    for path in ("/api/status", "/api/ask/status", "/healthz", "/livez"):
        response = get(client, path, **ENGLISH)
        assert response.status_code in (200, 503), path
        assert "location" not in response.headers and "vary" not in response.headers


@pytest.mark.parametrize("dest", ["empty", "script", "iframe"])
def test_fetches_are_never_redirected(client: TestClient, dest: str) -> None:
    response = get(client, "/sources/x", **ENGLISH, **{"sec-fetch-dest": dest})
    assert response.status_code == 200
    assert response.headers["vary"] == "Accept-Language, Cookie"
    navigation = get(client, "/sources/x", **ENGLISH, **{"sec-fetch-dest": "document"})
    assert navigation.status_code == 302


@pytest.mark.parametrize(
    ("path", "location"),
    [
        ("/how-it-works", "/pipeline"),
        ("/how-it-works/?x=1", "/pipeline?x=1"),
        ("/en/how-it-works", "/en/pipeline"),
        ("/en/how-it-works/?x=1", "/en/pipeline?x=1"),
    ],
)
def test_aliases_in_both_languages(client: TestClient, path: str, location: str) -> None:
    response = get(client, path, **FRENCH)
    assert response.status_code == 308 and response.headers["location"] == location
    assert get(client, "/EN/how-it-works").status_code == 404
    assert get(client, "/eng/how-it-works").status_code == 404


@pytest.mark.parametrize(
    "languages_json",
    [
        None,
        {"schema": 1, "canonical": "en", "languages": ["en"]},
        {"schema": 1, "canonical": "fr", "languages": ["fr", "EN"]},
        {"schema": 1, "canonical": "en", "languages": ["fr", "en"]},
        {"schema": 2, "canonical": "fr", "languages": ["fr", "en"]},
        {"schema": 1, "languages": "fr,en"},
        {"schema": 1, "languages": ["fr", "fr"]},
        "not json",
    ],
)
def test_sites_without_a_valid_mirror_never_redirect(
    tmp_path: Path, languages_json: object
) -> None:
    root = build_site(tmp_path / "site", languages=None)
    if languages_json is not None:
        target = root / "static" / "docwiki" / "languages.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        text = languages_json if isinstance(languages_json, str) else json.dumps(languages_json)
        target.write_text(text, encoding="utf-8")
    with TestClient(create_app(site_dir=root)) as client:
        client.cookies.set("docwiki_lang", "en")
        for path in ("/", "/sources/x", "/pipeline"):
            response = get(client, path, **ENGLISH)
            assert response.status_code == 200, path
            assert "vary" not in response.headers
        assert get(client, "/en/how-it-works").headers["location"] == "/en/pipeline"
