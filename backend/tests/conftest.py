import pytest

from backend.app.services import settings


@pytest.fixture(autouse=True)
def isolated_portal_credentials(monkeypatch, tmp_path):
    # Running tests must not read a developer's actual local credential file.
    monkeypatch.setattr(settings, "ENV_FILE", tmp_path / ".env")
    monkeypatch.delenv(settings.KEY_NAME, raising=False)
