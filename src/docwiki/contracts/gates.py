"""Quality gates (pipeline §7): gate catalogue, violations and gate results."""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Literal, get_args

from pydantic import Field

from docwiki.contracts._base import ContractModel, NonEmptyStr

__all__ = [
    "GATES",
    "GateId",
    "GateResult",
    "GateSpec",
    "Violation",
    "gate_results",
]

GateId = Literal[
    "G01",
    "G02",
    "G03",
    "G04",
    "G05",
    "G06",
    "G07",
    "G08",
    "G09",
    "G10",
    "G11",
    "G12",
    "G13",
    "G14",
    "G15",
    "G16",
    "G17",
]


@dataclass(frozen=True)
class GateSpec:
    gate: str
    name: str
    blocking: bool
    rule: str


GATES: dict[str, GateSpec] = {
    spec.gate: spec
    for spec in (
        GateSpec("G01", "frontmatter", True, "Every page validates against its schema"),
        GateSpec("G02", "links", True, "100 % of internal links and anchors resolve"),
        GateSpec(
            "G03", "citations-present", True, "Every key fact / topic claim has >= 1 citation"
        ),
        GateSpec(
            "G04", "quote-verification", True, ">= 95 % of native-text/table citations verified"
        ),
        GateSpec(
            "G05", "safe-content", True, "No raw HTML, external links or javascript:/data: URLs"
        ),
        GateSpec("G06", "sidecars", True, "Every cited locator has a sidecar"),
        GateSpec("G07", "audience", True, "No content above the build audience"),
        GateSpec(
            "G08", "injection-containment", True, "Canary strings absent from kit, indexes, site"
        ),
        GateSpec("G09", "paths", True, "All paths match the slug rules; no enum/class reprs"),
        GateSpec("G10", "glossary", True, "Non-empty when the domain pack has seeds"),
        GateSpec("G11", "supersession", True, "Superseded sources marked; current claims first"),
        GateSpec("G12", "tags", True, "Tags lower-case and de-duplicated"),
        GateSpec("G13", "orphans", False, "<= 5 % of pages without inbound links"),
        GateSpec("G14", "skills", True, "Skill projections identical and valid"),
        GateSpec("G15", "extraction", False, "<= 10 % sources quarantined"),
        GateSpec(
            "G16",
            "locked-vocabulary",
            True,
            "No wiki page renders a locked trade term with a banned English equivalent",
        ),
        GateSpec(
            "G17",
            "translations",
            False,
            "Every canonical page has its mirror in each other wiki language, translated",
        ),
    )
}
if tuple(GATES) != get_args(GateId):  # pragma: no cover - guards edits of the two lists
    raise RuntimeError("GATES and GateId are out of sync")


class Violation(ContractModel):
    """One problem found in a candidate release. ``path`` is relative to the release root."""

    gate: GateId
    code: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    severity: Literal["error", "warning"] = "error"
    path: str | None = None
    line: int | None = None
    message: NonEmptyStr


class GateResult(ContractModel):
    """Outcome of one gate; written to ``manifest.json`` and ``_meta/quality.md``."""

    gate: GateId
    name: NonEmptyStr
    blocking: bool
    status: Literal["pass", "fail", "warn", "skipped"]
    metric: float | None = None
    threshold: float | None = None
    violations: Annotated[int, Field(ge=0)] = 0
    details: list[Violation] = []
    message: str = ""

    @property
    def blocks_publish(self) -> bool:
        return self.blocking and self.status == "fail"


def gate_results(
    violations: Iterable[Violation],
    *,
    skipped: Iterable[str] = (),
    metrics: dict[str, tuple[float | None, float | None]] | None = None,
    max_details: int = 20,
) -> list[GateResult]:
    """Fold violations into one result per gate (G01–G17).

    Errors fail blocking gates and warn non-blocking ones; warnings only ever warn. Gates listed
    in ``skipped`` (evaluated elsewhere or not applicable) are reported as ``skipped``.
    """
    grouped: dict[str, list[Violation]] = {gate: [] for gate in GATES}
    for violation in violations:
        grouped[violation.gate].append(violation)
    skip = set(skipped)
    results: list[GateResult] = []
    for gate, spec in GATES.items():
        found = grouped[gate]
        metric, threshold = (metrics or {}).get(gate, (None, None))
        if gate in skip and not found:
            status = "skipped"
        elif any(v.severity == "error" for v in found):
            status = "fail" if spec.blocking else "warn"
        elif found:
            status = "warn"
        else:
            status = "pass"
        results.append(
            GateResult(
                gate=gate,  # type: ignore[arg-type]
                name=spec.name,
                blocking=spec.blocking,
                status=status,
                metric=metric,
                threshold=threshold,
                violations=len(found),
                details=found[:max_details],
                message=spec.rule,
            )
        )
    return results
