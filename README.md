# 🛡️ Aseguradora del Sur — Prototipo Antifraude Agéntico

Sistema agéntico híbrido diseñado para la detección de posibles fraudes en siniestros, asignación de score de riesgo mediante semáforos, auditoría técnica de facturas y asistencia interactiva mediante IA para la Unidad Antifraude de Aseguradora del Sur.

---

## 1. Resumen Ejecutivo
Este prototipo presenta una solución integral para mitigar el fraude en reclamaciones de seguros. Combina un **Motor de Reglas Determinísticas** (para validación de pólizas, deducibles, vigencias y facturas), un **Motor de Scoring de Fraude** (que evalúa 14 señales ponderadas y 7 reglas de negocio críticas) y un **Agente Conversacional Híbrido** (DeepSeek / Gemini) para auditoría interactiva de casos. La interfaz web responsive integra animaciones fluidas y widgets colapsables para ofrecer una experiencia premium y optimizada.

---

## 2. Planteamiento del Problema
Las aseguradoras enfrentan pérdidas millonarias debido a reclamaciones fraudulentas, que van desde inconsistencias documentales leves hasta patrones complejos como:
- Siniestros reportados inmediatamente después de contratar la póliza o antes de vencerse (borde de vigencia).
- Frecuencias atípicas de reclamos por parte del mismo asegurado, conductor o vehículo.
- Sobrecobros de talleres mecánicos y facturación de repuestos no relacionados con el siniestro.
- Clonación de descripciones físicas del incidente (narrativas coincidentes).

El análisis manual de estos factores es lento, costoso y propenso a errores, lo que justifica una automatización agéntica explicable que actúe como alerta temprana para los revisores humanos.

---

## 3. Objetivos
- **Automatizar el filtrado**: Procesar el 100% de las facturas y siniestros de forma instantánea.
- **Calcular Score de Riesgo**: Ponderar 14 señales de fraude para clasificar casos en un semáforo (Verde, Amarillo, Rojo).
- **Garantizar Explicabilidad**: Acompañar cada alerta con una justificación clara basada en datos facturales y narrativas detalladas.
- **Asistir en Lenguaje Natural**: Proveer un chatbot cognitivo capaz de responder consultas complejas sobre la base de datos de siniestros.

---

## 4. Alcance
El alcance de este prototipo abarca:
1. Ingestión y estructuración de pólizas, vehículos, asegurados, documentos y siniestros.
2. Cálculo determinístico de las 14 señales de la rúbrica y las 7 reglas críticas (RF01-RF07).
3. Auditoría automatizada de facturas (SRI) extrayendo texto de PDFs y contrastándolo con el tarifario homologado.
4. Asistencia por chat usando modelos de lenguaje (DeepSeek y Gemini 2.5 Flash).
5. Interfaz de usuario SPA con cola de auditoría y chat interactivo colapsables con animaciones de transiciones.

---

## 5. Arquitectura y Stack Tecnológico
La arquitectura detallada y el flujo se describen en [docs/arquitectura.md](docs/arquitectura.md).

- **Backend**: Python 3.10+ / FastAPI.
- **Base de Datos**: SQLite con SQLAlchemy.
- **Modelado de Datos**: 8 tablas normalizadas (ver [docs/modelo_datos.md](docs/modelo_datos.md)).
- **Motores de IA**: DeepSeek Chat API y Google Gemini 2.5 Flash.
- **Frontend**: HTML5 / CSS Vanilla / JavaScript Modular (sin paso de compilación).
- **Procesamiento de Archivos**: pdfplumber (OCR/Extracción Facturas SRI) y reportlab (Generador de Informes PDF).

---

## 6. Modelo de Datos
El sistema utiliza una base de datos SQLite relacional. Las tablas clave son:
- `siniestros`: Almacena el siniestro, el score calculado, clasificación y el JSON de alertas.
- `polizas`: Almacena vigencias, prima, suma asegurada y deducible.
- `asegurados_sinteticos`: Almacena historial de mora y frecuencia de reclamos del asegurado.
- `vehiculos`: Detalles físicos del vehículo (placa, chasis, marca, modelo).
- `documentos`: Estado de entrega y legibilidad de documentos requeridos (Cédula, Licencia, Denuncia, Presupuesto).
- `invoices` y `invoice_items`: Datos extraídos de facturas del taller para auditoría de tarifas.

*La documentación detallada se encuentra en [docs/modelo_datos.md](docs/modelo_datos.md).*

---

## 7. Señales de Posible Fraude
Se evalúan 14 señales de fraude ponderadas que suman un máximo de 98 puntos:
1. Reclamo cercano a borde de vigencia (S01 - hasta 8 pts)
2. Demora reporte robo (S02 - hasta 8 pts)
3. Alta frecuencia asegurado (S03 - hasta 8 pts)
4. Alta frecuencia vehículo (S04 - hasta 6 pts)
5. Frecuencia conductor (S05 - hasta 8 pts)
6. Frecuencia solo Responsabilidad Civil (S06 - hasta 6 pts)
7. Beneficiario recurrente cruzado (S07 - hasta 10 pts)
8. Documentación incompleta/ilegible (S08 - hasta 4 pts)
9. Dinámica sospechosa / nocturna (S09 - hasta 6 pts)
10. Evento sin tercero involucrado (S10 - hasta 6 pts)
11. Documentos con inconsistencias de fecha/enmienda (S11 - hasta 10 pts)
12. Reporte tardío extremo (S12 - hasta 5 pts)
13. Similitud de narrativas entre siniestros (S13 - hasta 8 pts)
14. Monto reclamado cercano a la suma asegurada (S14 - hasta 5 pts)

*La justificación detallada y algoritmo se encuentra en [docs/reglas_negocio.md](docs/reglas_negocio.md).*

---

## 8. Score de Riesgo (Semáforo)
El puntaje obtenido de las 14 señales se normaliza a una escala de 0-100 y clasifica los siniestros:
- **🟢 Verde (0 - 40)**: Riesgo Bajo. Continuar flujo normal.
- **🟡 Amarillo (41 - 75)**: Riesgo Medio. Escalar a Unidad Antifraude para revisión documental.
- **🔴 Rojo (76 - 100)**: Riesgo Alto. Escalar a Unidad Antifraude para inspección física especializada.

*Nota: El fallo de las reglas críticas RF01 (inconsistencia de ramo) o RF02 (siniestro fuera de vigencia de póliza) fuerza una clasificación automática en Rojo (Score 85+) por motivos de cobertura.*

---

## 9. Uso de Inteligencia Artificial (IA)
- **DeepSeek (Chatbot principal)**: Empleado para reescribir y estructurar en lenguaje natural formal las respuestas a las consultas del chatbot conversacional.
- **Gemini 2.5 Flash (Auditor e IA Fallback)**: Utilizado para auditar facturas complejas de talleres mediante técnicas de Chain-of-Thought y Self-Reflection, y como fallback del chatbot si la API de DeepSeek está inactiva.
- **Similitud semántica local**: Lógica NLP local para comparar narrativas duplicadas sin costo de tokens ni latencia innecesaria.

*La documentación sobre la integración se encuentra en [docs/uso_ia.md](docs/uso_ia.md).*

---

## 10. Instalación y Ejecución

### 1. Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto basándote en el archivo `.env.example`:
```bash
GOOGLE_API_KEY=tu_api_key_de_google_aqui
DEEPSEEK_API_KEY=tu_api_key_de_deepseek_aqui
```

### 2. Instalación de Dependencias
Instala los paquetes de Python desde el archivo `requirements.txt` en la raíz:
```bash
pip install -r requirements.txt
```

### 3. Inicialización y Ejecución del Servidor
Ejecuta el servidor FastAPI con uvicorn:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
La aplicación se inicializa automáticamente y crea la base de datos SQLite poblada con los ~60 siniestros sintéticos.

### 4. Ejecución de Pruebas Unitarias
Para correr la suite de pruebas del motor de reglas:
```bash
python -m unittest tests/test_fraud_rules.py
```

### 5. Acceso al Frontend
Abre en tu navegador la dirección: `http://localhost:8000/app/`

---

## 11. Demo y Casos de Uso
1. **Visualizar el Dashboard**: Revisa el semáforo y las métricas financieras de siniestros.
2. **Consultar al Asistente Antifraude**: Abre la burbuja de chat (esquina inferior derecha) y haz clic en alguna pregunta predefinida (FAQ) o formula tus propias preguntas como:
   - *¿Qué asegurados tienen mayor frecuencia de reclamos?*
   - *¿Por qué el siniestro SIN-6 fue marcado con alto riesgo?*
3. **Revisar Siniestros y Documentos**: Navega a la pestaña de "Siniestros" para ver el detalle de póliza, vehículos y documentos de cada caso.
4. **Ver Cola de Auditoría**: Despliega el panel colapsable flotante de pendientes (esquina inferior izquierda) para inspeccionar facturas sin auditar o inicia auditorías de prueba en la sección "Subir PDF".

---

## 12. Seguridad, Privacidad y Ética
- **Protección de Datos**: Todos los nombres de clientes, RUCs, placas de vehículos y montos son 100% sintéticos y generados aleatoriamente, cumpliendo con la Ley Orgánica de Protección de Datos Personales (LOPDP).
- **Revisión Humana Obligatoria**: La IA actúa únicamente como una herramienta de apoyo que sugiere alertas y calcula desviaciones. Todas las decisiones de aprobación, rechazo o escalamiento quedan reservadas al analista humano.

---

## 13. Limitaciones y Próximos Pasos
- **NLP Avanzado**: El análisis de narrativas actual se basa en correspondencia de strings. Se planea migrar a modelos de Embeddings locales (ej. SentenceTransformers) para detectar similitudes semánticas más abstractas.
- **OCR de Imágenes**: Actualmente el sistema procesa facturas estructuradas en PDF. El siguiente paso es integrar un motor de OCR para digitalizar imágenes de facturas arrugadas o fotos tomadas desde smartphones.

*La documentación sobre fronteras de error se encuentra en [docs/limitaciones.md](docs/limitaciones.md).*
