"""Recuperación local sobre los documentos JSON existentes."""

import json
import logging
import re

from config import DOCUMENTS_DIR, PROJECT_DIR
from sources import source_type

logger = logging.getLogger("MycoEngine")


def mentioned_zones(question: str, zones: set[str]) -> set[str]:
    question = question.casefold().replace("andía", "andia").replace("aitzkorri", "aizkorri")
    question = re.sub(r"\baizkorri(?:[\s–-]+aratz)?\b|\baratz\b", "aizkorri-aratz", question)
    return {
        zone for zone in zones
        if re.search(r"\b" + zone.casefold() + r"\b", question)
    }


def passages(names: list[str], limit: int = 8, question: str = "") -> list[dict]:
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
            hit = min(
                (match.start() for pattern in patterns if (match := pattern.search(text))),
                default=None,
            )
            if hit is None:
                continue
            seen.add(url)
            matches.append({
                "url": url,
                "title": document.get("title"),
                "type": kind,
                "excerpt": text[max(0, hit - 250):hit + 850],
            })
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            logger.warning("Documento ilegible: %s", path.name)
    regional = json.loads(
        (PROJECT_DIR / "knowledge" / "regiones" / "navarra.json").read_text(encoding="utf-8")
    )
    named_zones = mentioned_zones(question, {zone for row in regional for zone in row["zones"]} | {"Urdiain"})
    local_matches = [
        row for row in regional
        if (not named_zones or named_zones.intersection(row["zones"]))
        and (named_zones or any(pattern.search(name) for pattern in patterns for name in row["species"]))
    ]
    if named_zones:
        return (local_matches + matches)[:limit]
    return (matches + local_matches)[:limit]
