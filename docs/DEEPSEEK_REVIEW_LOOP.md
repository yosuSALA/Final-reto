# DeepSeek v4 Flash - Review e Iteracion Continua

Este documento define como usar DeepSeek v4 Flash (via OpenCode Go) para revisar cada avance del prototipo del reto HackIAthon 2026.

## 1) Objetivo del loop

- Detectar errores funcionales y de UX rapido.
- Validar cumplimiento del reto (score, explicabilidad, etica, entregables).
- Generar acciones concretas por iteracion, no solo opiniones.

## 2) Modo de trabajo recomendado

Trabajar en ciclos cortos de 20-40 minutos:

1. Implementar un bloque pequeno.
2. Ejecutar pruebas locales.
3. Pedir revision a DeepSeek con evidencia.
4. Aplicar correcciones.
5. Repetir hasta pasar checklist.

## 2.1) Configuracion del modelo en OpenCode Go

En tu archivo `.env` define explicitamente el modelo para que no rote a otros:

```env
OPENCODE_GO_API_KEY=tu_api_key
OPENCODE_GO_API_BASE=https://tu-gateway-opencode-go/v1
OPENCODE_GO_MODEL=deepseek-v4-flash
```

Si no existe `OPENCODE_GO_API_KEY`, el sistema usa modo local (sin LLM).

## 3) Checklist de verificacion por iteracion

### A. Flujo funcional

- [ ] Subir PDF agrega factura a pendientes.
- [ ] Cola inferior izquierda muestra pendientes.
- [ ] Si no hay pendientes, boton "Ejecutar auditoria" queda gris.
- [ ] Auditoria genera score y hallazgos.
- [ ] Vista detalle permite preview de PDF.

### B. Reglas y score

- [ ] Reglas excluyentes aplican correctamente.
- [ ] Score gradual respeta rangos 0-40 / 41-75 / 76-100.
- [ ] Accion sugerida visible por nivel.
- [ ] Lenguaje: "posible fraude" y "revision humana".

### C. Seguridad y etica

- [ ] Sin acusaciones automaticas.
- [ ] Sin decisiones legales automaticas.
- [ ] Restricciones por perfil respetadas (cuando se implemente chat agente).
- [ ] Sin credenciales en repo.

### D. Presentacion hackathon

- [ ] Dashboard muestra priorizacion.
- [ ] PDF interno y externo son legibles para demo.
- [ ] README y docs actualizados.

## 4) Prompt base para DeepSeek (revision tecnica)

Usa este prompt en OpenCode Go:

```text
Actua como revisor tecnico senior de hackathon.
Proyecto: Detector de posibles fraudes en siniestros.

Objetivo de esta revision:
1) Encontrar fallos funcionales reales.
2) Verificar cumplimiento del documento del reto.
3) Dar acciones concretas de correccion, con prioridad.

Responde en este formato:
- Hallazgo
- Evidencia (archivo/endpoint/pantalla)
- Impacto (alto/medio/bajo)
- Solucion sugerida
- Como probar la correccion

No des recomendaciones genericas. Solo cambios accionables.
```

## 5) Prompt base para DeepSeek (QA de UX y demo)

```text
Revisa la UX de demo para jurado en 10 minutos.

Evalua:
- Claridad del flujo de carga y cola
- Claridad del score de riesgo
- Explicabilidad de alertas
- Comprension de "alerta" vs "acusacion"

Devuelve:
1) 5 problemas de mayor impacto
2) 5 mejoras rapidas (menos de 30 min cada una)
3) Script de demo de 4 minutos
```

## 6) Comandos de prueba local

Backend:

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Frontend:

```bash
npm install
npm run start
```

Abrir:

- App FastAPI + frontend: `http://localhost:8000/app/`
- Landing: `http://localhost:8000/`

## 7) Matriz minima de pruebas API

1. `GET /api/dashboard?include_test=1`
2. `GET /api/invoices/pending?include_test=1`
3. `POST /api/audit-rules/{invoice_id}`
4. `GET /api/audit-results/{id}`
5. `GET /api/audit-results/{id}/report-preview?type=internal`
6. `GET /api/audit-results/{id}/report-preview?type=workshop`

## 8) Criterios de salida de una iteracion

Una iteracion se considera "aceptable" si:

- No hay errores bloqueantes en consola ni API.
- Se cumple el bloque funcional planificado.
- DeepSeek devuelve maximo 2 hallazgos de impacto alto.
- Se documentan cambios y pasos de prueba.

## 9) Proxima fase (pendiente)

- Chatbot tipo burbuja con restricciones por perfil.
- Capa de politicas para consultas del agente IA.
- Ajuste total del score al esquema del PDF del reto.
