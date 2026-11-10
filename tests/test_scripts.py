"""Local unit tests for prompt import, validation, and Gemini configuration."""

import sys
from pathlib import Path
from types import ModuleType

import yaml
from langchain_core.prompts import ChatPromptTemplate

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pull_prompts import PROMPT_KEY, prompt_to_dict
from push_prompts import PROMPT_NAME, build_chat_prompt, validate_prompt
from utils import _supports_sampling_parameters


def load_optimized_prompt() -> dict:
    prompt_file = PROJECT_ROOT / "prompts" / f"{PROMPT_NAME}.yml"
    with prompt_file.open(encoding="utf-8") as file:
        return yaml.safe_load(file)[PROMPT_NAME]


def test_optimized_prompt_validates_and_uses_dataset_input() -> None:
    prompt_data = load_optimized_prompt()
    is_valid, errors = validate_prompt(prompt_data)

    assert is_valid, errors
    assert set(build_chat_prompt(prompt_data).input_variables) == {"bug_report"}


def test_pull_conversion_preserves_system_and_user_templates() -> None:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Instruções"),
            ("human", "Relato: {bug_report}"),
        ]
    )

    result = prompt_to_dict(prompt)

    assert result["system_prompt"] == "Instruções"
    assert result["user_prompt"] == "Relato: {bug_report}"
    assert result["input_variables"] == ["bug_report"]
    assert PROMPT_KEY == "bug_to_user_story_v1"


def test_gemini_36_and_newer_omit_sampling_parameters(monkeypatch) -> None:
    captured: dict = {}

    def fake_chat_model(**kwargs):
        captured.update(kwargs)
        return kwargs

    fake_module = ModuleType("langchain_google_genai")
    fake_module.ChatGoogleGenerativeAI = fake_chat_model
    monkeypatch.setitem(sys.modules, "langchain_google_genai", fake_module)
    monkeypatch.setenv("LLM_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-not-a-real-credential")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.8-flash")

    from utils import get_llm

    get_llm(temperature=0)

    assert captured["model"] == "gemini-3.8-flash"
    assert "temperature" not in captured


def test_older_gemini_models_keep_temperature(monkeypatch) -> None:
    captured: dict = {}

    def fake_chat_model(**kwargs):
        captured.update(kwargs)
        return kwargs

    fake_module = ModuleType("langchain_google_genai")
    fake_module.ChatGoogleGenerativeAI = fake_chat_model
    monkeypatch.setitem(sys.modules, "langchain_google_genai", fake_module)
    monkeypatch.setenv("LLM_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-not-a-real-credential")

    from utils import get_llm

    get_llm(model="gemini-2.5-flash", temperature=0)

    assert captured["model"] == "gemini-2.5-flash"
    assert captured["temperature"] == 0


def test_sampling_parameter_compatibility_boundary() -> None:
    assert _supports_sampling_parameters("gemini-3.5-flash")
    assert not _supports_sampling_parameters("gemini-3.6-flash")
    assert not _supports_sampling_parameters("gemini-3.8-flash")
    assert not _supports_sampling_parameters("gemini-4-carbon")
