"""
tests/config/test_settings.py

Test suite for config/settings.py — focused on the two testable functions:

    _load_yaml(path)
    ├── Valid file        — returns a populated dict
    ├── Empty file        — returns empty dict (not None)
    ├── Missing file      — raises FileNotFoundError with clear message
    └── Nested structure  — nested keys are accessible

    Settings._get_env(key)
    ├── Key present       — returns the value
    ├── Key missing       — raises EnvironmentError with the key name
    └── Key empty string  — raises EnvironmentError
"""

from pathlib import Path

import pytest

from config.settings import Settings, _load_yaml


# ===========================================================================
# _load_yaml()
# ===========================================================================

class TestLoadYaml:

    def test_valid_yaml_returns_dict(self, project_root: Path):
        yaml_path = project_root / "config" / "config.yaml"
        result = _load_yaml(yaml_path)
        assert isinstance(result, dict)

    def test_valid_yaml_is_not_empty(self, project_root: Path):
        yaml_path = project_root / "config" / "config.yaml"
        result = _load_yaml(yaml_path)
        assert len(result) > 0

    def test_valid_yaml_top_level_keys(self, project_root: Path):
        yaml_path = project_root / "config" / "config.yaml"
        result = _load_yaml(yaml_path)
        for key in ("app", "llm", "embeddings", "vectorstore", "ingestion", "retrieval"):
            assert key in result

    def test_nested_values_accessible(self, project_root: Path):
        yaml_path = project_root / "config" / "config.yaml"
        result = _load_yaml(yaml_path)
        assert result["llm"]["model"] == "gpt-4o"
        assert result["ingestion"]["chunk_size"] == 500

    def test_empty_yaml_returns_empty_dict(self, tmp_path: Path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("", encoding="utf-8")
        result = _load_yaml(empty)
        assert result == {}

    def test_missing_file_raises_file_not_found(self, tmp_path: Path):
        missing = tmp_path / "no_such_file.yaml"
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            _load_yaml(missing)

    def test_error_message_contains_path(self, tmp_path: Path):
        missing = tmp_path / "no_such_file.yaml"
        with pytest.raises(FileNotFoundError) as exc_info:
            _load_yaml(missing)
        assert "no_such_file.yaml" in str(exc_info.value)


# ===========================================================================
# Settings._get_env()
# ===========================================================================

class TestGetEnv:

    def test_returns_value_when_key_present(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_KEY", "hello-world")
        result = Settings._get_env("TEST_KEY")
        assert result == "hello-world"

    def test_returns_exact_value(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_KEY", "sk-abc-123")
        assert Settings._get_env("TEST_KEY") == "sk-abc-123"

    def test_raises_when_key_missing(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("TEST_MISSING_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="TEST_MISSING_KEY"):
            Settings._get_env("TEST_MISSING_KEY")

    def test_raises_when_value_is_empty_string(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_EMPTY_KEY", "")
        with pytest.raises(EnvironmentError, match="TEST_EMPTY_KEY"):
            Settings._get_env("TEST_EMPTY_KEY")

    def test_error_message_suggests_env_file(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("TEST_MISSING_KEY", raising=False)
        with pytest.raises(EnvironmentError) as exc_info:
            Settings._get_env("TEST_MISSING_KEY")
        assert ".env" in str(exc_info.value)
