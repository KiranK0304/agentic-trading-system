from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from pydantic import Field, BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class LLMConfig(BaseModel):
    """ all llm configuration in one place"""
    provider: str = Field(default="openai", description="openai, anthropic, grok, etc.")
    model_name: str = "llama-3.1-8b-instant"  #WHY TWICE?
    temperature: float = 0.0


def build_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """Central place to create any LLM. No side effects at import time."""
    if config is None:
        config = LLMConfig()

    if config.provider == "openai":
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            openai_api_base=os.environ.get("base_url"),
            openai_api_key=os.environ.get("GROQ_API_KEY")
        )
    # Add other providers here (Anthropic, Grok via xAI, etc.)
    raise ValueError(f"Unsupported provider: {config.provider}")

def build_structured_llm(schema: type[BaseModel], 
                        config: LLMConfig | None = None,
                        ) -> BaseChatModel:
    """Convenience for nodes that need .with_structured_output()."""
    llm = build_llm(config)
    return llm.with_structured_output(schema)

#=========================
# Need more clarity 
# In the above code
#=========================