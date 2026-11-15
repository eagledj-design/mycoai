
import requests
import logging
import hashlib

from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

logger = logging.getLogger("MycoEngine")


def extract_content(url: str, allow_url=None) -> dict:
    """
    Descarga una página web y extrae su contenido textual.

    Detecta páginas de bloqueo y desafíos anti-bots.
    No interpreta ni valida científicamente la información.
    """

    if not url:
        raise ValueError("La URL está vacía.")

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("URL no válida.")

    headers = {
        "User-Agent": (
            "MycoAI Research Bot/1.0 "
            "(scientific mycology research)"
        )
    }

    try:
        for _ in range(5):
            if allow_url and not allow_url(url):
                raise ValueError("Origen fuera de la lista de fuentes documentales.")
            response = requests.get(
                url, headers=headers, timeout=30, allow_redirects=False
            )
            if not response.is_redirect:
                break
            url = urljoin(url, response.headers["Location"])
        else:
            raise ValueError("Demasiadas redirecciones.")

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if "text/html" not in content_type:
            raise ValueError(
                f"Contenido no compatible: {content_type}"
            )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Detectar páginas de bloqueo y desafíos anti-bots
        page_text = soup.get_text(
            " ",
            strip=True
        ).casefold()

        challenge_markers = [
            "client challenge",
            "checking your browser",
            "verify you are human",
            "enable javascript and cookies",
            "security verification"
        ]

        if any(
            marker in page_text
            for marker in challenge_markers
        ):
            raise ValueError(
                f"Página bloqueada por un sistema anti-bots: {url}"
            )

        # Eliminar elementos que no aportan contenido documental
        for element in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form"
        ]):
            element.decompose()

        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title else None
        )

        # Extraer el texto principal
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.body
        )

        if main is None:
            raise ValueError(
                "No se encontró contenido textual."
            )

        text = main.get_text(
            separator="\n",
            strip=True
        )

        # Limpiar líneas vacías repetidas
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        clean_text = "\n".join(lines)

        if len(clean_text) < 200:
            raise ValueError(
                "La página contiene muy poco texto útil."
            )

        # Calcular hash del contenido limpio
        content_hash = hashlib.sha256(
            clean_text.encode("utf-8")
        ).hexdigest()

        document = {
            "url": response.url,
            "domain": urlparse(
                response.url
            ).netloc.lower(),
            "title": title,
            "text": clean_text,
            "retrieved_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "content_length": len(clean_text),
            "content_hash": content_hash,
            "status": "extracted"
        }

        logger.info(
            "Documento extraído: %s | %s caracteres",
            document["domain"],
            document["content_length"]
        )

        return document

    except requests.RequestException as error:
        logger.error(
            "Error descargando %s: %s",
            url,
            error
        )
        raise

    except ValueError as error:
        logger.warning(
            "No se pudo extraer contenido de %s: %s",
            url,
            error
        )
        raise
