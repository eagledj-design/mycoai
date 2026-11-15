
import json
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from datetime import datetime, timezone

from config import METADATA_DIR

logger = logging.getLogger("MycoEngine")


def save_metadata(
    document: dict,
    metadata: dict,
    crossref_data: dict | None = None,
    validation: dict | None = None
) -> dict:
    """
    Guarda los metadatos bibliográficos en un JSON independiente.

    El documento original no se modifica.
    Cada registro se identifica mediante el hash del documento.
    """

    document_hash = document.get("content_hash")

    if not document_hash:
        raise ValueError(
            "El documento no contiene content_hash."
        )

    METADATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    metadata_path = METADATA_DIR / f"{document_hash}.json"

    record = {
        "document_hash": document_hash,
        "document_url": document.get("url"),
        "document_title": document.get("title"),
        "metadata": metadata,
        "crossref_metadata": crossref_data,
        "bibliographic_validation": validation,
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "storage_status": "stored"
    }

    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=metadata_path.parent, delete=False
        ) as file:
            temporary_path = Path(file.name)
            json.dump(
                record,
                file,
                ensure_ascii=False,
                indent=2
            )

            file.flush()

        temporary_path.replace(metadata_path)

    except Exception:
        logger.exception(
            "Error guardando metadatos para %s",
            document_hash
        )

        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

        raise

    logger.info(
        "Metadatos almacenados: %s",
        metadata_path.name
    )

    return {
        "saved": True,
        "path": str(metadata_path),
        "document_hash": document_hash
    }
