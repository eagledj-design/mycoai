"""Importa y consulta registros españoles de una descarga SIMPLE_CSV de GBIF."""

import argparse
import csv
import io
import json
import sqlite3
import sys
from contextlib import closing
from datetime import date
from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile

from config import KNOWLEDGE_DIR

DATABASE = KNOWLEDGE_DIR / "gbif" / "es.sqlite3"


def import_download(archive: Path, doi: str) -> int:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as bundle, closing(sqlite3.connect(DATABASE)) as db:
        member, = [name for name in bundle.namelist() if name.lower().endswith(".csv")]
        db.execute("""CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY, latitude REAL, longitude REAL,
            year_day INTEGER, record TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS by_date_lat ON records(year_day, latitude)")
        total = 0
        with bundle.open(member) as binary, io.TextIOWrapper(binary, encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            required = {"gbifID", "countryCode", "kingdom", "species", "decimalLatitude",
                        "decimalLongitude", "month", "day"}
            if not required.issubset(reader.fieldnames or ()):
                raise ValueError("Se requiere una descarga GBIF SIMPLE_CSV con coordenadas y fecha.")
            for row in reader:
                if row["countryCode"] != "ES" or row["kingdom"] != "Fungi" or not row["species"]:
                    continue
                if row.get("occurrenceStatus") not in (None, "", "PRESENT", "DETECTED"):
                    continue
                try:
                    key = int(row["gbifID"])
                    lat, lon = float(row["decimalLatitude"]), float(row["decimalLongitude"])
                    month, day = int(row["month"]), int(row["day"])
                    date(2000, month, day)
                    uncertainty = row.get("coordinateUncertaintyInMeters")
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        continue
                    if uncertainty and not 0 <= float(uncertainty) <= 5000:
                        continue
                except (ValueError, TypeError):
                    continue
                record = {field: row.get(field) for field in (
                    "species", "eventDate", "basisOfRecord", "datasetKey", "license",
                    "coordinateUncertaintyInMeters",
                )}
                record.update(key=key, month=month, day=day, download_doi=doi)
                db.execute("INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?, ?)",
                           (key, lat, lon, month * 100 + day, json.dumps(record, ensure_ascii=False)))
                total += 1
                if total % 5000 == 0:
                    db.commit()
                    print(f"{total:,} registros importados", flush=True)
            db.commit()
        return total


def species_names() -> tuple[str, ...]:
    if not DATABASE.is_file():
        return ()
    return _species_names(DATABASE, DATABASE.stat().st_mtime_ns)


@lru_cache(maxsize=1)
def _species_names(database: Path, modified_ns: int) -> tuple[str, ...]:
    with closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as db:
        return tuple(name for name, in db.execute(
            "SELECT DISTINCT json_extract(record, '$.species') FROM records"
        ) if name)


def records_nearby(bounds: tuple, days: set[tuple[int, int]]) -> list[tuple[str, int, int]]:
    if not DATABASE.is_file():
        return []
    south, north, west, east = bounds
    keys = sorted(month * 100 + day for month, day in days)
    placeholders = ",".join("?" for _ in keys)
    with closing(sqlite3.connect(f"{DATABASE.as_uri()}?mode=ro", uri=True)) as db:
        rows = db.execute(
            f"""SELECT json_extract(record, '$.species') AS species, COUNT(*), MIN(id)
                FROM records WHERE year_day IN ({placeholders})
                AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?
                GROUP BY species ORDER BY COUNT(*) DESC, species""",
            (*keys, south, north, west, east),
        )
        return rows.fetchall()


def document_species(limit: int) -> None:
    from library import passages
    from research_pipeline import research_species

    with closing(sqlite3.connect(f"{DATABASE.as_uri()}?mode=ro", uri=True)) as db:
        candidates = db.execute(
            """SELECT json_extract(record, '$.species') AS name FROM records
               GROUP BY name ORDER BY COUNT(*) DESC, name"""
        ).fetchall()
    researched = 0
    for name, in candidates:
        if any(row["type"] == "revista" for row in passages([name])):
            continue
        report = research_species(name)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        researched += 1
        if report["status"] == "search_failed":
            raise SystemExit("Falló la búsqueda. Revisa la configuración de Tavily.")
        if researched >= limit:
            break


if __name__ == "__main__":
    # GBIF exports can contain long text fields even in rows we skip.
    csv.field_size_limit(sys.maxsize)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--doi", required=True, help="DOI de la descarga de GBIF")
    parser.add_argument("--document-species", type=int, choices=range(1, 101),
                        metavar="1-100", help="Busca también bibliografía de hasta N especies")
    args = parser.parse_args()
    print(f"{import_download(args.archive, args.doi):,} registros procesados")
    if args.document_species:
        document_species(args.document_species)
