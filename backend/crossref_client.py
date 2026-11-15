
import logging
import requests

logger = logging.getLogger("MycoEngine")

CROSSREF_API = "https://api.crossref.org/works"


def get_crossref_metadata(doi: str) -> dict:
    """
    Consulta Crossref mediante DOI y devuelve
    los metadatos bibliográficos registrados.

    No valida la calidad científica del artículo.
    """

    if not doi or not doi.strip():
        raise ValueError("Debes indicar un DOI.")

    doi = doi.strip()

    url = f"{CROSSREF_API}/{doi}"

    headers = {
        "User-Agent": (
            "MycoAI/1.0 "
            "(scientific metadata verification)"
        )
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()["message"]

    except requests.RequestException:
        logger.exception(
            "Error consultando Crossref para DOI: %s",
            doi
        )
        raise

    except (ValueError, KeyError, TypeError):
        logger.exception(
            "Respuesta inesperada de Crossref para DOI: %s",
            doi
        )
        raise

    authors = [
        f"{author.get('given', '')} {author.get('family', '')}".strip()
        for author in data.get("author", [])
    ]

    published = (
        data.get("published-print")
        or data.get("published-online")
        or data.get("published")
    )

    publication_date = None
    publication_year = None

    if published and published.get("date-parts"):
        date_parts = published["date-parts"][0]

        if date_parts:
            publication_year = date_parts[0]

            if len(date_parts) >= 3:
                publication_date = (
                    f"{date_parts[2]:02d}/"
                    f"{date_parts[1]:02d}/"
                    f"{date_parts[0]}"
                )
            elif len(date_parts) == 2:
                publication_date = (
                    f"{date_parts[1]:02d}/"
                    f"{date_parts[0]}"
                )
            else:
                publication_date = str(date_parts[0])

    licenses = [
        license_data.get("URL")
        for license_data in data.get("license", [])
        if license_data.get("URL")
    ]

    return {
        "doi": data.get("DOI"),
        "title": (
            data.get("title", [None])[0]
            if data.get("title")
            else None
        ),
        "authors": authors,
        "journal": (
            data.get("container-title", [None])[0]
            if data.get("container-title")
            else None
        ),
        "publication_year": publication_year,
        "publication_date": publication_date,
        "document_type": data.get("type"),
        "licenses": list(dict.fromkeys(licenses)),
        "source": "Crossref",
        "verification_status": "crossref_retrieved"
    }
