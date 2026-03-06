"""
API pública del pipeline.

Expone una única función `run_pipeline()` que orquesta todo internamente.
El consumidor (main.py, un endpoint, un job, etc.) solo necesita importar esto.
"""

import logging

from pipeline_ai.agents_factory import build_agents, build_llm
from pipeline_ai.graph import build_graph
from pipeline_ai.state import build_initial_state, StateEstructure

from configuraciones_IA.prompts import prompt_cont, context_cont, context_otrosi

logger = logging.getLogger(__name__)


def run_pipeline(
    pdf_base64: str,
    max_attempts: int = 3,
    llm_kwargs: dict | None = None,
) -> dict:
    """
    Ejecuta el pipeline completo de clasificación → extracción → validación.

    Args:
        pdf_base64:   PDF codificado en base64.
        max_attempts: Máximo de ciclos extractor ↔ validador antes de forzar END.
        llm_kwargs:   Parámetros opcionales para sobreescribir la config del LLM
        (ej. {"model": "gemini-2.0-flash", "temperature": 0.2}).

    Returns:
        El StateEstructure final con todos los campos poblados:
            - tipo_archivo:   'CONTRATO' | 'OTROSI' | otro
            - extracted_data: dict con la información extraída
            - validation:     dict con la validación final
            - attempts:       cantidad de intentos realizados
    """
    logger.info("[Pipeline] Iniciando ejecución")

    llm    = build_llm(**(llm_kwargs or {}))
    agents = build_agents(llm)
    graph  = build_graph(agents)

    initial_state: StateEstructure = build_initial_state(
        pdf=pdf_base64,
        prompt_cont=prompt_cont,
        context_cont=context_cont,
        context_otrosi=context_otrosi,
        max_attempts=max_attempts,
    )

    result = graph.invoke(initial_state)

    logger.info(
        "✅ [Pipeline] Finalizado — tipo: %s — intentos: %d",
        result.get("tipo_archivo"),
        result.get("attempts", 0),
        # result.get("validation", {}).get("validacion"),
    )

    return result