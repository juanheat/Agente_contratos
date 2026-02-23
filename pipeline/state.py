from typing import TypedDict


class StateEstructure(TypedDict):
    prompt_cont: dict | str
    context_cont: str
    context_otrosi: str
    pdf: str
    tipo_archivo: str | None
    extracted_data: dict | str
    hist_msg_extration: dict
    validation: dict | None
    hist_msg_validation: dict
    attempts: int
    max_attempts: int


def build_initial_state(
    pdf: str,
    prompt_cont: dict | str,
    context_cont: str,
    context_otrosi: str,
    max_attempts: int = 3,
) -> StateEstructure:
    """
    Construye el estado inicial limpio para una nueva ejecución del grafo.

    Args:
        pdf:            PDF en base64.
        prompt_cont:    Prompt/contexto base del contrato.
        context_cont:   Contexto adicional para contratos.
        context_otrosi: Contexto adicional para otrosíes.
        max_attempts:   Máximo de intentos de corrección entre extractor y validador.

    Returns:
        StateEstructure lista para pasarle a graph.invoke().
    """
    return StateEstructure(
        prompt_cont=prompt_cont,
        context_cont=context_cont,
        context_otrosi=context_otrosi,
        pdf=pdf,
        tipo_archivo=None,
        extracted_data={},
        hist_msg_extration={"messages": []},
        validation=None,
        hist_msg_validation={"messages": []},
        attempts=0,
        max_attempts=max_attempts,
    )