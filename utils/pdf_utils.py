import base64
from pypdf import PdfReader, PdfWriter
import io

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