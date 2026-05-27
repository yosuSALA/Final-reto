# 🤖 Uso de Inteligencia Artificial — Aseguradora del Sur

El prototipo utiliza técnicas avanzadas de Inteligencia Artificial y Procesamiento de Lenguaje Natural (NLP) a través de un enfoque híbrido.

## 1. Auditoría Cognitiva de Facturas (Gemini 2.5 Flash)

Para auditar facturas complejas de talleres frente a los siniestros y al tarifario pactado, se implementa la clase `GeminiAuditor` que sigue los siguientes patrones:

- **Chain-of-Thought (Cadena de Razonamiento) Forzado**: El esquema JSON de respuesta obliga al modelo a rellenar el campo `cadena_de_razonamiento` antes de decidir la severidad y el veredicto final. Esto fuerza al LLM a computar los sobrecostos aritméticamente primero.
- **Few-Shot Calibration**: Se proveen ejemplos estructurados de facturas reales en el prompt de sistema (una limpia y otra con fraudes intencionados) para fijar el estilo analítico.
- **Self-Reflection Pass (Auto-Crítica)**: Una segunda llamada toma la respuesta inicial del modelo y le pide que actúe como un revisor escéptico. Esto permite corregir falsos positivos y encontrar hallazgos omitidos.
- **Validación Semántica y Reintento**: Si la respuesta viola las reglas de consistencia de la aseguradora, se reenvía el prompt con retroalimentación explícita.

---

## 2. Agente conversacional Antifraude (DeepSeek / Gemini)

El chatbot conversacional (disponible en la burbuja de chat flotante) procesa consultas libres sobre siniestros y fraudes mediante un pipeline estructurado:

1. **Inferencia Local sobre Base de Datos**: El backend de FastAPI intercepta la pregunta y realiza búsquedas estructuradas en las tablas SQL (`Poliza`, `AseguradoSintetico`, `Siniestro`, `Documento`). Esto recopila la información factual precisa.
2. **Contextualización de Prompts**: Se construye un prompt que une la pregunta del usuario y los datos duros recuperados.
3. **Llamada de Reescritura Cognitiva**:
   - **DeepSeek (Principal)**: Si `DEEPSEEK_API_KEY` está configurada, se consume el modelo `deepseek-chat` para dotar de una redacción elocuente y ejecutiva a los datos técnicos.
   - **Gemini (Fallback)**: Si no hay clave de DeepSeek pero está `GOOGLE_API_KEY`, se llama a `gemini-2.5-flash`.
   - **Formateador Local (Fallback Técnico)**: Si no hay claves de API, el sistema formatea los datos estructurados en markdown limpio para no interrumpir la experiencia de usuario.

---

## 3. NLP en Comparación de Siniestros (SequenceMatcher)

Para la señal **S13 (Narrativas Coincidentes)**, se implementa una lógica de procesamiento de textos que evalúa la similitud de caracteres entre la descripción del siniestro actual y el historial completo de siniestros. Si la coincidencia supera el **75%**, se activa una señal de alerta por copia o clonación de narrativas de fraude.
