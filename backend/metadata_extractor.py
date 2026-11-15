import re


def extract_metadata(document: dict) -> dict:
    """
    Extrae metadatos bibliográficos del documento.
    Todos los resultados permanecen sin verificar.
    """

    text = document.get("text", "")
    title = document.get("title")

    if title:
        title = re.sub(
            r'\s*\|\s*[^|]+\s*\|\s*Springer Nature Link$',
            '',
            title
        ).strip()

    url = document.get("url", "")

    metadata = {
        "title": title,
        "url": url,
        "doi": None,
        "authors": [],
        "journal": None,
        "publication_year": None,
        "publication_date": None,
        "license": None,
        "document_type": None,
        "extraction_method": "text_patterns",
        "verification_status": "unverified",
        "evidence": {}
    }

    if not text:
        return metadata

    # 1. DOI: priorizar el DOI de la ficha final del artículo
    doi_matches = list(re.finditer(
        r'https?://doi\.org/(10\.\d{4,9}/[^\s<>]+)',
        text,
        re.IGNORECASE
    ))

    if doi_matches:
        doi = doi_matches[-1].group(1).rstrip(".,;)")
        metadata["doi"] = doi
        metadata["evidence"]["doi"] = doi_matches[-1].group(0)

    else:
        # Alternativa: DOI incluido en la URL original
        url_match = re.search(
            r'/article/(?:doi/)?(10\.\d{4,9}/[^/?#]+)',
            url,
            re.IGNORECASE
        )

        if url_match:
            metadata["doi"] = url_match.group(1)
            metadata["evidence"]["doi"] = url

    # 2. Autores: bloque institucional de Springer
    authors_match = re.search(
        r'\nAuthors\s*\n(.*?)\nContributions\s*\n',
        text,
        re.DOTALL
    )

    if authors_match:
        section = authors_match.group(1)

        names = re.findall(
            r'(?m)^([A-Z][^\n]+?)\s*\nView author publications',
            section
        )

        metadata["authors"] = list(dict.fromkeys(
            name.strip() for name in names
        ))

        metadata["evidence"]["authors"] = section.strip()

    # 3. Revista
    journal_match = re.search(
        r'\b(Mycol(?:ogical)?\s+Progress)\b',
        text,
        re.IGNORECASE
    )

    if journal_match:
        metadata["journal"] = journal_match.group(1)
        metadata["evidence"]["journal"] = journal_match.group(0)

    # 4. Fecha de publicación
    publication_match = re.search(
        r'Published\s*:\s*(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})',
        text
    )

    if publication_match:
        date = publication_match.group(1)

        metadata["publication_date"] = date
        metadata["publication_year"] = int(
            date[-4:]
        )

        metadata["evidence"]["publication_date"] = (
            publication_match.group(0)
        )

    # 5. Licencia
    license_match = re.search(
        r'(Creative Commons Attribution 4\.0 International License)',
        text,
        re.IGNORECASE
    )

    if license_match:
        metadata["license"] = {
            "name": license_match.group(1),
            "identifier": "CC BY 4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/"
        }

        metadata["evidence"]["license"] = (
            license_match.group(0)
        )

    # 6. Tipo documental
    if re.search(r'\bAbstract\b', text, re.IGNORECASE):
        metadata["document_type"] = "scientific_article"

    return metadata

def compare_metadata(local: dict, crossref: dict) -> dict:
    """
    Compara metadatos extraídos del documento
    con los registrados en Crossref.
    """

    def normalize(value):
        return re.sub(
            r'\s+',
            ' ',
            str(value or '')
        ).strip().casefold()

    checks = {
        "doi": (
            normalize(local.get("doi"))
            == normalize(crossref.get("doi"))
        ),
        "title": (
            normalize(local.get("title"))
            == normalize(crossref.get("title"))
        ),
        "authors": (
            [normalize(a) for a in local.get("authors", [])]
            == [normalize(a) for a in crossref.get("authors", [])]
        ),
        "journal": (
            normalize(local.get("journal"))
            == normalize(crossref.get("journal"))
        ),
        "publication_year": (
            local.get("publication_year")
            == crossref.get("publication_year")
        ),
        "license": (
            normalize(
                (local.get("license") or {}).get("url", "")
            ).rstrip("/")
            == normalize(
                (crossref.get("licenses") or [""])[0]
            ).rstrip("/")
        )
    }

    mismatches = [
        field
        for field, matches in checks.items()
        if not matches
    ]

    return {
        "status": "matched" if not mismatches else "mismatch",
        "checks": checks,
        "mismatches": mismatches,
        "fields_checked": len(checks),
        "fields_matched": sum(checks.values())
    }