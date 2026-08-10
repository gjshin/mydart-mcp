import json
import os

import pytest

from mydart_mcp import selftest


@pytest.fixture
def capture_steps(monkeypatch):
    """STEPS를 통째로 갈아끼워 실행기 동작만 본다."""

    def use(*steps):
        monkeypatch.setattr(selftest, "STEPS", list(steps))

    return use


def test_reports_all_passing(capture_steps, capsys):
    capture_steps(("A", lambda s: "좋음"), ("B", lambda s: "좋음"))
    assert selftest.run() == 0
    out = capsys.readouterr().out
    assert "통과 2 · 건너뜀 0 · 실패 0" in out
    assert "자주 보는 원인" not in out


def test_keeps_going_after_a_failure(capture_steps, capsys):
    def boom(state):
        raise selftest.Failure("망가짐")

    capture_steps(("A", boom), ("B", lambda s: "그래도 실행됨"))
    assert selftest.run() == 1
    out = capsys.readouterr().out
    assert "그래도 실행됨" in out  # 실패 후에도 다음 단계가 돈다
    assert "통과 1 · 건너뜀 0 · 실패 1" in out
    assert "자주 보는 원인" in out


def test_fatal_failure_aborts_the_rest(capture_steps, capsys):
    def fatal(state):
        raise selftest.Failure("키 없음", fatal=True)

    capture_steps(("A", fatal), ("B", lambda s: "여긴 안 와야 함"))
    assert selftest.run() == 1
    out = capsys.readouterr().out
    assert "여긴 안 와야 함" not in out
    assert "앞 단계 실패로 건너뜀" in out
    assert "통과 0 · 건너뜀 1 · 실패 1" in out


def test_skip_is_not_a_failure(capture_steps, capsys):
    def skip(state):
        raise selftest.Skip("확인할 게 없음")

    capture_steps(("A", skip), ("B", lambda s: "계속됨"))
    assert selftest.run() == 0  # 건너뜀은 종료코드에 영향을 주지 않는다
    assert "통과 1 · 건너뜀 1 · 실패 0" in capsys.readouterr().out


def test_unexpected_exception_is_caught_and_named(capture_steps, capsys):
    def kaboom(state):
        raise ConnectionError("프록시 차단")

    capture_steps(("A", kaboom))
    assert selftest.run() == 1
    assert "ConnectionError: 프록시 차단" in capsys.readouterr().out


def test_rcept_no_is_passed_into_state(capture_steps, capsys):
    capture_steps(("A", lambda s: f"받은 값 {s['rcept_no']}"))
    selftest.run(rcept_no="20240315000123")
    assert "받은 값 20240315000123" in capsys.readouterr().out


def test_api_key_check_never_prints_the_key(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "abcdef0123456789" * 2)
    detail = selftest.check_api_key({})
    assert detail == "32자 설정됨 (환경변수)"
    assert "abcdef" not in detail


def test_api_key_check_is_fatal_when_missing(monkeypatch):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    with pytest.raises(selftest.Failure) as caught:
        selftest.check_api_key({})
    assert caught.value.fatal is True


def test_attachment_steps_skip_without_a_target():
    with pytest.raises(selftest.Skip):
        selftest.check_read_attachment({})
    with pytest.raises(selftest.Skip):
        selftest.check_financials({})


def _write_config(tmp_path, monkeypatch, payload):
    path = tmp_path / "claude_desktop_config.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(selftest, "claude_config_paths", lambda: [path])
    return path


def test_api_key_prefers_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "from-env")
    _write_config(tmp_path, monkeypatch, {"mcpServers": {"mydart": {"env": {"DART_API_KEY": "from-file"}}}})
    assert selftest.check_api_key({}) == "8자 설정됨 (환경변수)"


def test_api_key_falls_back_to_the_claude_config(tmp_path, monkeypatch):
    """설치 후 키는 Claude 설정에만 있고 셸에는 없다. 그걸 '키 없음'으로 보고하면
    멀쩡한 설치를 의심하게 된다."""
    monkeypatch.delenv("DART_API_KEY", raising=False)
    _write_config(tmp_path, monkeypatch, {"mcpServers": {"mydart": {"env": {"DART_API_KEY": "0123456789"}}}})

    detail = selftest.check_api_key({})

    assert "Claude 설정에서 읽음" in detail
    assert "0123456789" not in detail  # 키 자체는 화면에 찍지 않는다
    assert os.environ["DART_API_KEY"] == "0123456789"  # 이후 단계가 쓸 수 있어야 한다


def test_api_key_ignores_a_config_without_the_key(tmp_path, monkeypatch):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    _write_config(tmp_path, monkeypatch, {"preferences": {"sidebarMode": "epitaxy"}})
    with pytest.raises(selftest.Failure) as caught:
        selftest.check_api_key({})
    assert caught.value.fatal is True


def test_api_key_survives_a_broken_config(tmp_path, monkeypatch):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    path = tmp_path / "claude_desktop_config.json"
    path.write_text("{ 망가진 JSON", encoding="utf-8")
    monkeypatch.setattr(selftest, "claude_config_paths", lambda: [path, tmp_path / "없는파일.json"])
    with pytest.raises(selftest.Failure):
        selftest.check_api_key({})
