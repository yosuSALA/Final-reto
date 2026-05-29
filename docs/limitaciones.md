# ⚠️ Limitaciones y Consideraciones Éticas — Aseguradora del Sur

Este documento detalla las fronteras operativas del sistema, la gestión de falsos positivos y los principios de uso responsable de la Inteligencia Artificial.

## 1. Limitaciones Técnicas

- **Dependencia de la Calidad Documental**: Si los documentos cargados (cédulas, licencias, facturas digitalizadas) presentan resoluciones de escaneo extremadamente bajas o dobleces severos, el motor OCR/IA podría reportar falsos positivos por ilegibilidad (`legible == 0`) o marcar inconsistencias incorrectamente.
- **Nivel de Similitud Textual (NLP)**: La comparación de narrativas con `SequenceMatcher` es sintáctica. No detecta paráfrasis muy elaboradas escritas con sinónimos totalmente distintos, requiriendo en el futuro un modelo de Embeddings semánticos.
- **Enfoque Híbrido**: El score de fraude se calcula mediante reglas e indicadores ponderados, no mediante un modelo probabilístico predictivo (ML) entrenado con datos históricos etiquetados. Esto es una ventaja para la transparencia del negocio (explicabilidad al 100%), pero carece de auto-aprendizaje adaptativo automático.
- **Dependencia de API Externa**: La auditoría cognitiva depende de DeepSeek V4 Flash vía OpenCode Go. Si la API no está disponible, el sistema usa reglas locales como fallback técnico, pero pierde la capacidad de análisis semántico y generación de explicaciones en lenguaje natural.
- **Concurrencia de Auditoría Masiva**: La auditoría masiva con IA usa `ThreadPoolExecutor` con un máximo configurable de workers (`AI_AUDIT_CONCURRENCY`, default 4, max 8). En volúmenes muy altos puede verse limitada por rate-limits de la API.
- **Chatbot con Inferencia SQL**: El chatbot genera consultas SQL automáticas desde lenguaje natural. En preguntas muy ambiguas o fuera del dominio, la inferencia puede producir consultas incorrectas o resultados vacíos.

---

## 2. Gestión de Falsos Positivos

- **Filtrado Defensivo**: Para la auditoría de facturas, se implementa una holgura o tolerancia (típicamente del 10% al 15% según el repuesto). Si la desviación del precio facturado contra el máximo permitido se encuentra dentro de ese rango, el sistema descarta la alerta automáticamente para evitar abrumar al revisor con falsas alarmas.
- **Casos de Coincidencia de Nombre**: En la búsqueda de beneficiarios recurrentes (Señal S07), se evalúa la coincidencia exacta de strings. Nombres comunes podrían generar alertas cruzadas, lo que resalta la necesidad de validar siempre mediante RUC o identificador único.
- **Confianza Calibrada**: Los hallazgos de DeepSeek V4 Flash incluyen un valor de confianza 0.0-1.0. Los hallazgos CRITICAL requieren confianza >= 0.7 para reducir falsos positivos de alta severidad.
- **Self-Reflection**: El auditor IA ejecuta un segundo pase como "revisor escéptico" para corregir hallazgos imprecisos antes de devolver el resultado final.

---

## 3. Principios Éticos y Humanos

- **Alertas de Revisión, no Acusaciones**: El sistema genera **alertas de posible riesgo**, jamás acusaciones automáticas de fraude. El veredicto siempre es descriptivo ("Alerta de Riesgo").
- **Human-in-the-Loop (Revisión Humana Obligatoria)**: Ningún pago es bloqueado o debitado de forma automatizada sin la intervención humana. El flujo de decisión requiere acción explícita por rol:
  - **Costos/Contabilidad**: aprueban o escalan.
  - **Jefatura**: aprueba finalmente, rechaza o deriva a Legal.
  - **Legal**: revisa derivaciones.
- **Privacidad y Datos**: El prototipo utiliza datos sintéticos anonimizados para proteger la privacidad de los asegurados reales, siguiendo directrices de la Ley Orgánica de Protección de Datos Personales (LOPDP).
- **Trazabilidad**: Todas las acciones del sistema quedan registradas en el log de auditoría (`audit_log`), accesible únicamente al perfil administrador.
- **IA Responsable**: Los insights de DeepSeek V4 Flash citan exclusivamente datos suministrados, nunca inventan métricas ni especulan más allá de la evidencia disponible.
