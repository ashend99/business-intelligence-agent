"""Tests for src/agent/prompts.py and src/agent/graph.py."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.prompts import get_system_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_prompt_file(directory: Path, version: str, content: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    f = directory / f"system_{version}.txt"
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# TestGetSystemPrompt
# ---------------------------------------------------------------------------

class TestGetSystemPrompt:
    def test_returns_file_contents(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_system_prompt() returns the exact text from the prompt file."""
        expected = "You are a test assistant.\nBe helpful."
        _write_prompt_file(tmp_path, "v1", expected)

        monkeypatch.setattr("agents.prompts.settings.prompts_dir", tmp_path)
        monkeypatch.setattr("agents.prompts.settings.prompt_version", "v1")

        assert get_system_prompt() == expected

    def test_returns_non_empty_string(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_system_prompt() returns a non-empty string."""
        _write_prompt_file(tmp_path, "v1", "Some prompt text.")
        monkeypatch.setattr("agents.prompts.settings.prompts_dir", tmp_path)
        monkeypatch.setattr("agents.prompts.settings.prompt_version", "v1")

        result = get_system_prompt()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_loads_correct_version(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_system_prompt() loads the version specified in settings."""
        _write_prompt_file(tmp_path, "v1", "Version one.")
        _write_prompt_file(tmp_path, "v2", "Version two.")

        monkeypatch.setattr("agents.prompts.settings.prompts_dir", tmp_path)
        monkeypatch.setattr("agents.prompts.settings.prompt_version", "v2")

        assert get_system_prompt() == "Version two."

    def test_raises_file_not_found_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_system_prompt() raises FileNotFoundError if the prompt file is absent."""
        monkeypatch.setattr("agents.prompts.settings.prompts_dir", tmp_path)
        monkeypatch.setattr("agents.prompts.settings.prompt_version", "v99")

        with pytest.raises(FileNotFoundError, match="system_v99.txt"):
            get_system_prompt()

    def test_error_message_includes_version(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FileNotFoundError message contains the missing version string."""
        monkeypatch.setattr("agents.prompts.settings.prompts_dir", tmp_path)
        monkeypatch.setattr("agents.prompts.settings.prompt_version", "v42")

        with pytest.raises(FileNotFoundError, match="v42"):
            get_system_prompt()


# ---------------------------------------------------------------------------
# TestBuildAgent
# ---------------------------------------------------------------------------

class TestBuildAgent:
    """Tests for build_agent() in src/agent/graph.py.

    We mock ChatOpenAI, build_rag_tool, get_system_prompt, and
    create_react_agent so no real API calls or vector store access occur.
    """

    @pytest.fixture(autouse=True)
    def _patch_dependencies(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Provide a real prompt file so get_system_prompt() doesn't fail
        _write_prompt_file(tmp_path, "v1", "Test prompt.")
        monkeypatch.setattr("agents.prompts.settings.prompts_dir", tmp_path)
        monkeypatch.setattr("agents.prompts.settings.prompt_version", "v1")

        self.mock_llm = MagicMock()
        self.mock_tool = MagicMock()
        self.mock_graph = MagicMock()
        self.mock_graph.invoke = MagicMock(return_value={"messages": []})

        self._patches = [
            patch("agents.graph.ChatOpenAI", return_value=self.mock_llm),
            patch("agents.graph.build_rag_tool", return_value=self.mock_tool),
            patch("agents.graph.create_react_agent", return_value=self.mock_graph),
        ]
        for p in self._patches:
            p.start()

        yield

        for p in self._patches:
            p.stop()

    def test_returns_compiled_graph(self) -> None:
        """build_agent() returns an object with an invoke method."""
        from agents.graph import build_agent

        agent = build_agent("cafe")
        assert hasattr(agent, "invoke")

    def test_builds_rag_tool_with_business_key(self) -> None:
        """build_agent() calls build_rag_tool with the supplied business key."""
        from agents.graph import build_agent
        from agents import graph as graph_module

        build_agent("hotel")
        graph_module.build_rag_tool.assert_called_once_with("hotel")

    def test_create_react_agent_receives_tool(self) -> None:
        """build_agent() passes the RAG tool to create_react_agent."""
        from agents.graph import build_agent
        from agents import graph as graph_module

        build_agent("gems")

        _, kwargs = graph_module.create_react_agent.call_args
        assert self.mock_tool in kwargs.get("tools", [])

    def test_create_react_agent_receives_llm(self) -> None:
        """build_agent() passes the ChatOpenAI instance to create_react_agent."""
        from agents.graph import build_agent
        from agents import graph as graph_module

        build_agent("cafe")

        _, kwargs = graph_module.create_react_agent.call_args
        assert kwargs.get("model") is self.mock_llm

    def test_create_react_agent_receives_prompt(self) -> None:
        """build_agent() passes the system prompt string to create_react_agent."""
        from agents.graph import build_agent
        from agents import graph as graph_module

        build_agent("cafe")

        _, kwargs = graph_module.create_react_agent.call_args
        assert kwargs.get("prompt") == "Test prompt."

    def test_unknown_business_key_raises_key_error(self) -> None:
        """build_agent() propagates KeyError for unrecognised business keys."""
        from agents.graph import build_agent
        from agents import graph as graph_module

        graph_module.build_rag_tool.side_effect = KeyError("unknown_biz")

        with pytest.raises(KeyError):
            build_agent("unknown_biz")
