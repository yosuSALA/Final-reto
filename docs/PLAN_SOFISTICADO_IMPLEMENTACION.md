# Plan Sofisticado de Implementacion

## Contexto

Base actual: sistema de auditoria de facturas con FastAPI + frontend SPA. Objetivo: evolucionar a detector de posibles fraudes en siniestros alineado al reto HackIAthon 2026.

## Fase 1 (ya iniciada)

- Cola visual persistente de facturas pendientes.
- Boton de auditoria en gris cuando no hay pendientes.
- Flujo de subida -> cola -> auditoria.
- Guia formal de iteracion con DeepSeek.

## Fase 2 (siguiente)

### 2.1 Score del reto

- Incorporar reglas excluyentes RF-01..RF-07.
- Score gradual por tabla del reto.
- Semaforo oficial:
  - Verde 0-40
  - Amarillo 41-75
  - Rojo 76-100
- Accion sugerida obligatoria por nivel.

### 2.2 Restricciones eticas

- Sustituir textos de "rechazo" automatico por "requiere revision humana".
- Evitar lenguaje legal o acusatorio.

## Fase 3

### 3.1 Chatbot burbuja

- Widget flotante (esquina inferior derecha).
- Endpoint `POST /api/agent/query`.
- Preguntas guiadas del jurado + pregunta libre.

### 3.2 Perfiles y politicas

- Perfil: analista, antifraude, jefatura, auditoria, demo_jurado.
- Restriccion de campos por perfil.
- Bloqueo de consultas no permitidas.

## Fase 4

- Dashboard final orientado a fraude en siniestros.
- Top 10 riesgos, proveedores recurrentes, documentos faltantes.
- PDF interno/externo con narrativa del reto.

## Fase 5

- Entregables finales:
  - README actualizado
  - arquitectura.md
  - modelo_datos.md
  - reglas_negocio.md
  - uso_ia.md
  - limitaciones.md
  - pitch demo

## Politica de pruebas por fase

Para cerrar cada fase:

1. Pruebas API basicas.
2. Prueba UI manual en desktop y mobile.
3. Revision DeepSeek con evidencia.
4. Correccion de hallazgos altos.

## Guion de test rapido para ti

1. Subir 2 PDFs en `#upload`.
2. Verificar contador en cola inferior izquierda.
3. Verificar boton "Ejecutar auditoria" activo.
4. Ejecutar auditoria y confirmar que el contador baja.
5. Si llega a 0, confirmar boton gris/deshabilitado.
6. Abrir detalle y generar PDF interno y taller.
