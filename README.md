# Miraclex — Detector Agentico de Fraude en Siniestros | Hackathon 2026

Plataforma inteligente de Aseguradora del Sur para auditar automaticamente facturas de siniestros (vehiculares, salud, vida, hogar, generales), priorizar casos criticos y proteger la reserva tecnica. Detecta fraude, sobrecobros, duplicados e incoherencias antes del pago, combinando un motor de reglas deterministicas con DeepSeek V4 Flash para evaluacion de riesgo.

---

## 1. Resumen Ejecutivo
El prototipo prioriza casos sospechosos para revision humana en la Unidad Antifraude. Combina:
- Motor de reglas y scoring de riesgo
- Auditoria de facturas de taller (PDF)
- Dashboard ejecutivo con priorizacion
- Chatbot con preguntas del jurado y consultas por siniestro

Principio clave: la solucion genera alertas de posible fraude; no acusa ni decide pagos/rechazos automaticamente.

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
- Cargar y procesar datos sinteticos de siniestros multi-ramo (vehiculos, salud, vida, hogar, generales).
- Detectar senales de posible fraude y calcular score 0-100.
- Clasificar en Verde, Amarillo y Rojo con accion sugerida.
- Explicar por que cada caso fue marcado.
- Permitir consultas en lenguaje natural para analistas.

---

## 4. Alcance
Este prototipo abarca:
1. Ingestión y estructuración de pólizas, vehículos, asegurados, documentos y siniestros.
2. Cálculo determinístico de las 14 señales de la rúbrica y las 7 reglas críticas (RF01-RF07).
3. Auditoría automatizada de facturas (SRI) extrayendo texto de PDFs y contrastándolo con el tarifario homologado.
4. Asistencia por chat usando OpenCode Go (DeepSeek v4 Flash).
5. Interfaz de usuario SPA con cola de auditoría y chat interactivo colapsables con animaciones de transiciones.

No incluye: acusacion formal, conclusion legal, rechazo automatico de siniestros.

---

## 5. Arquitectura y Stack Tecnológico
La arquitectura detallada y el flujo se describen en [docs/arquitectura.md](docs/arquitectura.md).

- **Backend**: Python 3.10+ / FastAPI (puerto 8000).
- **Frontend Server**: Node.js / Express (puerto 3000, proxy API y SPA estática).
- **Base de Datos**: SQLite con SQLAlchemy.
- **Modelado de Datos**: 8 tablas normalizadas (ver [docs/modelo_datos.md](docs/modelo_datos.md)).
- **Motores de IA**: OpenCode Go (DeepSeek v4 Flash).
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

Nota operativa: el score se usa para priorizar revision humana, no para decision final automatica.

---

## 9. Uso de Inteligencia Artificial (IA)
- **DeepSeek V4 Flash (Chatbot principal)**: Empleado para reescribir y estructurar en lenguaje natural formal las respuestas a las consultas del chatbot conversacional.
- **DeepSeek V4 Flash (Auditor de Facturas)**: Utilizado para auditar facturas complejas de talleres mediante técnicas de Chain-of-Thought y Self-Reflection, evaluando riesgo de sobrecobro e inconsistencias.
- **Similitud semántica local**: Lógica NLP local para comparar narrativas duplicadas sin costo de tokens ni latencia innecesaria.

*La documentación sobre la integración se encuentra en [docs/uso_ia.md](docs/uso_ia.md).*

---

## 10. Instalacion y Ejecucion

### 1. Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto basándote en el archivo `.env.example`:
```bash
# Principal (recomendado): OpenCode Go con modelo explícito
OPENCODE_GO_API_KEY=tu_api_key_de_opencode_go_aqui
OPENCODE_GO_API_BASE=https://tu-gateway-opencode-go/v1
OPENCODE_GO_MODEL=deepseek-v4-flash

# Opcional: fallback directo a DeepSeek
DEEPSEEK_API_KEY=
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Nota: el backend prioriza `OPENCODE_GO_API_KEY` y usa ese gateway como fuente por defecto del chatbot.

### 2. Instalacion de Dependencias
Instala los paquetes Python:
```bash
pip install -r backend/requirements.txt
```

### 3. Inicializacion y Ejecucion del Servidor
Primero, inicia el Frontend (Express, puerto 3000):
```bash
npm install
node server.js
```

En otra terminal, inicia el Backend (FastAPI, puerto 8000):
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
La app inicializa SQLite y carga data sintetica de demo.

### 4. Ejecución de Pruebas Unitarias
Para correr la suite de pruebas del motor de reglas:
```bash
python -m unittest tests/test_fraud_rules.py
```

### 5. Acceso Web
- SPA Frontend: `http://localhost:3000/`
- Landing / API Backend: `http://localhost:8000/`
- App principal: `http://localhost:8000/app/`

---

## 11. Demo y Casos de Uso
1. **Visualizar el Dashboard**: Revisa el semáforo y las métricas financieras de siniestros.
2. **Consultar al Asistente Antifraude**: Abre la burbuja de chat (esquina inferior derecha) y haz clic en alguna pregunta predefinida (FAQ) o formula tus propias preguntas como:
   - *¿Qué asegurados tienen mayor frecuencia de reclamos?*
   - *¿Por qué el siniestro SIN-6 fue marcado con alto riesgo?*
3. **Revisar Siniestros por Asegurado**: Navega a la pestaña de "Siniestros" donde los casos se agrupan por asegurado. Cada fila muestra el score de posible fraude (0-100) con semaforo Verde/Amarillo/Rojo.
4. **Consultar Riesgo con DeepSeek**: Haz clic en el boton `DeepSeek` junto a cualquier siniestro para que el chatbot analice automaticamente por que fue marcado con ese nivel de riesgo.
5. **Ver Cola de Auditoria**: Despliega el panel colapsable flotante de pendientes (esquina inferior izquierda) para inspeccionar facturas sin auditar.
6. **Resumen Ejecutivo**: Usa el boton `Resumen` en cada siniestro para ver historial del asegurado y del bien asegurado.

---

## 12. Seguridad, Privacidad y Ética
- **Protección de Datos**: Todos los nombres de clientes, RUCs, placas de vehículos y montos son 100% sintéticos y generados aleatoriamente, cumpliendo con la Ley Orgánica de Protección de Datos Personales (LOPDP).
- **Revisión Humana Obligatoria**: La IA actúa únicamente como una herramienta de apoyo que sugiere alertas y calcula desviaciones. Todas las decisiones de aprobación, rechazo o escalamiento quedan reservadas al analista humano.

---

## 13. Limitaciones y Próximos Pasos
- **NLP Avanzado**: El análisis de narrativas actual se basa en correspondencia de strings. Se planea migrar a modelos de Embeddings locales (ej. SentenceTransformers) para detectar similitudes semánticas más abstractas.
- **OCR de Imágenes**: Actualmente el sistema procesa facturas estructuradas en PDF. El siguiente paso es integrar un motor de OCR para digitalizar imágenes de facturas arrugadas o fotos tomadas desde smartphones.

*La documentación sobre fronteras de error se encuentra en [docs/limitaciones.md](docs/limitaciones.md).*

---

## 14. Entregables y Evidencia
- Matriz de cumplimiento: `docs/MATRIZ_CUMPLIMIENTO_RETO.md`
- Plan de implementacion: `docs/PLAN_SOFISTICADO_IMPLEMENTACION.md`
- Loop de revision DeepSeek: `docs/DEEPSEEK_REVIEW_LOOP.md`
- Perfiles de acceso: `docs/PERFILES_ACCESO.md`

Estado actual recomendado para manana:
- Cerrar P0 de reglas/score en matriz
- Ejecutar pruebas de API y flujo UI
- Ensayar demo de 10 minutos con preguntas del jurado
