"""Consulta de observaciones históricas por zona y mes."""

from collections import Counter

import requests


def nearby_fungi(latitude: float, longitude: float, month: int) -> dict:
    # Ventana angular de 0,2° por lado, recortada en polos y antimeridiano.
    south, north = max(-90, latitude - .1), min(90, latitude + .1)
    west, east = max(-180, longitude - .1), min(180, longitude + .1)
    rectangle = f"{west} {south},{east} {south},{east} {north},{west} {north},{west} {south}"
    params = {
        "geometry": f"POLYGON(({rectangle}))",
        "kingdomKey": 5,
        "month": month,
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "occurrenceStatus": "PRESENT",
        "limit": 300,
    }
    response = requests.get("https://api.gbif.org/v1/occurrence/search", params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    counts = Counter()
    examples = {}
    for record in data["results"]:
        name = record.get("species")
        key = record.get("key")
        uncertainty = record.get("coordinateUncertaintyInMeters")
        if name and key and (uncertainty is None or uncertainty <= 5000):
            counts[name] += 1
            examples.setdefault(name, f"https://www.gbif.org/occurrence/{key}")

    return {
        "month": month,
        "sampled": len(data["results"]),
        "truncated": not data.get("endOfRecords", False),
        "candidate_species": [
            {"species": name, "sample_records": count, "example": examples[name]}
            for name, count in counts.most_common(12)
        ],
    }
