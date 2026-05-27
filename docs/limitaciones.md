# ⚠️ Limitaciones y Consideraciones Éticas — Aseguradora del Sur

Este documento detalla las fronteras operativas del sistema, la gestión de falsos positivos y los principios de uso responsable de la Inteligencia Artificial.

## 1. Limitaciones Técnicas

- **Dependencia de la Calidad Documental**: Si los documentos cargados (cédulas, licencias, facturas digitalizadas) presentan resoluciones de escaneo extremadamente bajas o dobleces severos, el motor OCR/IA podría reportar falsos positivos por ilegibilidad (`legible == 0`) o marcar inconsistencias incorrectamente.
- **Nivel de Similitud Textual (NLP)**: La comparación de narrativas con `SequenceMatcher` es sintáctica. No detecta paráfrasis muy elaboradas escritas con sinónimos totalmente distintos, requiriendo en el futuro un modelo de Embeddings semánticos.
- **Enfoque Híbrido**: El score de fraude se calcula mediante reglas e indicadores ponderados, no mediante un modelo probabilístico predictivo (ML) entrenado con datos históricos etiquetados. Esto es una ventaja para la transparencia del negocio (explicabilidad al 100%), pero carece de auto-aprendizaje adaptativo automático.

---

## 2. Gestión de Falsos Positivos

- **Filtrado Defensivo**: Para la auditoría de facturas, se implementa una holgura o tolerancia (típicamente del 10% al 15% según el repuesto). Si la desviación del precio facturado contra el máximo permitido se encuentra dentro de ese rango, el sistema descarta la alerta automáticamente para evitar abrumar al revisor con falsas alarmas.
- **Casos de Coincidencia de Nombre**: En la búsqueda de beneficiarios recurrentes (Señal S07), se evalúa la coincidencia exacta de strings. Nombres comunes podrían generar alertas cruzadas, lo que resalta la necesidad de validar siempre mediante RUC o identificador único.

---

## 3. Principios Éticos y Humanos

- **Alertas de Revisión, no Acusaciones**: El sistema genera **alertas de posible riesgo**, jamás acusaciones automáticas de fraude. El veredicto siempre es descriptivo ("Alerta de Riesgo").
- **Human-in-the-Loop (Revisión Humana Obligatoria)**: Ningún pago es bloqueado o debitado de forma automatizada sin la intervención del equipo de la Unidad Antifraude. Los analistas tienen la facultad de **Aprobar**, **Rechazar** o **Escalar** el caso directamente desde la interfaz, quedando la decisión final bajo jurisdicción humana.
- **Privacidad y Datos**: El prototipo utiliza datos sintéticos anonimizados para proteger la privacidad de los asegurados reales, siguiendo directrices de la Ley Orgánica de Protección de Datos Personales (LOPDP).
