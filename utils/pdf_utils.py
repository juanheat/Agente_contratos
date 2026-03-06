import base64
import io
import fitz  # PyMuPDF

import tempfile
import subprocess
import mimetypes
import os



def convertir_a_pdf_base64(file_base64: str, filename: str) -> str:
    """
    Convierte cualquier archivo (en base64) a PDF (en base64), todo en memoria.
    No guarda nada en disco.
    """
    file_bytes = base64.b64decode(file_base64)
    extension = filename.rsplit(".", 1)[-1].lower()
    
    doc = fitz.open(stream=file_bytes, filetype=extension)
    pdf_bytes = doc.convert_to_pdf()
    doc.close()
    
    return base64.b64encode(pdf_bytes).decode("utf-8")


def extraer_paginas(pdf_base64: str, num_paginas: int = 3, filename: str = "archivo.pdf") -> str:
    """
    Extrae las primeras N páginas. Si el archivo no es PDF, lo convierte primero.
    Entrada y salida en base64, sin tocar el disco.
    """
    extension = filename.rsplit(".", 1)[-1].lower()

    # Si no es PDF, convertir primero
    if extension != "pdf":
        pdf_base64 = convertir_a_pdf_base64(pdf_base64, filename)

    pdf_bytes = base64.b64decode(pdf_base64)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    new_doc = fitz.open()
    for i in range(min(num_paginas, len(doc))):
        new_doc.insert_pdf(doc, from_page=i, to_page=i)

    output_buffer = new_doc.tobytes()
    return base64.b64encode(output_buffer).decode("utf-8")




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


def base64_a_pdf(base64_str, ruta_salida):
    # Decodifica el base64
    pdf_bytes = base64.b64decode(base64_str)
    
    # Guarda el archivo en formato binario
    with open(ruta_salida, "wb") as f:
        f.write(pdf_bytes)

    print(f"PDF guardado en: {ruta_salida}")
    
    