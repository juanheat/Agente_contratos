# pip install google-cloud-aiplatform langchain-google-vertexai langchain
# gcloud auth application-default login
from langchain.agents import create_agent
from langchain_google_genai import (ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory)
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import HumanMessage
import json
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
import os

# SCHEMAS
from configuraciones_IA.schemas import SCHEMA_OUTPUT_CLASIFICADOR, SCHEMA_OUTPUT_EXTRACTOR_OTROSI, SCHEMA_OUTPUT_EXTRACTOR, SCHEMA_OUTPUT_VALIDATION
# PROMPTS
from configuraciones_IA.prompts import SYSTEM_PROMPT_CLASIFICADOR, SYSTEM_PROMPT_EXTRACTOR_OTROSI, SYSTEM_PROMPT_EXTRACTOR, SYSTEM_PROMPT_VALIDATION, prompt_cont, context_cont, context_otrosi
# Procesamiento de pdfs
from utils.pdf_utils import extraer_paginas, file_to_base64



docs = os.listdir("contratos")

pdf = file_to_base64(f"contratos/{docs[0]}")
pdf = file_to_base64('Firmado_Minuta (4).pdf')


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    project="gcp-sura-auditoria-eps",
    temperature= 0,
    max_tokens=4300,
    timeout=None,
    max_retries=2,
    thinking_budget= 0,
    safety_settings={
        HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    },
)


"""
CREACIÓN DE AGENTES
"""

# creación del State


class StateEstructure(TypedDict):
    prompt_cont: dict | str
    context_cont: str
    context_otrosi: str
    pdf: str
    tipo_archivo: str
    extracted_data: str
    hist_msg_extration: dict
    validation: dict | None
    hist_msg_validation: dict
    attempts: int                             # contador para evitar loops infinitos
    max_attempts: int

# NODOS
# 1. AGENTE EXTRACTOR

clasificator_agent = create_agent(
    llm,
    system_prompt= SYSTEM_PROMPT_CLASIFICADOR,
    response_format=ToolStrategy(SCHEMA_OUTPUT_CLASIFICADOR)
)


extractor_agent = create_agent(
    llm,
    system_prompt= SYSTEM_PROMPT_EXTRACTOR,
    response_format=ToolStrategy(SCHEMA_OUTPUT_EXTRACTOR)
)

extractor_otrosi_agent = create_agent(
    llm,
    system_prompt= SYSTEM_PROMPT_EXTRACTOR_OTROSI,
    response_format=ToolStrategy(SCHEMA_OUTPUT_EXTRACTOR_OTROSI)
)

validator_agent = create_agent(
    llm,
    system_prompt= SYSTEM_PROMPT_VALIDATION,
    response_format=ToolStrategy(SCHEMA_OUTPUT_VALIDATION)
)


def AgenteClasificadorNode(state: StateEstructure):
    pdf = state['pdf']
    pdf_corto = extraer_paginas(pdf, 3)


    m = {"messages": [{'role': 'user', 'content': [{"type": "text", "text": "Dime si este documento efectivamente es un contrato, un otrosi o otra cosa diferente y dime que tanta confianza confirmas que lo es o no."},
                                                {"type": "file", "base64": pdf_corto, "mime_type": "application/pdf"}]}]}
    response = clasificator_agent.invoke(m)
    
    structured = response.get("structured_response")
    return {"tipo_archivo": structured['tipo_arch']}



def AgenteExtractorNode(state: StateEstructure):

    """
    Si no hay feedback, genera extracción inicial.
    Si hay feedback, corrige según feedback.
    """
    # arma el mensaje (siempre en formato messages para consistencia)
    pdf = state['pdf']
    tipo_archivo = state['tipo_archivo']

    if tipo_archivo == "CONTRATO":
        print("\n==============================\n","🔵 [Extractor] Nodo ejecutado\n", "==============================\n")
        agente = extractor_agent
        
        if state.get("validation") is None:
            user_text = state["prompt_cont"] + state['context_cont']
    
        else:
            fb = state["validation"].get("feedback", "")
            user_text = (
                f"Corrige y revisa la extracción anterior teniendo en cuenta este feedback:\n{fb}\n"
            )
    else:
        agente = extractor_otrosi_agent
        
        if state.get("validation") is None:
            input = "Extrae y estructura exclusivamente la información que se encuentre explícitamente dentro del contrato. Debes extraer los siguientes campos, respetando exactamente el formato solicitado. El documento corresponde a contratos celebrados por EPS Sura con proveedores. EPS Sura es siempre la entidad contratante"
            user_text = input + state['context_cont']
        else:
            fb = state["validation"].get("feedback", "")
            user_text = (
                f"Corrige y revisa la extracción anterior teniendo en cuenta este feedback:\n{fb}\n"
            )
        
        
    state["hist_msg_extration"]["messages"].append({"role": "user", "content":[{"type": "text", "text": user_text},
                                        {"type": "file", "base64": pdf, "mime_type": "application/pdf"}]})
    
    response = agente.invoke(state["hist_msg_extration"])

    # comprobar que structured_response esté presente
    structured = response.get("structured_response")
    state["hist_msg_extration"]["messages"].append({"role": "assistant", "content": json.dumps(structured)})

    print(structured)
    
    return {"extracted_data": structured, "attempts": state.get("attempts", 0) + 1}



def AgenteValidadorNode(state: StateEstructure):
    """
    Valida la extracción. Devuelve structured_response con keys: validacion, feedback
    """
    print("\n==============================\n","🟣 [Validador] Nodo ejecutado\n", "==============================\n")
    
    extracted = state.get("extracted_data", {})
    
    if state["tipo_archivo"] == "CONTRATO":
        contexto = state["context_cont"]
    else:
        contexto = state['context_otrosi']
    
    if state.get("validation") is None:
        user_text = (
            "Valida la siguiente extracción que se realizó de un PDF y valida la coherencia del resultado según las definiciones para cada campo:\n\n"
            f"Contexto: \n {contexto} \n"
            f"Información extraida del PDF: \n{extracted}\n\n"
            "No des corrección de sobre lo que se clasifica como null, no importa si envia un estring 'null', igual lo tomaremos como un campo vacio\n"
            "Importante validar que el contratista nunca sea EPS SURA/ EPS SURAMERICANA con NIT 800088702-2 ya que este es el contratante. \n"
            "Si está todo bien responde validacion='CORRECTO' y en feedback escribe 'OK'.\n"
            "Si hay errores responde validacion='CORREGIR' y en feedback explica qué corregir y por qué.\n"
        )
    else:
        user_text = ("Valida si se corrigió el error antes mencionado, de no serlo así asume que en la segunda valiación se confirma que el dato está bien contruido. Además valida que el resto de la información sea coherente.\n"
                     f"{extracted}\n"
                    "Si está todo bien responde validacion='CORRECTO' y en feedback escribe 'OK'.\n"
                    "Si hay errores responde validacion='CORREGIR' y en feedback explica qué corregir y por qué."
        )
      
    state["hist_msg_validation"]["messages"].append({"role": "user", "content":user_text})

    response = validator_agent.invoke(state["hist_msg_validation"])

    structured = response.get("structured_response")
    
    state["hist_msg_validation"]["messages"].append({"role": "assistant", "content":json.dumps(structured)})

    print(structured)
    
    return {"validation": structured}

    
    

builder = StateGraph(StateEstructure)

builder.add_node("clasificador", AgenteClasificadorNode)
builder.add_node("extractor", AgenteExtractorNode)
builder.add_node("validador", AgenteValidadorNode)



builder.add_edge(START, "clasificador")

def routing_clasif(state: StateEstructure):

    tipo_archivo = state.get("tipo_archivo")

    print("\n==============================\n","🟠 [Router clasif] Decisión del grafo clasificacion\n", "==============================\n")
    print("Tipo de archivo:", tipo_archivo)


    if tipo_archivo in ["CONTRATO",  "OTROSI"]:
        print("[Router clasif] → extractor")
        return "extractor"
    print("[Router clasif] → END: no es un contrato legal")
    return END

builder.add_conditional_edges("clasificador", routing_clasif, ["extractor",  END])

builder.add_edge("extractor", "validador")

# Lógica: si validación requiere corrección → volver al extractor
def routing_val(state: StateEstructure):
    # seguridad: si llegamos al max intents -> END
    attempts = state.get("attempts", 0)
    max_attempts = state.get("max_attempts", 5)
    validation = state.get("validation")
    # extraer el valor
    val = validation.get("validacion", "").upper()
    
    print("\n==============================\n","🟠 [Router val] Decisión del grafo validacion\n", "==============================\n")
    print("Validación:", val)
    print("Intentos:", attempts)

    if val == "CORRECTO":
        print("[Router] → END")
        return END
    # si 'CORREGIR' o cualquier otro -> repetir, hasta max
    if attempts >= max_attempts:
        print("[Router] → END (máximos intentos alcanzados)")
        return END
    print("[Router] → extractor (se requiere corrección)")
    return "extractor"
        

builder.add_conditional_edges("validador", routing_val, ["extractor", END])
graph = builder.compile()


# Graficar el grafo
mermaid = graph.get_graph().draw_mermaid()
# print(mermaid)


"""
Para las adiciones se debe tener en cuenta que, las fechas y el valor se deben cambiar si tienen otrosi
"""

initial_state: StateEstructure = {
    "prompt_cont": prompt_cont,
    "context_cont": context_cont,
    "context_otrosi": context_otrosi,
    "pdf": pdf,
    "tipo_archivo":None, 
    "extracted_data": {},
    "hist_msg_extration": {"messages": []},
    "validation": None,
    "hist_msg_validation": {"messages": []},
    "attempts": 0,
    "max_attempts": 3
}



result = graph.invoke(initial_state)


hist = initial_state["hist_msg_extration"]
