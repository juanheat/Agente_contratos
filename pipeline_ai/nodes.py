"""
Nodos del grafo LangGraph.

Cada función recibe el state y retorna únicamente los campos que modifica,
siguiendo la convención de LangGraph (retorno parcial del estado).
"""

import json
import logging

from utils.pdf_utils import extraer_paginas

logger = logging.getLogger(__name__)

# Texto fijo que usa el extractor en la primera pasada para otrosíes.
_EXTRACTOR_OTROSI_PRIMER_TURNO = (
    "Extrae y estructura exclusivamente la información que se encuentre "
    "explícitamente dentro del contrato. Debes extraer los siguientes campos, "
    "respetando exactamente el formato solicitado. El documento corresponde a "
    "contratos celebrados por EPS Sura con proveedores. "
    "EPS Sura es siempre la entidad contratante"
)


# ---------------------------------------------------------------------------
# Nodo 1 — Clasificador
# ---------------------------------------------------------------------------

def nodo_clasificador(state: dict, agents: dict) -> dict:
    """
    Clasifica el documento como CONTRATO, OTROSI u OTRO.
    Solo envía las primeras 3 páginas para ahorrar tokens.
    """
    logger.info("🔵 [Clasificador] Nodo ejecutado")

    pdf_corto = extraer_paginas(state["pdf"], num_paginas=3)

    mensaje = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Dime si este documento efectivamente es un contrato, "
                            "un otrosi o otra cosa diferente y dime qué tanta "
                            "confianza confirmas que lo es o no."
                        ),
                    },
                    {"type": "file", "base64": pdf_corto, "mime_type": "application/pdf"},
                ],
            }
        ]
    }

    response = agents["clasificador"].invoke(mensaje)
    structured = response.get("structured_response", {})
    tipo = structured.get("tipo_arch")

    logger.info("🔵 [Clasificador] Tipo detectado: %s", tipo)
    return {"tipo_archivo": tipo}


# ---------------------------------------------------------------------------
# Nodo 2 — Extractor
# ---------------------------------------------------------------------------

def nodo_extractor(state: dict, agents: dict) -> dict:
    """
    Extrae la información del PDF.
    - Primera pasada: extracción inicial.
    - Pasadas siguientes: corrección según feedback del validador.
    """
    tipo_archivo = state["tipo_archivo"]
    es_contrato = tipo_archivo == "CONTRATO"

    logger.info(
        "🟢 [Extractor] Nodo ejecutado — tipo: %s — intento: %d",
        tipo_archivo,
        state.get("attempts", 0) + 1,
    )

    agente = agents["extractor"] if es_contrato else agents["extractor_otrosi"]

    # ── Construcción del texto de usuario ──────────────────────────────────
    if state.get("validation") is None:
        # Primera pasada: incluir contexto
        if es_contrato:
            # FIX: se usaba state["input_data"] que no existe en el State.
            # El contexto correcto viene de context_cont (prompt base).
            user_text = state["prompt_cont"] + state["context_cont"]
        else:
            user_text = _EXTRACTOR_OTROSI_PRIMER_TURNO + state["context_cont"]
    else:
        # Pasadas de corrección: incluir feedback del validador
        fb = state["validation"].get("feedback", "")
        user_text = (
            f"Corrige y revisa la extracción anterior teniendo en cuenta "
            f"este feedback:\n{fb}\n"
        )

    # ── Historial de mensajes (se muta in-place, LangGraph lo propaga) ────
    hist = state["hist_msg_extration"]
    hist["messages"].append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "file", "base64": state["pdf"], "mime_type": "application/pdf"},
            ],
        }
    )

    response = agente.invoke(hist)
    structured = response.get("structured_response", {})

    hist["messages"].append(
        {"role": "assistant", "content": json.dumps(structured)}
    )

    logger.info("🟢 [Extractor] Resultado: %s", structured)

    return {
        "extracted_data": structured,
        "attempts": state.get("attempts", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Nodo 3 — Validador
# ---------------------------------------------------------------------------

def nodo_validador(state: dict, agents: dict) -> dict:
    """
    Valida la coherencia de la extracción.
    Retorna:
        validacion: 'CORRECTO' | 'CORREGIR'
        feedback:   'OK' | descripción del error
    """
    logger.info("🟣 [Validador] Nodo ejecutado")

    extracted = state.get("extracted_data", {})
    contexto = (
        state["context_cont"]
        if state["tipo_archivo"] == "CONTRATO"
        else state["context_otrosi"]
    )

    # ── Texto de usuario según turno ───────────────────────────────────────
    if state.get("validation") is None:
        user_text = (
            "Valida la siguiente extracción que se realizó de un PDF y valida "
            "la coherencia del resultado según las definiciones para cada campo:\n\n"
            f"Contexto: \n{contexto}\n"
            f"Información extraída del PDF: \n{extracted}\n\n"
            "No des corrección sobre lo que se clasifica como null; "
            "si envía un string 'null' igual se tomará como campo vacío.\n"
            "Importante validar que el contratista NUNCA sea EPS SURA / "
            "EPS SURAMERICANA con NIT 800088702-2, ya que este es el contratante.\n"
            "Si está todo bien → validacion='CORRECTO' y feedback='OK'.\n"
            "Si hay errores → validacion='CORREGIR' y en feedback explica qué corregir y por qué."
        )
    else:
        user_text = (
            "Valida si se corrigió el error antes mencionado. De no ser así, "
            "asume que en la segunda validación se confirma que el dato está "
            "bien construido. Además valida que el resto de la información sea coherente.\n"
            f"{extracted}\n"
            "Si está todo bien → validacion='CORRECTO' y feedback='OK'.\n"
            "Si hay errores → validacion='CORREGIR' y en feedback explica qué corregir y por qué."
        )

    hist = state["hist_msg_validation"]
    hist["messages"].append({"role": "user", "content": user_text})

    response = agents["validador"].invoke(hist)
    structured = response.get("structured_response", {})

    hist["messages"].append(
        {"role": "assistant", "content": json.dumps(structured)}
    )

    logger.info("🟣 [Validador] Resultado: %s", structured)
    return {"validation": structured}