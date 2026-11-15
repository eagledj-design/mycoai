
import logging

from sources import DOMAINS, source_type
from search_engine import search_web
from content_extractor import extract_content
from document_store import save_document
from metadata_extractor import extract_metadata, compare_metadata
from crossref_client import get_crossref_metadata
from metadata_store import save_metadata

logger = logging.getLogger("MycoEngine")


def research_species(
    species_name: str,
    max_sources: int = 5
) -> dict:
    """
    Investiga una especie mediante búsqueda web,
    extracción documental, almacenamiento y contraste
    de metadatos bibliográficos con Crossref.

    El contraste bibliográfico no valida científicamente
    el contenido del documento.
    """

    if not species_name or not species_name.strip():
        raise ValueError("Debes indicar una especie.")

    species_name = species_name.strip()

    report = {
        "species": species_name,
        "status": "started",
        "search_results": 0,
        "documents_saved": 0,
        "duplicates": 0,
        "metadata_extracted": 0,
        "crossref_matched": 0,
        "crossref_mismatches": 0,
        "crossref_unavailable": 0,
        "crossref_not_applicable": 0,
        "errors": [],
        "documents": []
    }

    logger.info("Iniciando investigación: %s", species_name)

    # 1. Buscar documentación
    query = (
        f'"{species_name}" taxonomy morphology '
        'habitat scientific description'
    )

    try:
        results = search_web(
            query,
            max_results=max_sources, domains=DOMAINS
        )

        report["search_results"] = len(results)

    except Exception as error:
        logger.exception("Error durante la búsqueda")

        report["status"] = "search_failed"
        report["errors"].append({
            "stage": "search",
            "error": str(error)
        })

        return report

    # 2. Descargar, extraer metadatos y almacenar
    for index, result in enumerate(results, 1):

        url = result.get("url")

        if not url:
            continue

        logger.info(
            "Procesando fuente %s/%s: %s",
            index,
            len(results),
            url
        )

        try:
            if not source_type(url):
                continue
            document = extract_content(url, allow_url=source_type)
            document["source_type"] = source_type(document["url"])

            document["search_query"] = query
            document["search_title"] = result.get("title")
            document["search_score"] = result.get("score")

            # 3. Extraer metadatos bibliográficos
            metadata = extract_metadata(document)

            report["metadata_extracted"] += 1

            validation = {
                "status": "not_applicable",
                "reason": "La fuente no contiene un DOI detectable.",
                "checks": {},
                "mismatches": [],
                "fields_checked": 0,
                "fields_matched": 0
            }

            crossref_data = None

            # 4. Contrastar con Crossref si existe DOI
            doi = metadata.get("doi")

            if doi:
                try:
                    crossref_data = get_crossref_metadata(doi)

                    validation = compare_metadata(
                        metadata,
                        crossref_data
                    )

                    if validation["status"] == "matched":
                        report["crossref_matched"] += 1

                    else:
                        report["crossref_mismatches"] += 1

                    logger.info(
                        "Contraste Crossref: %s | %s",
                        doi,
                        validation["status"]
                    )

                except Exception as error:
                    report["crossref_unavailable"] += 1

                    validation["reason"] = (
                        f"No se pudo consultar Crossref: {error}"
                    )

                    logger.warning(
                        "Crossref no disponible para %s: %s",
                        doi,
                        error
                    )

            else:
                report.setdefault("crossref_not_applicable", 0)
                report["crossref_not_applicable"] += 1

            # 5. Incorporar metadatos al documento
            # El hash sigue correspondiendo únicamente al texto.
            document["bibliographic_metadata"] = metadata
            document["crossref_metadata"] = crossref_data
            document["bibliographic_validation"] = validation

            # 6. Almacenar documento
            storage = save_document(document)

            if storage["saved"]:
                report["documents_saved"] += 1

            elif storage["duplicate"]:
                report["duplicates"] += 1

            metadata_storage = save_metadata(
                document=document,
                metadata=metadata,
                crossref_data=crossref_data,
                validation=validation
            )

            report["documents"].append({
                "title": document["title"],
                "url": document["url"],
                "content_length": document["content_length"],
                "content_hash": document["content_hash"],
                "metadata": metadata,
                "crossref_validation": validation,
                "storage": storage,
                "metadata_storage": metadata_storage
            })

        except Exception as error:

            logger.exception(
                "No se pudo procesar la fuente: %s",
                url
            )

            report["errors"].append({
                "url": url,
                "error": str(error)
            })

            continue

    # 7. Estado final
    if report["documents_saved"] > 0 or report["duplicates"] > 0:

        report["status"] = (
            "completed_with_errors"
            if report["errors"]
            else "completed"
        )

    elif report["errors"]:
        report["status"] = "completed_with_errors"

    else:
        report["status"] = "no_documents_found"

    
    logger.info(
        "Investigación finalizada: %s | "
        "Guardados: %s | Duplicados: %s | "
        "Metadatos: %s | Crossref OK: %s | "
        "Discrepancias: %s | No contrastables: %s | "
        "No disponibles: %s | Errores: %s",
        species_name,
        report["documents_saved"],
        report["duplicates"],
        report["metadata_extracted"],
        report["crossref_matched"],
        report["crossref_mismatches"],
        report["crossref_not_applicable"],
        report["crossref_unavailable"],
        len(report["errors"])
    )

    return report
