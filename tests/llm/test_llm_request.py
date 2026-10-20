from __future__ import annotations

import hashlib
import json

import pytest
from llm_testkit import PNG_BYTES
from pydantic import BaseModel

from docwiki.llm import ImagePart, LlmRequest, TextPart, to_strict_json_schema
from docwiki.llm.hashing import canonical_json


class Answer(BaseModel):
    answer: str


class OtherAnswer(BaseModel):
    answer: str
    score: int


def build(**overrides: object) -> LlmRequest:
    arguments: dict[str, object] = {
        "tier": "fast",
        "system": "You classify documents.",
        "user": "Site meeting report",
        "output": Answer,
        "schema_name": "classify",
        "prompt_version": "classify-v1",
        "max_output_tokens": 200,
        "metadata": None,
    }
    arguments.update(overrides)
    return LlmRequest.build(**arguments)  # type: ignore[arg-type]


def test_request_hash_is_sha256_of_the_canonical_payload() -> None:
    request = build()
    payload = {
        "tier": "fast",
        "system": "You classify documents.",
        "user": [{"type": "text", "text": "Site meeting report"}],
        "schema_name": "classify",
        "output_schema": to_strict_json_schema(Answer),
        "prompt_version": "classify-v1",
    }
    assert request.hash_payload() == payload
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    assert request.request_hash == hashlib.sha256(encoded).hexdigest()


def test_request_hash_has_a_stable_golden_value() -> None:
    # Pinned so that a change of hashing scheme (which invalidates every fixture) is deliberate.
    assert canonical_json(to_strict_json_schema(Answer)) == (
        '{"additionalProperties":false,"properties":{"answer":{"type":"string"}},'
        '"required":["answer"],"type":"object"}'
    )
    assert build().request_hash == (
        "33e02395ea4e4dc592e40faa7bf399c50389b64679ffd229f7a159ac91434e41"
    )


def test_string_user_equals_single_text_part() -> None:
    assert build().request_hash == build(user=[TextPart("Site meeting report")]).request_hash


def test_line_endings_do_not_change_the_hash() -> None:
    unix = build(system="line one\nline two", user="a\nb")
    windows = build(system="line one\r\nline two", user="a\r\nb")
    assert unix.request_hash == windows.request_hash


@pytest.mark.parametrize(
    "change",
    [
        {"tier": "smart"},
        {"system": "Another system prompt."},
        {"user": "Another document"},
        {"schema_name": "classify2"},
        {"prompt_version": "classify-v2"},
        {"output": OtherAnswer},
    ],
)
def test_each_hashed_field_changes_the_hash(change: dict[str, object]) -> None:
    assert build(**change).request_hash != build().request_hash


@pytest.mark.parametrize("change", [{"max_output_tokens": 999}, {"metadata": {"stage": "x"}}])
def test_budget_and_metadata_are_not_hashed(change: dict[str, object]) -> None:
    assert build(**change).request_hash == build().request_hash


def test_images_are_hashed_by_digest_not_bytes() -> None:
    image = ImagePart.png(PNG_BYTES)
    request = build(user=[TextPart("Describe the figure."), image])
    image_entry = request.hash_payload()["user"][1]
    assert image_entry == {
        "type": "image",
        "media_type": "image/png",
        "detail": "auto",
        "sha256": hashlib.sha256(PNG_BYTES).hexdigest(),
    }
    other = ImagePart.png(PNG_BYTES + b"\x01")
    assert build(user=[TextPart("Describe the figure."), other]).request_hash != (
        request.request_hash
    )
    assert image.data_url().startswith("data:image/png;base64,iVBORw0KGgo")


def test_image_validation() -> None:
    with pytest.raises(ValueError, match="does not look like image/png"):
        ImagePart.png(b"GIF89a....")
    with pytest.raises(ValueError, match="Unsupported image media type"):
        ImagePart(data=PNG_BYTES, media_type="image/tiff")
    assert ImagePart(data=b"\xff\xd8\xff\xe0rest", media_type="image/jpeg").media_type == (
        "image/jpeg"
    )


def test_estimated_input_tokens() -> None:
    request = build(system="x" * 40, user=[TextPart("y" * 41), ImagePart.png(PNG_BYTES)])
    assert request.estimated_input_tokens() == 21 + 1000
    low = build(system="", user=[ImagePart.png(PNG_BYTES, detail="low")])
    assert low.estimated_input_tokens() == 85


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"tier": "medium"}, ValueError),
        ({"schema_name": "has space"}, ValueError),
        ({"schema_name": "x" * 65}, ValueError),
        ({"prompt_version": " "}, ValueError),
        ({"max_output_tokens": 0}, ValueError),
        ({"max_output_tokens": True}, TypeError),
        ({"user": []}, ValueError),
        ({"user": [b"raw"]}, TypeError),
        ({"output": dict}, TypeError),
        ({"metadata": {"stage": object()}}, TypeError),
        ({"metadata": {"": "x"}}, ValueError),
    ],
)
def test_invalid_requests_are_rejected(change: dict[str, object], error: type[Exception]) -> None:
    with pytest.raises(error):
        build(**change)
