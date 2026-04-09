"""
LLM client factory — single place to create and configure LLM instances.

Currently supports Groq (via OpenAI-compatible endpoint).
Extend the `build_llm` function to add new providers.
"""

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from pydantic import Field, BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class LLMConfig(BaseModel):
    """All LLM configuration in one place."""
    provider: str = Field(
        default="openai",
        description="LLM provider key: 'openai' routes to Groq's OpenAI-compatible API",
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

    Returns a plain ChatModel — call .with_structured_output(Schema)
    yourself when you need structured output for a specific node.
    """
    if config is None:
        config = LLMConfig()

    if config.provider == "openai":
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            openai_api_base=os.environ.get("base_url"),
            openai_api_key=os.environ.get("GROQ_API_KEY"),
        )

    # ── add more providers here ──
    # if config.provider == "anthropic": ...
    # if config.provider == "gemini": ...

    raise ValueError(f"Unsupported provider: {config.provider}")


def build_structured_llm(
    schema: type[BaseModel],
    config: LLMConfig | None = None,
    method: str = "function_calling",
) -> BaseChatModel:
    """
    Convenience wrapper: build an LLM and immediately attach
    structured output for the given Pydantic schema.

    Used by trading_agent.py to create sub-agent LLMs in one call.
    """
    llm = build_llm(config)
    return llm.with_structured_output(schema, method=method)