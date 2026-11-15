"""Consulta de observaciones históricas por proximidad y fecha."""

from collections import Counter
from datetime import date, timedelta

import requests

from national_records import records_nearby


def calendar_days(month: int, day: int | None) -> set[tuple[int, int]]:
    if day is None:
        from calendar import monthrange
        return {(month, value) for value in range(1, monthrange(2000, month)[1] + 1)}
    center = date(2000, month, day)
    window = [center + timedelta(days=offset) for offset in range(-15, 16)]
    return {(value.month, value.day) for value in window}


def nearby_fungi(latitude: float, longitude: float, month: int, day: int | None = None, *, genus: str | None = None) -> dict:
    south, north = max(-90, latitude - .1), min(90, latitude + .1)
    west, east = max(-180, longitude - .1), min(180, longitude + .1)
    bounds = south, north, west, east
    days = calendar_days(month, day)
    local_counts = records_nearby(bounds, days)
    records = []
    examined = sum(count for _, count, _ in local_counts)
    truncated = False
    origin = "gbif_local"
    if not local_counts:
        origin = "gbif_api"
        rectangle = f"{west} {south},{east} {south},{east} {north},{west} {north},{west} {south}"
        for relevant_month in sorted({value[0] for value in days}):
            response = requests.get("https://api.gbif.org/v1/occurrence/search", params={
                "geometry": f"POLYGON(({rectangle}))",
                "kingdomKey": 5,
                "month": relevant_month,
                "hasCoordinate": "true",
                "hasGeospatialIssue": "false",
                "occurrenceStatus": "PRESENT",
                "limit": 300,
            }, timeout=20)
            response.raise_for_status()
            data = response.json()
            examined += len(data["results"])
            truncated = truncated or not data.get("endOfRecords", False)
            records.extend(
                item for item in data["results"]
                if day is None or (item.get("month"), item.get("day")) in days
            )

    counts = Counter({name: count for name, count, _ in local_counts})
    examples = {name: f"https://www.gbif.org/occurrence/{key}" for name, _, key in local_counts}
    seen = set()
    for record in records:
        name = record.get("species")
        key = record.get("key")
        uncertainty = record.get("coordinateUncertaintyInMeters")
        if name and key and key not in seen and (not uncertainty or float(uncertainty) <= 5000):
            seen.add(key)
            counts[name] += 1
            examples.setdefault(name, f"https://www.gbif.org/occurrence/{key}")

    if genus:
        counts = Counter({
            name: count for name, count in counts.items()
            if name.split()[0].casefold() == genus.casefold()
        })

    return {
        "genus": genus,
        "month": month,
        "day": day,
        "window_days": 15 if day is not None else None,
        "origin": origin,
        "sampled": examined,
        "truncated": truncated,
        "species_count": len(counts),
        "candidate_species": [
            {"species": name, "sample_records": count, "example": examples[name]}
            for name, count in counts.most_common(12)
        ],
    }
