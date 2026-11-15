import requests
import logging
from urllib.parse import urlparse

from config import TAVILY_API_KEY

logger = logging.getLogger("MycoEngine")

TAVILY_URL = "https://api.tavily.com/search"


def search_web(query: str, max_results: int = 5, domains: tuple[str, ...] = ()) -> list:
    """
    Busca documentación mediante Tavily.
    Elimina URLs duplicadas y normaliza los resultados.
    """

    if not query or not query.strip():
        raise ValueError("La búsqueda no puede estar vacía.")

    if not TAVILY_API_KEY:
        raise RuntimeError("Configura TAVILY_API_KEY para buscar fuentes.")

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query.strip(),
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False
    }

    if domains:
        payload["include_domains"] = list(domains)

    try:
        response = requests.post(
            TAVILY_URL,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        results = []
        seen_urls = set()

        for item in data.get("results", []):

            url = item.get("url", "").strip()

            if not url:
                continue

            # Normalizar URL para detectar duplicados
            parsed = urlparse(url)
            normalized_url = (
                f"{parsed.scheme.lower()}://"
                f"{parsed.netloc.lower()}"
                f"{parsed.path.rstrip('/')}"
            )

            if normalized_url in seen_urls:
                continue

            seen_urls.add(normalized_url)

            results.append({
                "title": item.get("title"),
                "url": url,
                "snippet": item.get("content"),
                "score": item.get("score"),
                "source": parsed.netloc.lower()
            })

        logger.info(
            "Búsqueda completada: %s | Resultados únicos: %s",
            query,
            len(results)
        )

        return results

    except requests.RequestException as error:
        logger.error("Error en búsqueda Tavily: %s", error)
        raise