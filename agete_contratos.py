# pip install google-cloud-aiplatform langchain-google-vertexai langchain
# gcloud auth application-default login
from langchain.agents import create_agent
from langchain_google_genai import (ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory)
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import HumanMessage
import json
import base64
from langgraph.graph import StateGraph, START, END
from typing import TypedDict




def file_to_base64(path: str) -> str:
    """
    Lee un archivo local y lo convierte a base64.
    Retorna el string base64 sin saltos de línea.
    """
    with open(path, "rb") as f:
        file_bytes = f.read()

    base64_bytes = base64.b64encode(file_bytes)
    base64_string = base64_bytes.decode("utf-8")

    return base64_string


pdf = file_to_base64('Firmado_Minuta (4).pdf')


SYSTEM_PROMPT_CLASIFICADOR = (
    "Eres un experto legal capaz de diferenciar un contrato legal de cualquier otro documento.\n"
    "Debes determinar si el documento proporcionado es un contrato o no."
)
SYSTEM_PROMPT_EXTRACTOR = (
    "Eres un asistente experto en lectura y análisis de documentos, especializado en extraer información estructurada desde texto obtenido de PDFs.\n"
    "Tu objetivo es extraer datos estructurados sin inventar información.\n"
    "Eres completamente determinista, preciso y literal."
)

SYSTEM_PROMPT_VALIDATION = (
    "Eres un asistente especializado en validar información extraída desde documentos.\n"   
    "Tu tarea: \n"
    "- Revisar el JSON producido por el extractor.\n"
    "- Verificar si cada el contenido extraido es coherente y valido.\n"
    "No devuelvas texto fuera del JSON."
)




SCHEMA_OUTPUT_CLASIFICADOR = {
    "title": "ClasificadorInformacion",
    "type": "object",
    "properties":{
        "tipo_doc":{
            "type": "string",
            
            
            "description": ""
        }
    }
}


SCHEMA_OUTPUT_EXTRACTOR = {
    "title": "EstructuracionInformacion",
    "type": "object",
    "properties":{
        "contrato_id":{
            "type": "string",
            "description": "Identificador alfanumérico único del contrato."
        },
        "fecha_suscripcion":{
            "type": "string",
            "descripcion": "Fecha (YYYY-MM-DD) en que se firma el contrato. Puede coincidir que esta fecha sea igual a la fecha de inicio de vigencia del contrato, pero nunca puede ser posterior a la misma"
        },
        "fecha_inicio":{
            "type": "string",
            "description": "Fecha (YYYY-MM-DD) en la que inició el contrato."
        },
        "fecha_fin": {
            "type": "string",
            "description": "Fecha (YYYY-MM-DD) en la que terminarìa el contrato."
        },
        "clase_contrato": {
            "type": "string",
            "description": "Tipo de contrato por el que se realizó la contratación"
        },
        "objeto_contrato": {
            "type": "string",
            "description": "Objetivo del contrato máximo de 300 caracteres"
        }
    },
    "required": ["contrato_id", "fecha_suscripcion", "fecha_inicio", "fecha_fin", "clase_contrato", "objeto_contrato"]
}

SCHEMA_OUTPUT_VALIDATION = {
    "title": "ValidacionInformacion",
    "type": "object",
    "properties":{
        "validacion":{
            "type": "string",
            "enum": ["CORRECTO", "CORREGIR"],
            "description": "Se debe poner CORRECTO, si consideras que la informacón extraida es coherente, o  CORREGIR, si consideras que la información extraida no tiene sentido o debe corregirse"
        },
        "feedback":{
            "type": "string",
            "description": "Debes escribir detalladamente que es lo que debe corregir o revisar si está bien hecho."
        }
    },
    "required": ["validacion", "feedback"]
}


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
    input_data: dict | str
    context: str
    extracted_data: str
    hist_msg_extration: dict
    validation: dict | None
    hist_msg_validation: dict
    attempts: int                             # contador para evitar loops infinitos
    max_attempts: int

# NODOS
# 1. AGENTE EXTRACTOR


extractor_agent = create_agent(
    llm,
    system_prompt= SYSTEM_PROMPT_EXTRACTOR,
    response_format=ToolStrategy(SCHEMA_OUTPUT_EXTRACTOR)
)

validator_agent = create_agent(
    llm,
    system_prompt= SYSTEM_PROMPT_VALIDATION,
    response_format=ToolStrategy(SCHEMA_OUTPUT_VALIDATION)
)



def AgenteExtractorNode(state: StateEstructure):

    """
    Si no hay feedback, genera extracción inicial.
    Si hay feedback, corrige según feedback.
    """
    # arma el mensaje (siempre en formato messages para consistencia)
    print("\n==============================")
    print("🔵 [Extractor] Nodo ejecutado")
    print("==============================")
    print("Estado recibido:")
    print(state)
    
    if state.get("validation") is None:
        user_text = state["input_data"] + state['context']
        print("\n[Extractor] Primera extracción")
        # state["hist_msg_extration"]["messages"].append({"role": "user", "content":[{"type": "text", "text": user_text},
        #                                     {"type": "file", "base64": pdf, "mime_type": "application/pdf"}]})
         
    else:
        fb = state["validation"].get("feedback", "")
        user_text = (
            f"Corrige y revisa la extracción anterior teniendo en cuenta este feedback:\n{fb}\n"
        )
        print("\n[Extractor] Corrección basada en feedback:")
        print("Feedback recibido:", fb)
        # state["hist_msg_extration"]["messages"].append({"role": "user", "content": user_text})

    state["hist_msg_extration"]["messages"].append({"role": "user", "content":[{"type": "text", "text": user_text},
                                        {"type": "file", "base64": pdf, "mime_type": "application/pdf"}]})
    
    response = extractor_agent.invoke(state["hist_msg_extration"])

    # comprobar que structured_response esté presente
    structured = response.get("structured_response")
    state["hist_msg_extration"]["messages"].append({"role": "assistant", "content": json.dumps(structured)})
    print("\n[Extractor] structured_response generado:")
    print(structured)
    
    return {"extracted_data": structured, "attempts": state.get("attempts", 0) + 1}



def AgenteValidadorNode(state: StateEstructure):
    """
    Valida la extracción. Devuelve structured_response con keys: validacion, feedback
    """
    
    print("\n==============================")
    print("🟣 [Validador] Nodo ejecutado")
    print("==============================")
    print("Extracción recibida para validar:")
    print(state.get("extracted_data", {}))
    
    extracted = state.get("extracted_data", {})
    
    if state.get("validation") is None:
        user_text = (
            "Valida la siguiente extracción que se realizó de un PDF y valida la coherencia del resultado según las definiciones para cada campo:\n\n"
            f"Contexto: \n {state["context"]} \n"
            f"Información extraida del PDF: \n{extracted}\n\n"
            "Si está todo bien responde validacion='CORRECTO' y en feedback escribe 'OK'. "
            "Si hay errores responde validacion='CORREGIR' y en feedback explica qué corregir y por qué."
        )
        print("\n[Extractor] Primera extracción")
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

    print("\n[Validador] structured_response generado:")
    print(structured)
    
    return {"validation": structured}

    
    

builder = StateGraph(StateEstructure)

builder.add_node("extractor", AgenteExtractorNode)
builder.add_node("validador", AgenteValidadorNode)

builder.add_edge(START, "extractor")
builder.add_edge("extractor", "validador")

# Lógica: si validación requiere corrección → volver al extractor

def routing(state: StateEstructure):
    # seguridad: si llegamos al max intents -> END
    attempts = state.get("attempts", 0)
    max_attempts = state.get("max_attempts", 5)
    validation = state.get("validation")
    # extraer el valor
    val = validation.get("validacion", "").upper()
    
    
    print("\n==============================")
    print("🟠 [Router] Decisión del grafo")
    print("==============================")
    print("Validación:", val)
    print("Intentos:", attempts)
    print("Max intentos:", max_attempts)
    
    
    if val == "CORRECTO":
        print("[Router] → END")
        return END
    # si 'CORREGIR' o cualquier otro -> repetir, hasta max
    if attempts >= max_attempts:
        print("[Router] → END (máximos intentos alcanzados)")
        return END
    print("[Router] → extractor (se requiere corrección)")
    return "extractor"

builder.add_conditional_edges("validador", routing, ["extractor", END])

graph = builder.compile()


"""
PROMPT
"""

# From base64 data
msg = """Extrae y estructura exclusivamente la información que se encuentre explícitamente dentro del contrato.  
        Debes extraer los siguientes campos, respetando exactamente el formato solicitado.

        Si alguno de estos datos no aparece de manera explícita en el documento, devuelve el campo con el valor null.
        No infieras, no completes, no inventes información. Extrae únicamente lo que esté escrito literalmente en el contrato.
"""

context = """
        - contrato_id: Identificador del contrato tal como aparece en el documento.
        - fecha_suscripción: Fecha en que se suscribe o firma el contrato.
        - fecha_inicio: Fecha en que inicia la ejecución del contrato.
        - fecha_fin: Fecha en que termina la ejecución del contrato.
        - clase_contrato: Tipo o modalidad del contrato según lo indicado en el documento.
        - objeto_contrato: Texto completo que describa el objeto contractual exactamente como aparece en el contrato.
"""



initial_state: StateEstructure = {
    "input_data": msg,
    "context": context,
    "extracted_data": {},
    "hist_msg_extration": {"messages": []},
    "validation": None,
    "hist_msg_validation": {"messages": []},
    "attempts": 0,
    "max_attempts": 3
}


result = graph.invoke(initial_state)
print("Resultado final:", result)



initial_state['hist_msg_extration']

