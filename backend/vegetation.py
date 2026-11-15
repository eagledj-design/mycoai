"""Consulta online y local del Mapa Forestal de España."""

from concurrent.futures import ThreadPoolExecutor
from math import cos, radians

import requests


from config import KNOWLEDGE_DIR

MAPS = KNOWLEDGE_DIR / "vegetacion"
SOURCE = "https://www.miteco.gob.es/es/biodiversidad/temas/inventarios-nacionales/mapa-forestal-espana/mfe_25.html"
WMS_URL = "https://iepnb.gob.es/geoserver/foto_fija_mfe/ff_uso/wms"
WMS_LAYER = "foto_fija_mfe:ff_uso"

TREES = {
    71: "Haya (Fagus sylvatica)",
    72: "Castaño (Castanea sativa)",
}


def describe_species(value) -> str | None:
    if value is None or not str(value).strip():
        return None
    label = str(value).strip()
    try:
        code = int(label)
    except ValueError:
        return label
    return TREES.get(code, f"Especie forestal MFE {code}") if code > 0 else None


def local_forest_nearby(latitude: float, longitude: float, radius_m: int = 2000) -> dict | None:
    files = sorted(MAPS.rglob("*.shp"))
    if not files:
        return None

    import fiona
    from pyproj import CRS, Transformer
    from shapely.geometry import Point, shape
    from shapely.ops import transform

    local = CRS.from_proj4(f"+proj=aeqd +lat_0={latitude} +lon_0={longitude} +datum=WGS84 +units=m")
    circle = Point(0, 0).buffer(radius_m)
    species = set()
    land_cover = set()
    covered = False
    for path in files:
        with fiona.open(path) as layer:
            fields = {name.upper(): name for name in layer.schema["properties"]}
            if "SP1" not in fields or not layer.crs:
                continue
            to_layer = Transformer.from_crs(local, layer.crs, always_xy=True)
            to_local = Transformer.from_crs(layer.crs, local, always_xy=True)
            bbox = to_layer.transform_bounds(*circle.bounds)
            for feature in layer.filter(bbox=bbox):
                geometry = feature.geometry
                if geometry is None or not transform(to_local.transform, shape(geometry)).intersects(circle):
                    continue
                covered = True
                properties = feature.properties
                for field in ("SP1", "SP2", "SP3"):
                    name = describe_species(properties.get(fields.get(field, field)))
                    if name:
                        species.add(name)
                for field in ("TIPOBOSQUE", "TIPOESTR"):
                    value = properties.get(fields.get(field, field))
                    if isinstance(value, str) and value.strip() and not value.strip().isdigit():
                        land_cover.add(value.strip())
    if not covered:
        return None
    return {"radius_m": radius_m, "tree_species": sorted(species),
            "land_cover": sorted(land_cover), "source": SOURCE}


def forest_point(latitude: float, longitude: float) -> list[dict]:
    delta = .0005
    response = requests.get(WMS_URL, params={
        "service": "WMS", "version": "1.1.1", "request": "GetFeatureInfo",
        "layers": WMS_LAYER, "query_layers": WMS_LAYER,
        "srs": "EPSG:4326", "styles": "", "format": "image/png",
        "bbox": f"{longitude-delta},{latitude-delta},{longitude+delta},{latitude+delta}",
        "width": 101, "height": 101, "x": 50, "y": 50,
        "info_format": "application/json", "feature_count": 1,
    }, timeout=(2, 3))
    response.raise_for_status()
    return [feature["properties"] for feature in response.json()["features"]]


def online_forest_nearby(latitude: float, longitude: float, radius_m: int) -> dict | None:
    # Muestrea el centro y ocho puntos del entorno, sin descargar geometrías.
    latitude_step = radius_m / (111_320 * 2 ** .5)
    longitude_step = latitude_step / cos(radians(latitude))
    points = [
        (latitude + row * latitude_step, longitude + col * longitude_step)
        for row in (-1, 0, 1) for col in (-1, 0, 1)
    ]
    species, land_cover = set(), set()
    checked = 0
    with ThreadPoolExecutor(max_workers=len(points)) as pool:
        futures = [pool.submit(forest_point, *point) for point in points]
        for future in futures:
            try:
                features = future.result()
            except (requests.RequestException, KeyError, TypeError, ValueError):
                continue
            checked += 1
            for raw in features:
                fields = {key.upper(): value for key, value in raw.items()}
                for field in ("SP1", "SP2", "SP3"):
                    name = describe_species(fields.get(field))
                    if name:
                        species.add(name)
                for field in ("TIPOBOSQUE", "TIPOESTR", "FORMACION", "USO"):
                    value = fields.get(field)
                    if isinstance(value, str) and value.strip() and not value.strip().isdigit():
                        land_cover.add(value.strip())
    if not species and not land_cover:
        return None
    return {
        "radius_m": radius_m, "tree_species": sorted(species),
        "land_cover": sorted(land_cover), "source": SOURCE,
        "origin": "mfe25_wms", "points_checked": checked, "points_total": len(points),
    }


def forest_nearby(latitude: float, longitude: float, radius_m: int = 2000) -> dict | None:
    # Evita peticiones para coordenadas fuera de los entornos de cobertura españoles.
    if ((35 <= latitude <= 44 and -10 <= longitude <= 5)
            or (27 <= latitude <= 30 and -19 <= longitude <= -13)):
        online = online_forest_nearby(latitude, longitude, radius_m)
        if online:
            return online
    return local_forest_nearby(latitude, longitude, radius_m)
