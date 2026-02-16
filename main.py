# pip install google-cloud-aiplatform langchain-google-vertexai langchain
# gcloud auth application-default login
from langchain.agents import create_agent
from langchain_google_genai import (ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory)
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import HumanMessage

import base64

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


SYSTEM_PROMPT = """
Eres un asistente especializado en análisis y extracción de información desde documentos
de cualquier tipo (contratos, historias clínicas, certificados, facturas, reportes, etc.).
Tu objetivo es extraer datos estructurados sin inventar información. 
"""

# Responde únicamente en JSON.
# Si algo no aparece, responde deja el campo null. 

SCHEMA_OUTPUT = {}

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    project="gcp-sura-auditoria-eps",
    temperature= 0,
    max_tokens=4300,
    timeout=None,
    max_retries=2,
    thinking_budget= 0,
    response_format ={'type': 'application/json'},
    safety_settings={
        HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    },
)

agent = create_agent(
    llm,
    system_prompt=SYSTEM_PROMPT
    #response_format=ToolStrategy(SCHEMA_OUTPUT)
)
 

# From base64 data
msg = {"messages":[{
    "role": "user",
    "content": [
        {"type": "text", "text": "Extrae la información que consideres más relevante extraer de este contrato y entregalo en un json. maximo 5 llaves."},
        {
            "type": "file",
            "base64": pdf,
            "mime_type": "application/pdf",
        },
    ]
}]}


result = agent.invoke(msg)



print(result)














