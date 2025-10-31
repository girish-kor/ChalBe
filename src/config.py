import os
import logging
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv, set_key

HOME_DIR = Path.home()
CHAL_DIR = HOME_DIR / ".chalbe"
ENV_FILE = CHAL_DIR / ".env"
CHAL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("chalbe")

PROVIDERS = {
    "openai": {
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
    },
    "google": {
        "models": ["gemini-1.5-pro", "gemini-1.5-flash"],
    },
    "mistral": {
        "models": ["mistral-medium", "mistral-large"],
    },
    "cohere": {
        "models": ["command-r", "command-r-plus"],
    },
    "huggingface": {
        "models": ["mistralai/Mistral-7B-Instruct-v0.2", "meta-llama/Llama-3-8B"],
    },
    "replicate": {
        "models": ["meta/llama-2-70b-chat", "mistralai/mixtral-8x7b"],
    },
    "together": {
        "models": ["meta-llama/Llama-3-70B", "mistralai/Mixtral-8x22B"],
    },
    "bedrock": {
        "models": ["anthropic.claude-v2", "ai21.j2-ultra"],
    },
}

def save_env(provider: str, model: str, api_key: str) -> None:
    if not CHAL_DIR.exists():
        CHAL_DIR.mkdir(parents=True)
    if not ENV_FILE.exists():
        ENV_FILE.touch()
    set_key(str(ENV_FILE), "PROVIDER", provider)
    set_key(str(ENV_FILE), "MODEL", model)
    set_key(str(ENV_FILE), "API_KEY", api_key)
    logger.info("API key saved to %s", ENV_FILE)


def load_env() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not ENV_FILE.exists():
        return None, None, None
    load_dotenv(ENV_FILE)
    return os.getenv("PROVIDER"), os.getenv("MODEL"), os.getenv("API_KEY")
