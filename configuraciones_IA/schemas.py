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