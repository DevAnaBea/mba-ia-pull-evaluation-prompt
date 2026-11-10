"""Validate and publish the optimized prompt to LangSmith Prompt Hub."""

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

from utils import check_env_vars, configure_console_encoding, load_yaml, print_section_header

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_NAME = "bug_to_user_story_v2"
PROMPT_PATH = PROJECT_ROOT / "prompts" / f"{PROMPT_NAME}.yml"
REQUIRED_INPUT_VARIABLES = {"bug_report"}

load_dotenv(PROJECT_ROOT / ".env", override=True)


def build_chat_prompt(prompt_data: dict[str, Any]) -> ChatPromptTemplate:
    """Build the LangChain chat prompt from the YAML messages."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", prompt_data["system_prompt"]),
            ("human", prompt_data["user_prompt"]),
        ]
    )


def build_readme(prompt_data: dict[str, Any]) -> str:
    """Build the description shown on the published Hub prompt page."""
    techniques = "\n".join(
        f"- {technique}" for technique in prompt_data.get("techniques_applied", [])
    )
    return (
        f"# {PROMPT_NAME}\n\n"
        f"{prompt_data.get('description', '')}\n\n"
        f"**Versão:** {prompt_data.get('version', '')}\n\n"
        f"## Técnicas aplicadas\n\n{techniques}\n\n"
        "## Entrada\n\n- `bug_report`: relato de bug em texto livre\n"
    )


def validate_prompt(prompt_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate prompt content and ensure it accepts exactly the dataset input."""
    errors: list[str] = []
    if not isinstance(prompt_data, dict):
        return False, ["O conteúdo do prompt deve ser um objeto YAML."]

    for field in ("description", "version", "system_prompt", "user_prompt"):
        value = prompt_data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Campo obrigatório ausente ou vazio: {field}")

    techniques = prompt_data.get("techniques_applied")
    if not isinstance(techniques, list) or not all(
        isinstance(technique, str) and technique.strip() for technique in techniques
    ):
        errors.append("techniques_applied deve ser uma lista de textos não vazios.")
        techniques = []
    elif len(techniques) < 2:
        errors.append("São necessárias pelo menos duas técnicas.")

    if not any("few-shot" in technique.lower() for technique in techniques):
        errors.append("Few-shot Learning deve constar em techniques_applied.")

    tags = prompt_data.get("tags", [])
    if not isinstance(tags, list) or not all(
        isinstance(tag, str) and tag.strip() for tag in tags
    ):
        errors.append("tags deve ser uma lista de textos não vazios.")

    system_prompt = prompt_data.get("system_prompt")
    user_prompt = prompt_data.get("user_prompt")
    if isinstance(system_prompt, str) and isinstance(user_prompt, str):
        full_text = f"{system_prompt}\n{user_prompt}"
        if "[TODO]" in full_text or "TODO" in full_text:
            errors.append("O prompt ainda contém TODO.")
        if "{bug_report}" not in user_prompt:
            errors.append("user_prompt deve conter a variável {bug_report}.")

    if errors:
        return False, errors

    try:
        input_variables = set(build_chat_prompt(prompt_data).input_variables)
    except Exception as exc:
        return False, [f"Template inválido: {exc}"]

    if input_variables != REQUIRED_INPUT_VARIABLES:
        errors.append(
            "As variáveis do template devem ser exatamente "
            f"{sorted(REQUIRED_INPUT_VARIABLES)}; encontradas: {sorted(input_variables)}. "
            "Escape chaves literais como {{ e }}."
        )

    return not errors, errors


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict[str, Any]) -> bool:
    """Publish a validated prompt publicly and report its Hub URL."""
    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
    if not username:
        print("❌ USERNAME_LANGSMITH_HUB não está configurado.")
        return False

    prompt_identifier = f"{username}/{prompt_name}"
    techniques = prompt_data.get("techniques_applied", [])
    tags = list(
        dict.fromkeys(
            [
                *prompt_data.get("tags", []),
                *(technique.lower().replace(" ", "-") for technique in techniques),
                prompt_data.get("version", ""),
            ]
        )
    )
    tags = [tag for tag in tags if isinstance(tag, str) and tag]

    try:
        print(f"Fazendo push público: {prompt_identifier}")
        url = Client().push_prompt(
            prompt_identifier,
            object=build_chat_prompt(prompt_data),
            is_public=True,
            description=prompt_data["description"],
            readme=build_readme(prompt_data),
            tags=tags,
            commit_description=prompt_data.get(
                "changelog", f"Versão {prompt_data.get('version', '')}"
            ),
        )
        print(f"   ✓ Push concluído: {url}")
        return True
    except Exception as exc:
        print(f"❌ Erro ao fazer push de '{prompt_identifier}': {exc}")
        return False


def main() -> int:
    configure_console_encoding()
    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH HUB")
    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_PATH))
    if not isinstance(data, dict) or PROMPT_NAME not in data:
        print(f"❌ Prompt '{PROMPT_NAME}' não encontrado em {PROMPT_PATH}")
        return 1

    prompt_data = data[PROMPT_NAME]
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1

    print("   ✓ Prompt validado")
    return 0 if push_prompt_to_langsmith(PROMPT_NAME, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
