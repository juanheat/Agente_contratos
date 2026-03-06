"""
Fábrica de LLM y agentes.

Centraliza la instanciación para que sea fácil:
- Cambiar modelo/parámetros en un solo lugar.
- Mockear en tests.
- Reutilizar el LLM entre agentes sin recrearlo.
"""

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory

from configuraciones_IA.schemas import (
    SCHEMA_OUTPUT_CLASIFICADOR,
    SCHEMA_OUTPUT_EXTRACTOR,
    SCHEMA_OUTPUT_EXTRACTOR_OTROSI,
    SCHEMA_OUTPUT_VALIDATION,
)
from configuraciones_IA.prompts import (
    SYSTEM_PROMPT_CLASIFICADOR,
    SYSTEM_PROMPT_EXTRACTOR,
    SYSTEM_PROMPT_EXTRACTOR_OTROSI,
    SYSTEM_PROMPT_VALIDATION,
)


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

def build_llm(
    model: str = "gemini-2.5-flash",
    project: str = "gcp-sura-auditoria-eps",
    temperature: float = 0,
    max_tokens: int = 4300,
    thinking_budget: int = 0,
) -> ChatGoogleGenerativeAI:
    """
    Instancia el LLM con la configuración estándar.
    Externaliza los parámetros para facilitar cambios por entorno.
    """
    return ChatGoogleGenerativeAI(
        model=model,
        project=project,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=None,
        max_retries=2,
        thinking_budget=thinking_budget,
        safety_settings={
            HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        },
    )


# ---------------------------------------------------------------------------
# Agentes
# ---------------------------------------------------------------------------

def build_agents(llm: ChatGoogleGenerativeAI) -> dict:
    """
    Crea todos los agentes del pipeline y los retorna en un diccionario.

    Uso:
        llm    = build_llm()
        agents = build_agents(llm)
        # agents["clasificador"], agents["extractor"], etc.
    """
    return {
        "clasificador": create_agent(
            llm,
            system_prompt=SYSTEM_PROMPT_CLASIFICADOR,
            response_format=ToolStrategy(SCHEMA_OUTPUT_CLASIFICADOR),
        ),
        "extractor": create_agent(
            llm,
            system_prompt=SYSTEM_PROMPT_EXTRACTOR,
            response_format=ToolStrategy(SCHEMA_OUTPUT_EXTRACTOR),
        ),
        "extractor_otrosi": create_agent(
            llm,
            system_prompt=SYSTEM_PROMPT_EXTRACTOR_OTROSI,
            response_format=ToolStrategy(SCHEMA_OUTPUT_EXTRACTOR_OTROSI),
        ),
        "validador": create_agent(
            llm,
            system_prompt=SYSTEM_PROMPT_VALIDATION,
            response_format=ToolStrategy(SCHEMA_OUTPUT_VALIDATION),
        ),
    }