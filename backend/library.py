"""Recuperación local sobre los documentos JSON existentes."""

import json
import logging
import re
import unicodedata

from config import DOCUMENTS_DIR, PROJECT_DIR
from national_records import species_names
from sources import source_type

logger = logging.getLogger("MycoEngine")


def mentioned_zones(question: str, zones: set[str]) -> set[str]:
    question = question.casefold().replace("andía", "andia").replace("aitzkorri", "aizkorri")
    question = re.sub(r"\baizkorri(?:[\s–-]+aratz)?\b|\baratz\b", "aizkorri-aratz", question)
    return {
        zone for zone in zones
        if re.search(r"\b" + zone.casefold() + r"\b", question)
    }


def normalize_name(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.casefold())
                   if not unicodedata.combining(char))


def common_name_match(document: dict, question: str) -> str | None:
    if source_type(document["url"]) != "ficha_micologica":
        return None
    heading = document["title"].partition("|")[0].partition(" - ")[0].strip()
    if not re.fullmatch(r"[A-Z][a-z]+ [a-z][a-z-]+", heading):
        return None
    common_names = re.findall(
        r"^En castellano:[ \t]*\n([^\n]+)|\bCast\.:[ \t]*([^;\n]+)",
        document["text"], re.I | re.M,
    )
    aliases = [normalize_name(alias.strip()) for pair in common_names for part in pair
               for alias in part.split(",") if alias.strip()]
    if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", normalize_name(question)) for alias in aliases):
        return heading
    return None


def species_evidence(question: str, explicit_names: list[str]) -> tuple[list[str], list[dict]]:
    requested = " ".join([question, *explicit_names]).casefold()
    words = re.findall(r"[^\W\d_]+", requested)
    phrases = {f"{first} {second}" for first, second in zip(words, words[1:])}
    names = list(explicit_names)
    profiles = []
    for path in sorted((PROJECT_DIR / "knowledge" / "especies").glob("*.json")):
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
            if profile.get("type") != "ficha_especie":
                continue
            terms = profile["species"] + profile.get("aliases", [])
            if any(re.search(r"(?<!\w)" + re.escape(term.casefold()) + r"(?!\w)", requested)
                   for term in terms):
                profiles.append(profile)
                names.extend(profile["species"])
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            logger.warning("Ficha ilegible: %s", path.name)
    names.extend(name for name in species_names() if name.casefold() in phrases)
    # Aprovecha los nombres castellanos declarados en las fichas ya descargadas.
    for path in sorted(DOCUMENTS_DIR.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            name = common_name_match(document, requested)
            if name:
                names.append(name)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            logger.warning("No se pudieron leer los nombres populares de %s", path.name)
    return list(dict.fromkeys(names)), profiles


def descriptive_excerpt(text: str) -> str:
    if "Texto de descripción" in text:
        text = text.split("Texto de descripción", 1)[1]
        text = re.split(r"^[ \t]*(?:Bibliografía|Nombres populares|Sinonímias)[ \t]*$", text,
                        maxsplit=1, flags=re.I | re.M)[0]
    headings = re.compile(
        r"^(Basidioma|Sombrero|Himenóforo|Pie|Carne|Hábitat|Ecología|"
        r"Caracteres macroscópicos|Caracteres microscópicos|Microscopía|"
        r"Distribución|Comestibilidad|Toxicidad|Confusiones|Bibliografía)"
        r"\s*:?[ \t]*(.*)$", re.I | re.M
    )
    matches = list(headings.finditer(text))
    allowed = {"basidioma", "sombrero", "himenóforo", "pie", "carne",
               "hábitat", "ecología", "caracteres macroscópicos"}
    sections = []
    for index, match in enumerate(matches):
        if match[1].casefold() not in allowed:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = " ".join((match[2] + " " + text[match.end():end]).split()).lstrip(". ")
        if content:
            sections.append(f"{match[1]}: {content[:780]}")
    return "\n".join(sections)


def passages(
    names: list[str], limit: int = 8, question: str = "", *, location_scoped: bool = False
) -> list[dict]:
    patterns = [
        re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, name.split())) + r"(?!\w)", re.I)
        for name in names if name.strip()
    ]
    matches = []
    seen = set()
    for path in sorted(DOCUMENTS_DIR.glob("*.json")) if patterns else ():
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            url = document["url"]
            text = document["text"]
            kind = source_type(url)
            if not kind or url in seen:
                continue
            if location_scoped and not any(
                pattern.search(document.get("title") or "") for pattern in patterns
            ):
                continue
            hit = min(
                (match.start() for pattern in patterns if (match := pattern.search(text))),
                default=None,
            )
            if hit is None:
                continue
            seen.add(url)
            description = descriptive_excerpt(text) if kind == "ficha_micologica" else ""
            matches.append({
                "url": url,
                "title": document.get("title"),
                "type": kind,
                "excerpt": description or text[max(0, hit - 250):hit + 850],
                **({"description": description} if description else {}),
            })
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            logger.warning("Documento ilegible: %s", path.name)
    regional = json.loads(
        (PROJECT_DIR / "knowledge" / "regiones" / "navarra.json").read_text(encoding="utf-8")
    )
    named_zones = mentioned_zones(question, {zone for row in regional for zone in row["zones"]} | {"Urdiain"})
    if location_scoped and not named_zones:
        return matches[:limit]
    local_matches = [
        row for row in regional
        if (not named_zones or named_zones.intersection(row["zones"]))
        and (named_zones or any(pattern.search(name) for pattern in patterns for name in row["species"]))
    ]
    if named_zones:
        return (local_matches + matches)[:limit]
    return (matches + local_matches)[:limit]
