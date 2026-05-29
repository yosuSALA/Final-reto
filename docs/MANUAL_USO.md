# Manual de Uso — Miraclex

Guía práctica para ejecutar la demo final y operar el expediente de siniestros.

## 1. Qué Hace la Aplicación

Miraclex permite:

- Crear y consultar siniestros.
- Generar PDFs sintéticos para demo.
- Cargar declaración, parte policial y factura.
- Detectar automáticamente el siniestro desde referencias `SIN-...` dentro del PDF.
- Auditar facturas con DeepSeek V4 Flash como motor principal.
- Usar reglas locales como fallback técnico o revisión manual.
- Revisar hallazgos, score, reportes y estado del expediente.
- Tomar decisiones humanas: aprobar, rechazar, escalar o derivar a Legal.
- Consultar datos con el chatbot inteligente.
- Analizar métricas con la plataforma de inteligencia operativa.
- Administrar perfiles, contraseñas y revisar el log de auditoría.

## 2. Arranque

Windows:

```bat
start.bat
```

macOS/Linux:

```bash
./start.sh
```

Alternativa con npm:

```bash
npm start
```

Abrir:

- `http://localhost:8000/`
- `http://localhost:8000/app/`
- `http://localhost:8000/docs`

## 3. Demo Automática con IA

Esta es la ruta más rápida para jurado.

1. Abrir la app en `http://localhost:8000/app/`.
2. Seleccionar perfil `Demo / Jurado` o un perfil con permisos.
3. Ir a `Carga`.
4. En `Qué generar`, elegir `Expediente automático con IA`.
5. En `Nivel de riesgo de factura`, elegir `Aleatorio`, `Limpio`, `Sobrecobro` o `Fraude`.
6. Pulsar `Generar`.
7. Esperar a que el sistema cree siniestro, declaración, parte policial, factura y auditoría.
8. Revisar el detalle de auditoría que se abre al finalizar.

Si DeepSeek V4 Flash no responde, el backend usa reglas como fallback y lo muestra en pantalla.

## 4. Demo Manual Paso a Paso

Esta ruta permite mostrar trazabilidad documental.

1. Ir a `Carga`.
2. Elegir `Expediente manual completo (3 PDFs)`.
3. Elegir nivel de riesgo.
4. Pulsar `Generar`.
5. Descargar los tres PDFs generados.
6. En `Tipo de documento`, seleccionar `Declaración` y cargar la declaración.
7. Seleccionar `Parte Policial` y cargar el parte.
8. Seleccionar `Factura` y cargar la factura.
9. Mantener `Siniestro destino` en `Detectar automáticamente desde el PDF` para probar la resolución automática.
10. Ir a `Auditorías` y ejecutar/revisar la auditoría IA.

Orden recomendado: declaración → parte policial → factura → auditoría.

## 5. Carga de Documentos

El selector `Siniestro destino` es opcional.

- Si el PDF trae una referencia `SIN-...`, el backend busca el expediente.
- Si no existe, puede crear un siniestro mínimo con los datos extraídos.
- Si no puede identificarlo, devuelve un mensaje pidiendo selección manual.

Endpoints usados por la UI:

- Declaración automática: `POST /api/claims/auto/declaration`
- Parte automático: `POST /api/claims/auto/police-report`
- Factura: `POST /api/audit-pdf`

## 6. Auditoría

Motor principal:

- DeepSeek V4 Flash vía OpenCode Go.

Motores secundarios:

- DeepSeek API directa si está configurada.
- Reglas locales si DeepSeek falla o si el usuario las ejecuta manualmente.

La auditoría muestra hallazgos, severidad, monto observado, recomendación y reportes PDF.

Opciones de auditoría:

- **Individual con IA**: audita una factura con DeepSeek V4 Flash.
- **Masiva con IA**: audita todas las facturas pendientes con concurrencia.
- **Individual con reglas**: audita con motor de reglas (manual/fallback).
- **Masiva con agente**: audita todas con motor principal + fallback.

## 7. Flujo de Decisión Humana

Desde el detalle de auditoría, según el rol del perfil:

1. **Costos / Contabilidad** pueden:
   - **Aprobar**: aprueba un siniestro no escalado.
   - **Escalar**: escala a Jefatura para revisión.

2. **Jefatura** puede:
   - **Aprobar** (final): aprueba un siniestro previamente escalado.
   - **Rechazar**: rechaza un siniestro escalado.
   - **Derivar a Legal**: envía a Legal un siniestro escalado.

3. **Legal** puede:
   - Consultar siniestros derivados en la sección de notificaciones.

## 8. Workspace del Siniestro

Vista centralizada accesible desde la lista de siniestros. Incluye:

- Resumen ejecutivo.
- Timeline del expediente con todas las acciones.
- Score de fraude con desglose de señales.
- Documentos: declaración, parte policial, facturas.
- Datos de póliza, cliente y vehículo.

## 9. Chatbot Inteligente

Burbuja flotante en la esquina inferior derecha.

- Permite hacer preguntas en lenguaje natural sobre datos del sistema.
- El chatbot usa DeepSeek V4 Flash para reescribir las respuestas.
- Las respuestas están filtradas según el perfil/rol del usuario.
- Incluye preguntas guiadas y pregunta libre.

## 10. Perfiles

Perfiles principales:

- `Demo / Jurado`: puede recorrer todo el flujo.
- `Operaciones`: registra/carga documentos.
- `Antifraude`: revisa riesgo y alertas.
- `Auditoría`: revisa auditorías.
- `Costos` y `Contabilidad`: revisan montos, aprueban o escalan.
- `Jefatura`: aprueba finalmente, rechaza o deriva a Legal.
- `Legal`: revisa derivaciones.
- `Administrador`: gestiona perfiles, contraseñas y auditoría del sistema.

Los perfiles tienen contraseña. La clave maestra de testing por defecto es `admin`, configurable con `ADMIN_PASSWORD`.

## 11. Reportes

Desde el detalle de auditoría se pueden generar:

- Reporte interno con score y hallazgos.
- Notificación al taller sin lenguaje acusatorio.

## 12. Plataforma de Inteligencia

Accesible desde el dashboard:

- Métricas antifraude: distribución de riesgo, montos bajo alerta.
- Métricas de cartera: distribución por ramo, vigencia, sumas.
- Métricas operativas: tiempos, pendientes, cobertura.
- Insight por siniestro: análisis detallado con DeepSeek V4 Flash.
- Insight bajo demanda: briefings ejecutivos generados por IA.

## 13. Panel de Administración

Solo accesible con perfil administrador:

- Log de auditoría de todas las acciones del sistema.
- Filtrado por acción y perfil.
- Estadísticas agregadas por tipo de acción y rol.

## 14. Preguntas Frecuentes

**¿Necesito API key para arrancar?**  
No. La app arranca sin API key. Para auditoría IA real se recomienda configurar `OPENCODE_GO_API_KEY`.

**¿Qué pasa si DeepSeek V4 Flash no responde?**  
El sistema usa reglas locales como fallback técnico y lo indica en la UI.

**¿Dónde quedan los PDFs demo?**  
En `backend/test_pdfs`.

**¿Dónde quedan los reportes?**  
Se sirven desde los endpoints de reportes de auditoría; el backend usa `backend/generated_reports` para archivos generados.

**¿La app decide rechazos automáticamente?**  
No. La app genera alertas y recomendaciones. La decisión final es humana (aprobar, rechazar, escalar o derivar a Legal).

**¿Puedo importar datos desde CSV?**  
Sí. El sistema soporta importación de siniestros (`POST /api/claims/import-csv`) y tarifario (`POST /api/tariffs/import-csv`).

**¿Cómo funciona el chatbot?**  
El chatbot recibe preguntas en lenguaje natural, genera consultas SQL automáticas y reescribe las respuestas con DeepSeek V4 Flash. Las respuestas están filtradas por perfil.

## 15. Checklist de Demo Final

1. Ejecutar `start.bat` o `npm start`.
2. Abrir `http://localhost:8000/app/`.
3. Entrar como `Demo / Jurado`.
4. Mostrar panel `Dashboard`.
5. Ejecutar `Expediente automático con IA`.
6. Mostrar detalle de auditoría con hallazgos y score.
7. Demostrar decisión humana (aprobar/escalar).
8. Abrir workspace del siniestro y mostrar timeline.
9. Probar chatbot con una pregunta.
10. Mostrar métricas de inteligencia operativa.
11. Mostrar flujo manual con PDFs si el jurado pide trazabilidad.
