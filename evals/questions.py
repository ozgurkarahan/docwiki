"""Golden questions (docs/spec/domain-and-corpus.md §5): model and loader."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

__all__ = [
    "GoldenQuestion",
    "QuestionSet",
    "QuestionSetError",
    "RequiredCitation",
    "load_questions",
]


class QuestionSetError(ValueError):
    """The questions file is missing or malformed (the message never quotes question text)."""


class RequiredCitation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    source_path: str
    locator_key: str


class GoldenQuestion(BaseModel):
    """One line of ``evals/golden/dev.jsonl`` (or of the private holdout)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(min_length=1)
    split: str = "dev"
    category: str = Field(min_length=1)
    question: str = Field(min_length=1)
    lang: str = "en"
    expected_answer: str = ""
    must_include: list[str] = Field(default_factory=list)
    required_citations: list[RequiredCitation] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    abstain: bool = False
    notes: str = ""


@dataclass(frozen=True)
class QuestionSet:
    questions: tuple[GoldenQuestion, ...]
    sha256: str
    name: str
    total: int
    """Questions in the file (``len(questions)`` is smaller when ``--limit`` was applied)."""

    @property
    def complete(self) -> bool:
        return len(self.questions) == self.total


def load_questions(path: Path, *, limit: int | None = None) -> QuestionSet:
    """Read a JSONL golden set; ``limit`` keeps the first N questions."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise QuestionSetError(
            f"cannot read the questions file {Path(path).name}: {exc.strerror}"
        ) from None
    questions: list[GoldenQuestion] = []
    for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            questions.append(GoldenQuestion.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError) as exc:
            # Never chain the error: validation messages quote the (possibly private) input.
            reason = type(exc).__name__
            raise QuestionSetError(
                f"line {number} of {Path(path).name} is invalid ({reason})"
            ) from None
    ids = [question.id for question in questions]
    duplicates = sorted({qid for qid in ids if ids.count(qid) > 1})
    if duplicates:
        raise QuestionSetError(f"duplicate question ids: {', '.join(duplicates)}")
    if not questions:
        raise QuestionSetError(f"{Path(path).name} has no questions")
    if limit is not None and limit < 1:
        raise QuestionSetError("--limit must be >= 1")
    kept = questions[:limit] if limit else questions
    return QuestionSet(
        questions=tuple(kept),
        sha256=hashlib.sha256(raw).hexdigest(),
        name=Path(path).name,
        total=len(questions),
    )
