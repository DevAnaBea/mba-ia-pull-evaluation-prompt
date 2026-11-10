"""Pull the challenge seed prompt from LangSmith Prompt Hub."""

import sys
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langsmith import Client

from utils import check_env_vars, configure_console_encoding, print_section_header, save_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
PROMPT_KEY = "bug_to_user_story_v1"
OUTPUT_PATH = PROJECT_ROOT / "prompts" / f"{PROMPT_KEY}.yml"

load_dotenv(PROJECT_ROOT / ".env", override=True)


def _message_template(message: Any) -> tuple[str, str]:
    """Return a message role and template, rejecting unsupported message types."""
    prompt = getattr(message, "prompt", None)
    template = getattr(prompt, "template", None)
    if template is None:
        template = getattr(message, "template", None)

    message_type = getattr(message, "type", None)
    class_name = type(message).__name__.lower()
    if message_type == "system" or "systemmessage" in class_name:
        role = "system"
    elif message_type in {"human", "user"} or "humanmessage" in class_name:
        role = "user"
    else:
        raise ValueError(f"Tipo de mensagem do prompt não suportado: {type(message).__name__}")

    if not isinstance(template, str):
        raise ValueError(f"Não foi possível extrair o template da mensagem {role}.")
    return role, template


def prompt_to_dict(prompt: Any) -> dict[str, Any]:
    """Convert the pulled LangChain prompt into this repository's YAML format."""
    system_prompt = ""
    user_prompt = ""

    for message in prompt.messages:
        role, template = _message_template(message)
        if role == "system":
            system_prompt = template
        elif role == "user":
            user_prompt = template

    if not system_prompt or not user_prompt:
        raise ValueError("O prompt semente precisa conter mensagens System e Human/User.")

    return {
        "description": "Prompt para converter relatos de bugs em User Stories",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "input_variables": list(prompt.input_variables),
        "version": "v1",
        "source": SOURCE_PROMPT,
        "pulled_at": date.today().isoformat(),
        "tags": ["bug-analysis", "user-story", "product-management"],
    }


def pull_prompts_from_langsmith() -> bool:
    """Pull and save the seed prompt locally."""
    client = Client()
    print(f"Puxando prompt: {SOURCE_PROMPT}")
    prompt = client.pull_prompt(
        SOURCE_PROMPT,
        dangerously_pull_public_prompt=True,
    )
    prompt_data = prompt_to_dict(prompt)

    if not save_yaml({PROMPT_KEY: prompt_data}, str(OUTPUT_PATH)):
        return False

    print(
        f"   ✓ Prompt salvo em {OUTPUT_PATH.relative_to(PROJECT_ROOT)} "
        f"(variáveis: {', '.join(prompt.input_variables)})"
    )
    return True


def main() -> int:
    configure_console_encoding()
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")
    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        return 0 if pull_prompts_from_langsmith() else 1
    except Exception as exc:
        print(f"❌ Erro ao fazer pull de '{SOURCE_PROMPT}': {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
