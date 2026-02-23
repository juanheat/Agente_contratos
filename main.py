from pipeline import run_pipeline
from utils.pdf_utils import file_to_base64

pdf = file_to_base64("Firmado_Minuta (4).pdf")

r = run_pipeline(pdf_base64= pdf)

