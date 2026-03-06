from pipeline_ai import run_pipeline
from utils.pdf_utils import file_to_base64, extraer_paginas
import logging
import sys
# pip install google-cloud-aiplatform langchain-google-vertexai langchain
# gcloud auth application-default login

# crear txt con librerias
# py -m pip freeze > requirements.txt

#instalar dependencias
# py -m pip install -r requirements.txt


# 1. Eliminar handlers previos (limpia lo que configuró google/httpx)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# 2. Configurar logging desde cero
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(name)s: %(message)s"
)

# 3. Silenciar ruido de librerías externas
for noisy in ["httpx", "google", "grpc", "urllib3", "absl"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)



pdf = file_to_base64("contratos\CW2370068.pdf")

pdf = extraer_paginas(pdf, num_paginas=3, filename="CW2370068.pdf")

r = run_pipeline(pdf_base64= pdf,
                max_attempts= 2,
                llm_kwargs= {"model": "gemini-2.5-flash",
                "project": "gcp-sura-auditoria-eps",
                "temperature": 0,
                "max_tokens": 4300,
                "thinking_budget": 0,})

