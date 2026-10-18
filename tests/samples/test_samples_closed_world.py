"""Closed world: names, e-mail domains, the injection canary and the allowlist."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from samples.generators import allowlist
from samples.generators.closedworld import known_tokens, unknown_names

_EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")


def _corpus_texts(documents: list[dict[str, Any]], extracted) -> dict[str, str]:
    texts = {}
    for entry in documents:
        content = extracted(entry["path"])
        texts[entry["path"]] = "\n".join([content.text(), *content.metadata.values()])
    return texts


def test_allowlist_is_generated_from_the_bible(repo_root: Path, bible: dict[str, Any]) -> None:
    current = (repo_root / "samples/fiction/allowlist.txt").read_text(encoding="utf-8")
    assert current == allowlist.render(bible)
    lines = current.splitlines()
    assert lines == sorted(set(lines), key=lambda line: (line.casefold(), line))
    assert all(line.strip() == line and line for line in lines)
    for line in lines:
        if line.startswith("re:"):
            re.compile(line.removeprefix("re:"))


def test_capitalised_names_are_in_the_closed_world(
    documents: list[dict[str, Any]], extracted, repo_root: Path, bible: dict[str, Any]
) -> None:
    lines = (repo_root / "samples/fiction/allowlist.txt").read_text(encoding="utf-8").splitlines()
    vocabulary = bible["vocabulary"]
    known = known_tokens(lines, [*vocabulary["technology"], *vocabulary["generic"]])
    problems = {}
    for path, text in _corpus_texts(documents, extracted).items():
        unknown = sorted(set(unknown_names(text, known)))
        if unknown:
            problems[path] = unknown
    assert not problems, f"names outside the bible: {problems}"


def test_email_addresses_use_bible_domains(
    documents: list[dict[str, Any]], extracted, corpus_root: Path, bible: dict[str, Any]
) -> None:
    allowed = set(bible["world"]["email_domains"]["domains"])
    texts = _corpus_texts(documents, extracted)
    for entry in documents:
        if entry["format"] == "eml":
            texts[entry["path"] + " (raw)"] = (corpus_root / entry["path"]).read_text("utf-8")
    for path, text in texts.items():
        for domain in _EMAIL.findall(text):
            assert domain in allowed, f"{path}: {domain}"
    assert all(domain.endswith(".example") for domain in allowed)


def test_canary_only_in_the_oem_email(
    documents: list[dict[str, Any]], extracted, bible: dict[str, Any], manifest: dict[str, Any]
) -> None:
    canary = bible["injection"]["canary"]
    assert re.fullmatch(r"CANARY-[0-9A-F]{8}", canary)
    carriers = sorted(path for path, text in _corpus_texts(documents, extracted).items()
                      if canary in text)
    assert carriers == [bible["injection"]["document"]]
    body = " ".join(extracted(bible["injection"]["document"]).text().split())
    assert " ".join(bible["injection"]["sentence"].split()) in body
    copies = [e["path"] for e in manifest["files"] if e["copy_of"] == carriers[0]]
    assert len(copies) == 1


# sha256 of case-folded words that must never appear (a surname the brief excludes and the
# name of a real wind farm). Hashes keep the real names out of the repository.
_BANNED_WORD_HASHES = {
    "c5f975b35c72cfe2da72009c9866a7ce5eafadce57af395c9c1b6c94b383ed2c",
    "84e2cdb7a166d1671bc5e2abc1e78b59777dd1f863d3c5b05d09c2dd088444c2",
}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _banned_words(text: str) -> set[str]:
    return {
        word
        for word in set(_WORD.findall(text.casefold()))
        if hashlib.sha256(word.encode("utf-8")).hexdigest() in _BANNED_WORD_HASHES
    }


def test_banned_names_are_absent(
    documents: list[dict[str, Any]], extracted, repo_root: Path
) -> None:
    for path, text in _corpus_texts(documents, extracted).items():
        assert not _banned_words(text), path
    for folder in ("samples/fiction", "samples/generators", "domains", "evals/golden"):
        for file in (repo_root / folder).rglob("*"):
            if file.is_file() and file.suffix in (".yaml", ".md", ".txt", ".j2", ".py", ".jsonl"):
                assert not _banned_words(file.read_text(encoding="utf-8")), file.name
