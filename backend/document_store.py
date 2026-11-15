import json
import hashlib
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from datetime import datetime, timezone

from config import DOCUMENTS_DIR

logger = logging.getLogger("MycoEngine")

def save_document(document: dict) -> dict:
    """
    Guarda un documento extraído en la biblioteca.

    - Comprueba que contiene los campos necesarios.
    - Verifica su hash SHA-256.
    - Evita guardar documentos duplicados.
    - No valida científicamente su contenido.
    """

    required_fields = [
        "url",
        "title",
        "text",
        "content_hash"
    ]

    for field in required_fields:
        if not document.get(field):
            raise ValueError(
                f"Falta un campo obligatorio: {field}"
            )

    text = document["text"]

    # Calcular el hash real del contenido
    calculated_hash = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    if calculated_hash != document["content_hash"]:
        raise ValueError(
            "El hash del documento no coincide con su contenido."
        )

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{calculated_hash}.json"
    destination = DOCUMENTS_DIR / filename

    # Comprobar si el documento ya existe
    if destination.exists():
        logger.info(
            "Documento duplicado: %s",
            document["title"]
        )

        return {
            "saved": False,
            "duplicate": True,
            "path": str(destination),
            "content_hash": calculated_hash
        }

    # Preparar documento para almacenamiento
    stored_document = document.copy()

    stored_document.update({
        "document_id": calculated_hash,
        "stored_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "storage_status": "stored"
    })

    # Escritura temporal para evitar archivos incompletos
    temporary_file = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False
        ) as file:
            temporary_file = Path(file.name)
            json.dump(
                stored_document,
                file,
                ensure_ascii=False,
                indent=2
            )

        temporary_file.replace(destination)

        logger.info(
            "Documento guardado: %s",
            destination
        )

        return {
            "saved": True,
            "duplicate": False,
            "path": str(destination),
            "content_hash": calculated_hash
        }

    except Exception:
        if temporary_file is not None and temporary_file.exists():
            temporary_file.unlink()

        raise