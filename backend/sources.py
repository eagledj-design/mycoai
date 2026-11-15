"""Política de fuentes para la biblioteca documental."""

from urllib.parse import urlsplit

DOMAINS = (
    "mycokeys.pensoft.net",
    "imafungus.biomedcentral.com",
    "link.springer.com",
    "mycobank.org",
    "indexfungorum.org",
)


def source_type(url: str) -> str | None:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port not in (None, 443)):
        return None
    host = (parsed.hostname or "").removeprefix("www.")
    if host in ("mycobank.org", "indexfungorum.org"):
        return "registro_taxonomico"
    if host == "mycokeys.pensoft.net" and parsed.path.startswith("/article/"):
        return "revista"
    if host == "imafungus.biomedcentral.com" and parsed.path.startswith("/articles/"):
        return "revista"
    if host == "link.springer.com" and parsed.path.startswith("/article/10.1007/s11557-"):
        return "revista"
    return None
