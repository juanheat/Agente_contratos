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
from pypdf import PdfReader, PdfWriter
import io
import os


def extraer_paginas(pdf_base64: str, num_paginas: int = 3) -> str:
    """Extrae las primeras N páginas de un PDF en base64 y devuelve un nuevo PDF en base64."""
    
    pdf_bytes = base64.b64decode(pdf_base64)
    
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for i in range(min(num_paginas, len(reader.pages))):
        writer.add_page(reader.pages[i])

    output = io.BytesIO()
    writer.write(output)

    return base64.b64encode(output.getvalue()).decode("utf-8")




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

docs = os.listdir("contratos")

pdf = file_to_base64(f"contratos/{docs[0]}")
pdf = file_to_base64('Firmado_Minuta (4).pdf')

SYSTEM_PROMPT_CLASIFICADOR = (
    "Eres un experto legal especializado en clasificación documental.\n"
    "Tu tarea es analizar el archivo proporcionado y determinar si corresponde a un CONTRATO legal, un OTROSI (adición de un contrato base) o a cualquier otro tipo de documento.\n"
    "No inventes información ni infieras contenido ausente. Solo clasifica el documento basado en lo que leas.\n"
)

SYSTEM_PROMPT_EXTRACTOR_OTROSI = (
    "Eres un agente especializado en la lectura y análisis de “otrosí” o modificaciones contractuales. Tu objetivo es identificar con precisión si el documento incluye: ['ADICIÓN EN TIEMPO', 'ADICIÓN EN VALOR', 'AMBAS', 'NINGUNA'] \n"
    "Identifica cualquier modificación al valor, presupuesto, precio, monto, costos adicionales o incrementos del contrato."
    "La forma como se formula la modificación (por ejemplo: prórroga, ampliación, extensión, adición, incremento, ajuste, modificación)."
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
        "tipo_arch":{
            "type": "string",
            "enum": ["CONTRATO", "OTROSI", "OTRO"],
            "description": "Determina si se clasifica como un contrato, otrosi o algo diferente"
        },
        "confianza":{
            "type": "number",
            "minimum": 0.00,
            "maximum": 1.00,
            "description": "Nivel de confianza del modelo en la clasificación, entre 0 y 1."
        }
    }
}


SCHEMA_OUTPUT_EXTRACTOR_OTROSI = {
    "title": "EstrucruracionInfoOtrosi",
    "type": "object",
    "properties":{
        "ident" : {
            "type": "object",
            "properties":{
                "contrato_base_id": {
                    "type": ["string", "null"],
                    "description": "Identificador alfanumérico único del contrato base o padre.",
                    "nullable": True
                },
                "otrosi_id":{
                    "type": "string",
                    "description": "Identificador alfanumérico único del contrato.",
                    "nullable": False
                }
            }
        },
        "adiciones": {
            "type": "object",
            "properties":{
                "tipo": {
                    "type": "string",
                    "description": "Tipo de adición que se realiza al contrato base por medio de este otrosi",
                    "enum": ["ADICIÓN EN TIEMPO", "ADICIÓN EN VALOR", "AMBAS", "NINGUNA"]
                },
                "fecha_fin":{
                    "type": ["string", "null"],
                    "description": "Fecha (YYYY-MM-DD) en la que terminarìa el contrato. Si no aparece devuelve null.",
                    "nullable": True
                },
                "valor": {
                    "type": ["number", "null"],
                    "description": "Valor económico en pesos colombianos (COP). Puede estar con o sin IVA. Si no aparece devuelve null."
                }
            }
        }
}}

SCHEMA_OUTPUT_EXTRACTOR = {
    "title": "EstructuracionInformacion",
    "type": "object",
    "properties":{
        "contrato_id":{
            "type": "string",
            "description": "Identificador alfanumérico único del contrato.",
            "nullable": False
        },
        "valor":{
            "type": "number",
            "description": "Valor económico pactado en el contrato en pesos colombianos (COP). Puede estar con o sin IVA. Si no aparece explícitamente, devolver 0.",
            "nullable": False
        },
        "objeto_contrato": {
            "type": "string",
            "description": "Resumen del servicio contratado por EPS SURA y pactado en el contrato."
        },
        "fechas":{
            "type": "object",
            "properties":{
                "fecha_suscripcion":{
                    "type": "string",
                    "format":"date",
                    "descripcion": "Fecha (YYYY-MM-DD) en que se firma el contrato. Puede coincidir que esta fecha sea igual a la fecha de inicio de vigencia del contrato, pero nunca puede ser posterior a la misma"
                },
                "fecha_inicio":{
                    "type": "string",
                    "format":"date",
                    "description": "Fecha (YYYY-MM-DD) en la que inició el contrato.",
                    "nullable": False
                },
                "fecha_fin": {
                    "type":["string", "null"],
                    "format":"date",
                    "description": "Fecha (YYYY-MM-DD) en la que terminarìa el contrato. Si no aparece se considera contrato a término indefinido y se devuelve null.",
                    "nullable": True
                }
            }  
        },
        "contratista":{
            "type": "object",
            "descripcion":"Información del prestador del servicio. Si aparecen varios nombres, se considera como algun tipo de PERSONA JURÍDICA y se toma únicamente el primero.",
            "properties":{
                "tipo_persona": {
                    "type": "string",
                    "description": "Con que tipo de persona se contrata",
                    "enum": ["PERSONA NATURAL", "PERSONA JURÍDICA", "PERSONA JURÍDICA - UNIÓN TEMPORAL o CONSORCIO" ],
                    "nullable": False
                    
                },
                "tipo_documento":{
                    "type": "string",
                    "description": "Tipo de documento identificado en el contrato.",
                    "enum": ["NIT", "RUT - REGISTRO ÚNICO TRIBUTARIO", "CÉDULA DE CIUDADANÍA", "CÉDULA DE EXTRANJERÍA"],
                    "nullable": False
                },
                "numero_documento":{
                    "type": "number",
                    "description":"Número de identificación del prestador solo si es persona jurídica, de ser una persona juridica, no incluir el dígito de verificación.",
                    "nullable": False
                },
                "digito_verificación":{
                    "type":["number", "null"],
                    "description":"Dígito verificador del NIT (solo aplica a personas jurídicas). Si no está presente, devolver nulo",
                    "minimum": 0,
                    "maximum": 9,
                    "nullable": True
                },
                "nombre_persona":{
                    "type": "string",
                    "description": "Nombre legal del prestador. Si hay varios nombres, se toma el primero.",
                    "nullable": False
                }
            }
        },
        "plazo_contrato":{
            "type": "number",
            "description": "Cantidad de días entre fecha_inicio y fecha_fin. Si no existe fecha_fin, devolver 0.",
            "mininimum":0,
            "nullable": False
            },
        "clase_contrato": {
            "type": "string",
            "description": "Clase de contrato según el contenido del objeto contractual y el tipo real de actividad que realizará el contratista",
            "enum": ["AGENCIA", "ARRENDAMIENTO y/o ADQUISICIÓN DE INMUEBLES", "CESIÓN DE CRÉDITOS", "COMISION", "COMODATO", "COMPRAVENTA MERCANTIL", "COMPRAVENTA y/o SUMINISTRO", "CONCESIÓN", "CONSULTORÍA", "CONTRATOS DE ACTIVIDAD CIENTÍFICA Y TECNOLÓGICA", "PRESTACIÓN DE SERVICIOS", "CONTRATOS DE ESTABILIDAD JURÍDICA", "DEPÓSITO", "FACTORING", "FIDUCIA y/o ENCARGO FIDUCIARIO", "FLETAMENTO", "FRANQUICIA", "INTERVENTORÍA", "LEASING", "MANTENIMIENTO y/o REPARACIÓN", "MEDIACIÓN o MANDATO", "OBRA PÚBLICA", "PERMUTA", "PRESTACIÓN DE SERVICIOS DE SALUD", "PRÉSTAMO o MUTUO", "PUBLICIDAD", "RENTING", "SEGUROS", "TRANSPORTE", "OTRO"],
            "nullable": False
        },
    },
} # hace falta añadir las "adiciones"
# , "PRESTACIÓN DE SERVICIOS"


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
            user_text = state["input_data"] + state['context_cont']
    
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
    tipo_archivo = state.get("tipo_archivo")
    
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
PROMPT
"""

# From base64 data
msg = """Extrae y estructura exclusivamente la información que se encuentre explícitamente dentro del contrato. Debes extraer los siguientes campos, respetando exactamente el formato solicitado. El documento corresponde a contratos celebrados por EPS Sura con proveedores.
        EPS Sura es siempre la entidad contratante, por lo que nunca la incluyas como prestador del servicio. Si alguno de estos datos no aparece de manera explícita en el documento, devuelve el campo con el valor null.
        No infieras, no completes, no inventes información. Extrae únicamente lo que esté escrito literalmente en el contrato. IMPORTANTE: NO cites cláusulas, NO menciones anexos si es necesario mencionarlo plasmalos en forma de resumen esta parte. Ten en cuenta que la persona que lee tu mensaje no tiene contexto del contrato, entonces no cites cosas dentro porque no va a entender.
"""

context_cont = """
- contrato_id: Identificador del contrato, usualmente alfanumérico y frecuentemente inicia con “CW”.
- valor: Valor económico pactado en el contrato en pesos colombianos (COP), si es en otra moneda se debe hacer el cambio según la tasa de cambio. Puede estar expresado con o sin IVA. Si no aparece explícitamente en ninguna cláusula, devolver 0. Debe ser el valor total que se tiene estipulado por toda la contratación.  Si el contrato incluye tarifas por hora, valores referenciales, costos máximos, precios por actividad o valors estimados PERO no indica un valor total contratado, el valor debe ser 0. Solo se debe reportar un valor distinto de 0 si el contrato establece explícitamente un valor total global contratado.
- fechas:
    - fecha_suscripción: Fecha de firma del contrato. Puede encontrarse en la portada, cláusulas o en la sección de firmas. Formato esperado: YYYY-MM-DD. Debe ser menor o igual a la fecha de inicio.
    - fecha_inicio: Fecha en la que inicia la ejecución del contrato. Debe ser mayor o igual a la fecha de suscripción.
    - fecha_fin: Fecha en la que termina la ejecución del contrato. Si no aparece, se considera un contrato sin término definido → devolver null.
- objeto_contrato: Debes generar un resumen de máximo 30 palabras que describa con claridad la actividad real que el contratista realizará según el documento. 
- contratista: Cuando el contrato menciona varias personas o razones sociales, se toma la primera que aparezca.
    - tipo_persona: Determinar si es PERSONA NATURAL, PERSONA JURÍDICA, PERSONA JURÍDICA - UNIÓN TEMPORAL o CONSORCIO. Si hay varios nombres o razón social compuesta → se trata como persona jurídica.
    - tipo_documento: Puede ser NIT, RUT, CÉDULA DE CIUDADANÍA o CÉDULA DE EXTRANJERÍA. Debe tomarse exactamente como aparezca.
    - numero_documento: Número de identificación del prestador. Si es NIT, NO incluir el dígito de verificación.
    - digito_verificacion: Solo aplica para personas jurídicas con NIT. Si el dígito no aparece explícitamente, devolver null (no calcularlo).
    - nombre_persona: Nombre del prestador tal como aparece en el contrato. Si hay varias menciones, tomar la primera.
- plazo_contrato: Número de días entre fecha_inicio y fecha_fin. Si no existe fecha_fin, devolver 0.
- clase_contrato: Debe clasificarse EXCLUSIVAMENTE según el contenido del objeto contractual y el tipo real de actividad que realizará el contratista (la contraparte distinta a EPS Sura). Usa las categorías proporcionadas siguiendo esta regla estricta:\n1. Primero intenta asignar la categoría que mejor coincida de forma explícita con las acciones descritas en el objeto contractual\n2. Solo asigna “PRESTACIÓN DE SERVICIOS” si y únicamente si: el objeto contractual NO describe ninguna actividad que encaje razonablemente con las demás categorías, o el objeto contractual es genérico y no permite determinar una actividad más específica.
""" 

context_otrosi = """
- identificacion: extrae los id relacionados al contrato.
    - contrato_base_id: el otrosi tiene un  contrato principal o padre. Debe tomarse textualmente, si no aparece dejarlo "null".
    - otrosi_id: Identificador del OTROSÍ. Debe ser exactamente como aparece.
- adiciones: las adiciones pueden ser en TIEMPO, VALOR o AMBAS. Detewrminar cual es el nuevo valor según la adición.
    - tipo: Determinar el tipo de adición que realiza el OTROSÍ.  
        Reglas:
            • Si solo modifica la fecha final → "ADICIÓN EN TIEMPO"
            • Si solo agrega o modifica valor económico → "ADICIÓN EN VALOR"
            • Si modifica ambos → "AMBAS"
            • Si no modifica ni tiempo ni valor → "NINGUNA"
    - fecha_fin: Fecha final resultante del contrato después del OTROSÍ.Debe estar explícitamente escrita en el OTROSÍ.Formato: YYYY-MM-DD. Si no aparece, devolver null.
    - valor: Valor económico agregado, ampliado o ajustado por el OTROSÍ en pesos colombianos (COP), si es en otra moneda se debe hacer el cambio según la tasa de cambio. Debe extraerse textualmente (con o sin IVA). Si no aparece explícitamente → devolver null. 
"""
"""
Para las adiciones se debe tener en cuenta que, las fechas y el valor se deben cambiar si tienen otrosi
"""

initial_state: StateEstructure = {
    "input_data": msg,
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
