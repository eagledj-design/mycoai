from pathlib import Path
from dotenv import load_dotenv
import os

# ============================================================
# UBICACIONES DEL PROYECTO
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

# Directorio persistente de datos.
# Por defecto, se conserva la ubicación actual en BD_PYTHON.
DATA_DIR = Path(
    os.getenv(
        "MYCOAI_DATA_DIR",
        "/mnt/BD_PYTHON/Proyectos Programacion/MycoAI"
    )
).expanduser().resolve()

# ============================================================
# CREDENCIALES
# ============================================================

# La clave Tavily permanece en el HDD.
ENV_FILE = (
    Path(
        os.getenv(
            "MYCOAI_ENV_FILE",
            str(DATA_DIR / "backend" / ".env")
        )
    )
    .expanduser()
    .resolve()
)

load_dotenv(ENV_FILE)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


# ============================================================
# BIBLIOTECA Y REGISTROS
# ============================================================

KNOWLEDGE_DIR = DATA_DIR / "knowledge"
LOG_DIR = DATA_DIR / "logs"

SPECIES_DIR = KNOWLEDGE_DIR / "especies"
PENDING_DIR = SPECIES_DIR / "pendientes"
SOURCES_DIR = KNOWLEDGE_DIR / "fuentes"

DOCUMENTS_DIR = SOURCES_DIR / "documentos"
METADATA_DIR = SOURCES_DIR / "metadatos"
