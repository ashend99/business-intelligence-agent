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
