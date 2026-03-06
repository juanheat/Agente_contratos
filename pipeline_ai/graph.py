"""
Construcción y compilación del StateGraph.

Separa la definición del grafo de los nodos y del punto de entrada,
de modo que el grafo sea fácilmente testeable y reutilizable.
"""

import logging
from functools import partial

from langgraph.graph import END, START, StateGraph

from pipeline_ai.nodes import nodo_clasificador, nodo_extractor, nodo_validador
from pipeline_ai.state import StateEstructure

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

def _router_clasificador(state: StateEstructure) -> str:
    """Decide si el documento debe ir al extractor o terminar."""
    tipo = state.get("tipo_archivo")
    logger.info("🟠 [Router Clasificador] tipo_archivo=%s", tipo)

    if tipo in ("CONTRATO", "OTROSI"):
        return "extractor"
    logger.info("🟠 [Router Clasificador] → END: documento no procesable")
    return END


def _router_validador(state: StateEstructure) -> str:
    """Decide si se requiere una nueva extracción o el pipeline termina."""
    attempts = state.get("attempts", 0)
    max_attempts = state.get("max_attempts", 3)
    validation = state.get("validation", {})
    val = validation.get("validacion", "").upper()

    logger.info("🟠 [Router Validador] validacion=%s — intentos=%d/%d", val, attempts, max_attempts)

    if val == "CORRECTO":
        logger.info("🟠 [Router Validador] → END: extracción correcta")
        return END

    if attempts >= max_attempts:
        logger.warning("🟠 [Router Validador] → END: máximos intentos alcanzados")
        return END

    logger.info("🟠 [Router Validador] → extractor: se requiere corrección")
    return "extractor"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_graph(agents: dict):
    """
    Construye y compila el StateGraph con los agentes dados.

    Usar `partial` permite inyectar `agents` en cada nodo sin convertirlos
    en globales, manteniendo los nodos testeables de forma aislada.

    Args:
        agents: Diccionario retornado por `pipeline.agents_factory.build_agents()`.

    Returns:
        CompiledGraph listo para invocar con `graph.invoke(state)`.
    """
    builder = StateGraph(StateEstructure)

    # Nodos — se inyecta `agents` vía partial para evitar globals
    builder.add_node("clasificador", partial(nodo_clasificador, agents=agents))
    builder.add_node("extractor",    partial(nodo_extractor,    agents=agents))
    builder.add_node("validador",    partial(nodo_validador,    agents=agents))

    # Edges
    builder.add_edge(START, "clasificador")
    builder.add_conditional_edges("clasificador", _router_clasificador, ["extractor", END])
    builder.add_edge("extractor", "validador")
    builder.add_conditional_edges("validador", _router_validador, ["extractor", END])

    return builder.compile()