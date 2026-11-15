
"""
MYCO ENGINE
Motor de investigación micológica de MycoAI.

Responsabilidades:
- Recibir investigaciones sobre especies.
- Coordinar búsquedas documentales.
- Analizar fuentes mediante LM Studio.
- Preparar fichas provisionales.
- Gestionar el almacenamiento de la biblioteca.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
import logging
import os
import urllib.request
import urllib.error

from search_engine import search_web
from config import (
    DATA_DIR,
    KNOWLEDGE_DIR,
    LOG_DIR,
    SPECIES_DIR,
    PENDING_DIR,
    SOURCES_DIR,
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

LM_STUDIO_URL = os.getenv("MYCOAI_LM_URL", "http://127.0.0.1:1234/v1/chat/completions")

# ============================================================
# REGISTRO DE ACTIVIDAD
# ============================================================

logger = logging.getLogger("MycoEngine")


# ============================================================
# INICIALIZACIÓN
# ============================================================

def initialize():
    """Comprueba y prepara los directorios necesarios."""

    directories = [
        KNOWLEDGE_DIR,
        SPECIES_DIR,
        PENDING_DIR,
        SOURCES_DIR,
        LOG_DIR
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    logger.info("Myco Engine inicializado correctamente.")
    logger.info("Biblioteca: %s", KNOWLEDGE_DIR)


# ============================================================
# REGISTRO DE INVESTIGACIONES
# ============================================================

def create_research_request(species_name: str) -> dict:
    """
    Prepara una solicitud de investigación.

    Todavía no realiza búsquedas ni modifica fichas.
    """

    if not species_name or not species_name.strip():
        raise ValueError("Debes proporcionar un nombre de especie.")

    request = {
        "species": species_name.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "sources": [],
        "validated": False
    }

    logger.info(
        "Solicitud de investigación creada: %s",
        request["species"]
    )

    return request


def ask_lm_studio(prompt: str, system_prompt: str = None, images: tuple[str, ...] = (), model: str | None = None) -> str:
    """
    Envía una petición al modelo local de LM Studio.

    El modelo analiza la información proporcionada.
    Sus respuestas no se consideran conocimiento validado.
    """

    content = prompt
    if images:
        content = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": image}}
            for image in images
        )

    payload = {
        "model": model or os.getenv("MYCOAI_TEXT_MODEL", "mistralai/ministral-3-14b-reasoning"),
        "messages": [
            {
                "role": "system",
                "content": system_prompt or (
                    "Eres un analista documental especializado en micología. "
                    "Trabaja exclusivamente con la documentación proporcionada. "
                    "No inventes fuentes, referencias ni características. "
                    "Distingue los hechos documentados de las hipótesis. "
                    "Si falta información, indícalo. "
                    "Nunca autorices el consumo de hongos."
                )
            },
            {
                "role": "user",
                "content": content
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2500
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        LM_STUDIO_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"]

        logger.info("Respuesta recibida de LM Studio.")

        return content

    except urllib.error.URLError as error:
        logger.error("Error conectando con LM Studio: %s", error)
        raise

    except (KeyError, IndexError, json.JSONDecodeError) as error:
        logger.error("Respuesta inesperada de LM Studio: %s", error)
        raise



# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":

    initialize()
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging.FileHandler(LOG_DIR / "myco_engine.log", encoding="utf-8"),
                  logging.StreamHandler()],
    )

    request = create_research_request("Amanita caesarea")
    print("\nPROBANDO CONEXIÓN CON LM STUDIO...")

    respuesta = ask_lm_studio(
        "Responde únicamente: CONEXIÓN CORRECTA. "
        "No añadas ninguna explicación."
    )

    print("\nRespuesta del modelo:")
    print(respuesta)
    print("\nMYCO ENGINE")
    print("=" * 40)
    print(json.dumps(request, indent=4, ensure_ascii=False))
    print("=" * 40)
    print("Motor preparado correctamente.")
    print("\nPROBANDO BÚSQUEDA WEB CON TAVILY...")

    resultados = search_web(
        "Amanita caesarea morphology taxonomy scientific description",
        max_results=5
    )

    for i, resultado in enumerate(resultados, 1):
        print(f"\n--- RESULTADO {i} ---")
        print("Título:", resultado["title"])
        print("Fuente:", resultado["source"])
        print("URL:", resultado["url"])
        print("Fragmento:", resultado["snippet"][:300])