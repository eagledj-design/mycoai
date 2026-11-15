"""Carga manual de fuentes documentales por nombre científico."""

import argparse
import json
import logging

from research_pipeline import research_species


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("species", nargs="+", help="Nombres científicos entre comillas.")
    parser.add_argument("--max-sources", type=int, choices=range(1, 21), default=5)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    reports = [research_species(name, args.max_sources) for name in args.species]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    raise SystemExit(int(any(not report["documents"] for report in reports)))
