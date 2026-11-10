"""Automated validation for the optimized prompt."""

import re
from pathlib import Path

import pytest
import yaml

from src.utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


@pytest.fixture(scope="module")
def prompt() -> dict:
    with PROMPT_FILE.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    assert isinstance(data, dict), "O YAML deve conter um objeto na raiz."
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada."
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt: dict) -> str:
    return prompt.get("system_prompt", "")


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt: dict) -> None:
        assert isinstance(prompt.get("system_prompt"), str)
        assert prompt["system_prompt"].strip()

    def test_prompt_has_role_definition(self, system_prompt: str) -> None:
        assert re.search(r"Você é um Product Manager", system_prompt, re.IGNORECASE)

    def test_prompt_mentions_format(self, system_prompt: str) -> None:
        normalized = system_prompt.lower()
        assert "como um/uma" in normalized
        assert "eu quero" in normalized
        assert "para que" in normalized
        assert "critérios de aceitação" in normalized
        assert all(term in normalized for term in ("dado que", "quando", "então"))

    def test_prompt_has_few_shot_examples(self, system_prompt: str) -> None:
        examples = re.findall(r"(?m)^Exemplo \d+ —", system_prompt)
        assert len(examples) >= 2
        assert system_prompt.count("Relato de bug:") >= len(examples)
        assert system_prompt.count("Resposta:") >= len(examples)

    def test_prompt_no_todos(self, prompt: dict) -> None:
        serialized = yaml.safe_dump(prompt, allow_unicode=True)
        assert "[TODO]" not in serialized
        assert not re.search(r"\bTODO\b", serialized, re.IGNORECASE)

    def test_minimum_techniques(self, prompt: dict) -> None:
        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        assert any("few-shot" in technique.lower() for technique in techniques)

    def test_prompt_structure_is_valid(self, prompt: dict) -> None:
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, errors

    def test_user_prompt_uses_bug_report_variable(self, prompt: dict) -> None:
        assert "{bug_report}" in prompt.get("user_prompt", "")
        assert "{bug_report}" not in prompt["system_prompt"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
