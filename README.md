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

### Cobertura nacional y fecha

En GBIF, solicita una descarga de ocurrencias en formato CSV simple
(`SIMPLE_CSV`) con país España, reino Fungi, presencia, coordenadas
disponibles y sin problemas geoespaciales. La descarga incluye los
registros publicados que coincidan con los filtros, con cobertura desigual
entre lugares y fechas. Descarga el ZIP y conserva el DOI de GBIF.

```bash
python backend/national_records.py /ruta/a/descarga-gbif.zip --doi 10.15468/dl.TU_CODIGO
```

El importador conserva cada registro como JSON en un índice SQLite
ubicado en `knowledge/gbif/` dentro del directorio de datos. Repetir la
importación actualiza por identificador de GBIF. El índice alimenta
consultas GPS. Para ampliar la documentación por especie, se mantiene
`backend/ingest.py` con las fuentes autorizadas.

En Android puedes añadir `observation_date` al JSON de `POST /consult`
con la fecha local en formato ISO (por ejemplo, `"2026-11-15"`). Si falta,
el servidor usa el día actual en la zona Europe/Madrid. Las peticiones
que envían explícitamente solo `month` conservan el filtro mensual.

Con fecha completa se buscan observaciones históricas de los 15 días
anteriores y posteriores a ese día del calendario, en cualquier año.
Si el índice no tiene coincidencias se consulta GBIF en directo.
`geography.origin` indica qué fuente se usó y `geography.truncated`
indica si la consulta muestreó una parte de los registros.

Añade `--document-species 20` al comando de importación para buscar y
guardar también artículos de hasta 20 especies del índice. Prioriza las
más representadas en la descarga, omite las que ya tienen un artículo
recuperable y requiere la clave Tavily.

### Vegetación alrededor del GPS

Instala `python -m pip install -r requirements-vegetation.txt` y descarga
la cartografía provincial del Mapa Forestal de España (MFE25) desde
[MITECO](https://www.miteco.gob.es/es/biodiversidad/servicios/banco-datos-naturaleza/informacion-disponible/informacion_situacion_actual_mfe25_50.html).
Extrae los shapefiles completos (incluidos .dbf, .shx y .prj) en
`knowledge/vegetacion/` dentro del directorio de datos de MycoAI en
BD_PYTHON. Puedes usar subcarpetas por provincia.

El backend consulta las teselas MFE25 con campos SP1–SP3 a 2 km del
GPS. Muestra los árboles registrados en esas teselas en la respuesta y
en el campo opcional `vegetation`. Los códigos sin nombre incorporado
se muestran como códigos MFE. La cartografía se procesa en local.

MycoAI intenta primero consultar online el WMS del Mapa Forestal de
España. Envía el GPS al servicio del MITECO y muestrea nueve puntos
en un radio aproximado de 2 km. La respuesta muestra las especies y la
cobertura que el servicio publique en los atributos. El muestreo puede
omitir manchas pequeñas. Si el servicio no aporta datos utilizables, se
intenta leer la cartografía local si está instalada.
