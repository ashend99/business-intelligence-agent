"""Loads the active system prompt from a versioned text file.

The active version is set in config/config.yaml under agent.prompt_version.
Prompt files live in config/prompts/ and are named system_<version>.txt
(e.g. system_v1.txt, system_v2.txt).

To introduce a new prompt:
  1. Copy config/prompts/system_v1.txt → system_v2.txt and edit it.
  2. Change agent.prompt_version: "v2" in config/config.yaml.
  3. No code changes needed.
"""

from pathlib import Path

from config.settings import settings


def get_agent_prompt(agent_name: str, version: str | None = None) -> str:
    """Load and return the system prompt for a named agent.

    Args:
        agent_name: One of orchestrator, rag, analytics, synthesizer, direct_response.
        version: Prompt version string (e.g. "v1"). Defaults to the version
                 configured in settings.agent_prompt_versions for that agent.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    resolved_version = version or settings.agent_prompt_versions.get(agent_name, "v1")
    prompt_file = settings.prompts_dir / f"{agent_name}_{resolved_version}.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_file}\n"
            f"Create config/prompts/{agent_name}_{resolved_version}.txt "
            f"or update agents.{agent_name}.prompt_version in config.yaml."
        )
    return prompt_file.read_text(encoding="utf-8")


def get_system_prompt() -> str:
    """Load and return the active system prompt from disk.

    The file path is derived from settings.prompts_dir and
    settings.prompt_version: <prompts_dir>/system_<version>.txt

    Returns:
        The prompt text as a string.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    prompt_file: Path = settings.prompts_dir / f"system_{settings.prompt_version}.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_file}\n"
            f"Create config/prompts/system_{settings.prompt_version}.txt "
            f"or update agent.prompt_version in config.yaml."
        )
    return prompt_file.read_text(encoding="utf-8")
