from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient
from studio_testkit import seed_storage

from docwiki.studio.__main__ import main
from docwiki.studio.wiring import build_app, check


def _env(root: Path) -> dict[str, str]:
    return {"DOCWIKI_MODE": "local", "DOCWIKI_WORK_DIR": str(root)}


def test_check_reports_storage_access_without_agents(tmp_path: Path) -> None:
    seed_storage(tmp_path / "store")
    assert check(_env(tmp_path / "store")) == {
        "storage": True,
        "agents": None,
        "queue_readable": False,
        "ok": True,
    }


def test_check_command_prints_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seed_storage(tmp_path / "store")
    for key, value in _env(tmp_path / "store").items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("DOCWIKI_FOUNDRY_PROJECT_ENDPOINT", raising=False)
    assert main(["--check"]) == 0
    assert json.loads(capsys.readouterr().out)["storage"] is True


def test_local_flag_only_on_loopback() -> None:
    with pytest.raises(SystemExit):
        main(["--local", "--host", "0.0.0.0"])


def test_build_app_from_the_environment(tmp_path: Path) -> None:
    seed_storage(tmp_path / "store")
    app = build_app({**_env(tmp_path / "store"), "DOCWIKI_STUDIO_WIKI_URL": "https://w.example"})
    with TestClient(app) as client:
        response = client.get(
            "/api/me",
            headers={"x-ms-client-principal-id": "someone", "x-ms-client-principal-name": "x"},
        )
    # Signed-in requests are refused while no principal is allowed (fail closed).
    assert response.status_code == 403
