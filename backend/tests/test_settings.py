import pytest

from backend.app.services import settings


def test_local_file_loaded_without_loading_other_settings(monkeypatch):
    before = settings.os.environ.get('OTHER_SETTING')
    settings.ENV_FILE.write_text('OTHER_SETTING=TEST_ONLY_OTHER\nDATA_GO_KR_SERVICE_KEY=TEST_ONLY_LOCAL+KEY=\n', encoding='utf-8-sig')
    assert settings.service_key() == 'TEST_ONLY_LOCAL+KEY='
    assert settings.os.environ.get('OTHER_SETTING') == before


def test_process_environment_takes_precedence(monkeypatch):
    settings.ENV_FILE.write_text('DATA_GO_KR_SERVICE_KEY=TEST_ONLY_LOCAL')
    monkeypatch.setenv(settings.KEY_NAME, 'TEST_ONLY_PROCESS')
    assert settings.service_key() == 'TEST_ONLY_PROCESS'


@pytest.mark.parametrize('content', [
    'DATA_GO_KR_SERVICE_KEY=', 'DATA_GO_KR_SERVICE_KEY=EXAMPLE_KEY_NOT_REAL',
    'DATA_GO_KR_SERVICE_KEY=TEST ONLY', 'DATA_GO_KR_SERVICE_KEY="TEST_ONLY',
    'DATA_GO_KR_SERVICE_KEY=TEST_ONLY_A\nDATA_GO_KR_SERVICE_KEY=TEST_ONLY_B',
])
def test_unsafe_or_ambiguous_config_not_used(content):
    settings.ENV_FILE.write_text(content)
    assert settings.service_key() == ''


@pytest.mark.parametrize('quote', ['"', "'"])
def test_quoted_local_key(quote):
    settings.ENV_FILE.write_text(f'export DATA_GO_KR_SERVICE_KEY={quote}TEST_ONLY_KEY={quote}')
    assert settings.service_key() == 'TEST_ONLY_KEY='


def test_absent_file_not_configured():
    assert settings.service_key() == ''
