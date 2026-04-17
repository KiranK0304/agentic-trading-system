"""
LLM client factory — universal provider registry.

Supports: Groq, OpenRouter, Nvidia, Kimi, OpenAI.
All providers use the OpenAI-compatible ChatOpenAI interface.
Just change `provider` in LLMConfig to switch the entire system.
"""

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from pydantic import Field, BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

# ── Provider Registry ──────────────────────────────────────────
# Maps provider name → (base_url, env_var_for_api_key)
PROVIDERS: dict[str, tuple[str, str]] = {
    "groq": (
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
    ),
    "nvidia": (
        "https://integrate.api.nvidia.com/v1",
        "NVIDIA_API_KEY",
    ),
    "kimi": (
        "https://api.moonshot.ai/v1",
        "KIMI_API_KEY",
    ),
    "openai": (
        "https://api.openai.com/v1",
        "OPENAI_API_KEY",
    ),
}


class LLMConfig(BaseModel):
    """All LLM configuration in one place."""
    provider: str = Field(
        default="groq",
        description=f"LLM provider key. Supported: {list(PROVIDERS.keys())}",
    )
    model_name: str = Field(
        default="llama-3.3-70b-versatile",
        description="Model identifier on the provider",
    )
    temperature: float = Field(
        default=0.0,
        description="Sampling temperature (0 = deterministic)",
    )


def build_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """
    Central factory for creating LLM clients.

    Looks up the provider in the PROVIDERS registry, reads
    the correct env var and base URL, and constructs a ChatOpenAI instance.
    """
    if config is None:
        config = LLMConfig()

    if config.provider not in PROVIDERS:
        supported = ", ".join(PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider '{config.provider}'. Supported: {supported}"
        )

    base_url, api_key_env = PROVIDERS[config.provider]
    api_key = os.environ.get(api_key_env)

    if not api_key:
        raise ValueError(
            f"API key not found. Set '{api_key_env}' in your .env file "
            f"for provider '{config.provider}'."
        )

    return ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature,
        openai_api_base=base_url,
        openai_api_key=api_key,
    )


def build_structured_llm(
    schema: type[BaseModel],
    config: LLMConfig | None = None,
    method: str = "function_calling",
) -> BaseChatModel:
    """
    Convenience wrapper: build an LLM and immediately attach
    structured output for the given Pydantic schema.
    """
    llm = build_llm(config)
    return llm.with_structured_output(schema, method=method)