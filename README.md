MycoAI 🍄
Asistente de inteligencia artificial para investigación e identificación
preliminar de especies fúngicas.
Objetivo
Construir una biblioteca micológica documentada y un sistema RAG local
que permita consultar información científica y ecológica durante la
identificación de hongos.

La prioridad es el rigor científico, la trazabilidad de las fuentes
y la seguridad.
Arquitectura prevista
Android
|
| Consulta, GPS e imágenes
v
Backend Python (Linux)
|
| Recuperación de documentación (RAG)
v
Biblioteca micológica
|
| Contexto relevante + instrucciones
v
LM Studio (LLM local)
|
v
Respuesta estructurada a Android

La comunicación remota se realizará mediante Tailscale.
Estructura del proyecto
- SYSTEM_MICOLOGIA.txt: protocolo científico del asistente.
- knowledge/especies/: fichas individuales de especies.
- knowledge/habitats/: información ecológica y de hábitats.
- knowledge/regiones/: información geográfica y distribución.
- knowledge/fuentes/: bibliografía y criterios de documentación.
- backend/: API, recuperación RAG e integración con LM Studio.
- tests/: pruebas y benchmark de identificación.
- logs/: registros técnicos.
- backups/: copias de seguridad.
Principios
1. Fuentes verificables.
2. Separación entre observaciones e hipótesis.
3. Identificación diferencial.
4. Incertidumbre explícita.
5. Distribución geográfica basada en registros.
6. Ninguna autorización automatizada de consumo.
7. Privacidad: procesamiento local siempre que sea posible.
Flujo de consulta
1. Android obtiene la ubicación y recoge la información del ejemplar.
2. El backend recibe la consulta.
3. Se recuperan las fichas y fuentes relevantes.
4. Se construye una petición con contexto científico.
5. LM Studio genera una respuesta.
6. El backend devuelve el resultado a Android.
Estado del desarrollo
- [x] Estructura inicial.
- [x] Protocolo científico.
- [x] Plantilla de fichas.
- [x] Documentación principal.
- [ ] Registro bibliográfico.
- [ ] Primeras fichas verificadas.
- [ ] Biblioteca de hábitats.
- [ ] Biblioteca geográfica.
- [ ] Sistema RAG.
- [ ] Backend Python.
- [ ] Integración Android.
- [ ] Benchmark de evaluación.
Seguridad
MycoAI es una herramienta de apoyo a la identificación.
Nunca sustituye la identificación presencial por una persona experta
y nunca debe autorizar el consumo de un ejemplar.
Motor de biblioteca y API
Instala las dependencias en el entorno de MycoAI con
python -m pip install -r requirements.txt. Configura TAVILY_API_KEY
en el .env existente del backend del HDD o en el entorno. Solo la ingesta
requiere esa clave. MYCOAI_DATA_DIR permite usar otro directorio de datos.

Carga documentación por nombre científico desde la raíz del proyecto.
python backend/ingest.py "Amanita caesarea" "Boletus edulis" --max-sources 8
La ingesta conserva los JSON y contrasta los DOI con Crossref cuando se
encuentran. La recuperación usa coincidencias de nombres científicos sobre
los JSON, con extractos y URL. Comprueba el dominio y, para revistas,
la ruta del artículo. Los documentos fuera de la lista permanecen en disco.
Las coincidencias de Crossref cotejan datos bibliográficos. Los registros
taxonómicos sirven para nomenclatura. Las fuentes pueden tener cobertura
desigual según la especie.

Configura MYCOAI_API_TOKEN con un secreto propio y
MYCOAI_VISION_MODEL con el identificador exacto del modelo multimodal de
LM Studio. MYCOAI_TEXT_MODEL y MYCOAI_LM_URL permiten cambiar el modelo
de texto y su URL. Arranca el backend desde la raíz con la IP Tailscale del PC.
python -m uvicorn api:app --app-dir backend --host IP_TAILSCALE_DEL_PC --port 8765
En SetasAI, cambia la petición directa a LM Studio por
POST http://IP_TAILSCALE_DEL_PC:8765/consult con cabecera
Authorization: Bearer <token> y cuerpo JSON. GET /health comprueba
que el backend responde.
{
  "question": "¿Qué hongos están documentados cerca y en qué hábitats?",
  "species": ["Amanita caesarea"],
  "latitude": 42.89,
  "longitude": -2.14,
  "month": 11
}
Los campos son opcionales. Si se envía GPS se requieren ambas coordenadas y
se consulta GBIF en una ventana de ±0,1° por eje para el mes indicado. Si
falta el mes se usa el actual en España peninsular. Se envía esa ventana a
GBIF. geography indica cuántos registros se muestrearon y si había más.
Los registros agrupan taxones del reino Fungi, incluidos los que pueden
quedar fuera del interés de una salida a por setas.

Para fotos, añade images con hasta cuatro data URLs JPEG o PNG en base64.
El modelo visual propone rasgos e hipótesis y el modelo de texto los coteja
con la biblioteca. La API devuelve answer, sources, geography y
safety. El resultado es orientativo y el GPS aporta evidencia histórica,
sin confirmar presencia actual.
