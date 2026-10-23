"""End to end on the real golden set and corpus (local extraction, fake model, no network)."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from evals.corpus import CorpusContext, load_corpus
from evals.metrics import aggregate, is_abstention, recall_of, score_answer
from evals.questions import QuestionSet, load_questions
from evals.records import Answer, Citation
from evals.systems import BaselineRagSystem

from docwiki.contracts import parse_locator_key
from docwiki.llm import FakeLlmClient, LlmRequest
from evals import runner, systems


@pytest.fixture(scope="module")
def golden(repo_root: Path) -> QuestionSet:
    return load_questions(repo_root / "evals" / "golden" / "dev.jsonl")


@pytest.fixture(scope="module")
def real_corpus(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> CorpusContext:
    cache = tmp_path_factory.mktemp("extract-cache")
    return asyncio.run(load_corpus(repo_root / "samples" / "corpus", cache_dir=cache))


def _overall(records: list[dict[str, Any]]) -> dict[str, Any]:
    return aggregate(records)["overall"]


def _score(golden: QuestionSet, corpus: CorpusContext, make: Any) -> dict[str, Any]:
    records = []
    for question in golden.questions:
        body, citations = make(question)
        result = Answer(
            text=body,
            body=body,
            citations=citations,
            abstained=is_abstention(body, cited=bool(citations)),
        )
        score = score_answer(question, result, corpus)
        records.append({"id": question.id, "category": question.category, "metrics": score.metrics})
    return _overall(records)


def test_reference_answers_score_full_marks(
    golden: QuestionSet, real_corpus: CorpusContext
) -> None:
    """The expected answer with the required citations passes every deterministic metric: the
    metrics agree with the sealed golden set and its corpus."""

    def oracle(question: Any) -> tuple[str, list[Citation]]:
        citations = [
            Citation(source_path=item.source_path, locator_key=item.locator_key, unit=f"[{index}]")
            for index, item in enumerate(question.required_citations, 1)
        ]
        return question.expected_answer, citations

    overall = _score(golden, real_corpus, oracle)
    for name in (
        "answer_accuracy",
        "must_include_coverage",
        "numeric_exactness",
        "citation_precision",
        "citation_recall",
        "abstention_accuracy",
        "injection_resistance",
        "restricted_exclusion",
    ):
        assert overall[name]["value"] == 1.0, (name, overall[name])
        assert overall[name]["n"] > 0
    assert overall["abstention_accuracy"]["n"] == overall["questions"] == len(golden.questions)


def test_always_abstaining_scores_only_the_abstentions(
    golden: QuestionSet, real_corpus: CorpusContext
) -> None:
    overall = _score(golden, real_corpus, lambda question: ("Not found in the wiki.", []))
    abstain = sum(1 for question in golden.questions if question.abstain)
    assert overall["abstention_accuracy"]["passed"] == abstain
    assert overall["answer_accuracy"]["passed"] == abstain
    assert overall["citation_recall"]["value"] == 0.0
    assert overall["citation_precision"]["n"] == 0


def _shift(key: str) -> str:
    """A locator of the same source next to ``key`` (never overlapping it)."""
    if key == "*":
        return "img-b99"
    parts = parse_locator_key(key)
    updates: dict[str, Any] = {}
    for name in ("page", "paragraph", "slide", "region"):
        if getattr(parts, name) is not None:
            updates[name] = getattr(parts, name) + 1
    for start, end in (("row_start", "row_end"), ("line_start", "line_end")):
        low, high = getattr(parts, start), getattr(parts, end)
        if low is not None and high is not None:
            updates[start], updates[end] = low + (high - low) + 10, high + (high - low) + 10
    if parts.kind == "vtt-cue":
        updates["cue_start"] = "00:00:00"
    return parts.model_copy(update=updates).key


def test_neighbouring_locators_lose_recall(golden: QuestionSet, real_corpus: CorpusContext) -> None:
    def shifted(question: Any) -> tuple[str, list[Citation]]:
        citations = [
            Citation(source_path=item.source_path, locator_key=_shift(item.locator_key))
            for item in question.required_citations
        ]
        return question.expected_answer, citations

    overall = _score(golden, real_corpus, shifted)
    assert overall["citation_recall"]["value"] < 0.1  # only the image ("*" = any region) remains


def test_bm25_retrieval_finds_most_required_evidence(
    golden: QuestionSet, real_corpus: CorpusContext
) -> None:
    rag = BaselineRagSystem(
        docs=real_corpus.docs,
        files=real_corpus.manifest.select("full", "public"),
        llm=FakeLlmClient({}),
    )
    rag.build_index()
    recalls = []
    for question in golden.questions:
        citations = [
            Citation(source_path=chunk.path, locator_key=key)
            for chunk, _ in rag.retrieve(question.question)
            for key in chunk.keys
        ]
        value = recall_of(question, citations, real_corpus)
        if value is not None:
            recalls.append(value)
    assert sum(recalls) / len(recalls) > 0.5
    # Since slice F, restricted documents sit in their chantier's folders (ADR 0011).
    restricted = {
        entry.path
        for entry in real_corpus.manifest.documents()
        if entry.sensitivity == "restricted"
    }
    assert restricted and not any(chunk.path in restricted for chunk in rag.chunks)


def test_cli_end_to_end_with_a_fake_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    golden: QuestionSet,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = {question.question: question.expected_answer for question in golden.questions}

    def handler(request: LlmRequest) -> dict[str, Any]:
        asked = request.text.split("Question: ", 1)[1].split("\n", 1)[0]
        return {"answer": expected[asked], "citations": [{"chunk_id": "c1"}, {"chunk_id": "c2"}]}

    monkeypatch.setattr(
        systems, "default_llm_factory", lambda: FakeLlmClient({"eval_baseline_rag": handler})
    )
    code = runner.main(
        [
            "--system",
            "baseline-rag",
            "--questions",
            str(runner.REPO_ROOT / "evals" / "golden" / "dev.jsonl"),
            "--limit",
            "3",
            "--out",
            str(tmp_path / "out"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == 0
    path = next((tmp_path / "out").glob("*-baseline-rag-dev-limit3.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["questions_file"]["file"] == "evals/golden/dev.jsonl"
    assert data["questions_file"]["seal"]["matches"] is True
    assert [record["id"] for record in data["questions"]] == ["q001", "q002", "q003"]
    assert all(record["error"] is None for record in data["questions"])
    assert data["questions"][0]["metrics"]["answer_accuracy"] == 1.0
    assert "retrieval_recall" in data["questions"][0]["metrics"]
    assert data["config"]["system"]["top_k"] == 8 and data["config"]["scope"] == "full"
    assert data["versions"]["system"]["prompt_version"] == systems.RAG_PROMPT_VERSION
    assert data["versions"]["extraction"].startswith("local-")
    assert data["cost"]["input_tokens"] > 0
    total = len(golden.questions)
    assert f"baseline-rag · dev · 3/{total} questions" in capsys.readouterr().out


def test_cli_long_context_baseline_reads_the_public_documents_of_full(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    golden: QuestionSet,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = {question.question: question.expected_answer for question in golden.questions}
    seen: list[str] = []

    def handler(request: LlmRequest) -> dict[str, Any]:
        seen.append(request.text)
        asked = request.text.rsplit("Question: ", 1)[1].split("\n", 1)[0]
        return {"answer": expected[asked], "citations": [{"chunk_id": "S01:p0001"}]}

    monkeypatch.setattr(
        systems,
        "default_llm_factory",
        lambda: FakeLlmClient({"eval_baseline_long_context": handler}),
    )
    code = runner.main(
        [
            "--system",
            "baseline-long-context",
            "--questions",
            str(runner.REPO_ROOT / "evals" / "golden" / "dev.jsonl"),
            "--limit",
            "2",
            "--out",
            str(tmp_path / "out"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == 0, capsys.readouterr().err
    data = json.loads(
        next((tmp_path / "out").glob("*-baseline-long-context-dev-limit2.json")).read_text(
            encoding="utf-8"
        )
    )
    assert data["status"] == "ok" and data["config"]["scope"] == "full"
    assert data["config"]["system"]["documents"] == 39  # the public documents of full/
    assert data["versions"]["system"]["prompt_version"] == systems.LONG_CONTEXT_PROMPT_VERSION
    context = seen[0]
    for path in (
        "chantiers/moreau/1-marche/works-contract/2026-02-10_contrat-de-travaux-signe.docx",
        "chantiers/moreau/0-commercial/quote/DEV-2026-014_indice-A",
        "entreprise/billing-register/2026-04-10_suivi-de-facturation-clients.xlsx",
    ):
        assert f'source="full/{path}' in context
    assert "etude-de-prix-interne" not in context  # restricted: not a public document
    assert "tableau-de-bord-des-marges" not in context  # restricted as well
    assert "held-back" not in context  # the held-back revision is not in the full scope


def _group_digits(text: str) -> str:
    """French digit grouping (narrow no-break space) and a no-break space before the euro sign."""
    return re.sub(
        r"(?<![\d,])(\d{1,3})(\d{3}),(\d{2}) €",
        lambda match: f"{match[1]}\u202f{match[2]},{match[3]}\u00a0€",
        text,
    )


_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_ENGLISH_DATE = re.compile(rf"\b(\d{{1,2}}) ({'|'.join(_MONTHS)}) (\d{{4}})\b")


def _french_dates(text: str) -> str:
    """``23 February 2026`` as ``23/02/2026``."""
    return _ENGLISH_DATE.sub(
        lambda match: f"{int(match[1]):02d}/{_MONTHS.index(match[2]) + 1:02d}/{match[3]}", text
    )


def _score_rewritten(
    golden: QuestionSet, corpus: CorpusContext, rewrite: Callable[[str], str]
) -> tuple[dict[str, Any], int]:
    """Metrics of the reference answers once ``rewrite`` changed their numbers or dates, and the
    number of answers it changed."""
    changed = 0

    def make(question: Any) -> tuple[str, list[Citation]]:
        nonlocal changed
        body = rewrite(question.expected_answer)
        changed += body != question.expected_answer
        citations = [
            Citation(source_path=item.source_path, locator_key=item.locator_key)
            for item in question.required_citations
        ]
        return body, citations

    return _score(golden, corpus, make), changed


@pytest.mark.parametrize("rewrite", [_group_digits, _french_dates], ids=["amounts", "dates"])
def test_french_formats_still_match_the_golden_items(
    golden: QuestionSet, real_corpus: CorpusContext, rewrite: Callable[[str], str]
) -> None:
    """A model that groups the digits of amounts (47 271,60 €) or writes dates JJ/MM/AAAA is not
    penalised: the items of the golden set match whatever the format."""
    overall, changed = _score_rewritten(golden, real_corpus, rewrite)
    assert changed >= 5
    for name in ("answer_accuracy", "must_include_coverage", "numeric_exactness"):
        assert overall[name]["value"] == 1.0, (name, overall[name])
