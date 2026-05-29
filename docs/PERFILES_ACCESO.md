# Perfiles de Acceso (Demo)

El sistema incluye selector de perfil para simular controles por rol de la Aseguradora del Sur.

## Perfiles disponibles

- `demo_jurado`
- `analista`
- `antifraude`
- `jefatura`
- `auditoria`
- `operaciones`
- `costos`
- `contabilidad`
- `legal`

## Permisos actuales

| Permiso | demo_jurado | analista | antifraude | jefatura | auditoria | operaciones | costos | contabilidad | legal |
|---|---|---|---|---|---|---|---|---|---|
| Ejecutar auditoría masiva | Sí | No | Sí | Sí | Sí | No | No | No | No |
| Ejecutar auditoría individual | Sí | No | Sí | Sí | Sí | No | No | No | No |
| Aprobar (no escalado) | No | No | No | No | No | No | Sí | Sí | No |
| Escalar a Jefatura | No | No | No | No | No | No | Sí | Sí | No |
| Aprobar (escalado) | No | No | No | Sí | No | No | No | No | No |
| Rechazar (escalado) | No | No | No | Sí | No | No | No | No | No |
| Derivar a Legal | No | No | No | Sí | No | No | No | No | No |
| Ver notificaciones Legal | No | No | No | No | No | No | No | No | Sí |
| Gestionar tarifario | No | No | No | Sí | Sí | No | No | No | No |
| Notificación a taller | No | No | No | Sí | Sí | No | No | No | No |
| Chatbot inteligente | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Sí |
| Inteligencia operativa | Sí | Sí | Sí | Sí | Sí | No | No | No | No |

## Flujo de decisión por roles

```
Auditoría completada
    ↓
Costos / Contabilidad
    ├── Aprobar → Aprobado
    └── Escalar → Escalado a Jefatura
                      ↓
                  Jefatura
                      ├── Aprobar → Aprobado Final
                      ├── Rechazar → Rechazado
                      └── Derivar → Enviado a Legal
```

## Perfil Administrador

- ID fijo: `admin`.
- Puede crear/eliminar perfiles.
- Puede cambiar contraseñas de otros perfiles.
- Puede emitir tokens para otros perfiles sin contraseña.
- Accede al log de auditoría de acciones (`GET /api/admin/audit-log`).
- Clave maestra por defecto: `admin` (configurable con `ADMIN_PASSWORD`).

## Donde se configura

- UI de perfil: `frontend/index.html`
- Estado perfil: `frontend/js/state.js`
- Reglas de permisos: `frontend/js/auth.js`
- Restricción de acciones en detalle: `frontend/js/pages/auditDetail.js`
- Restricción de auditoría masiva: `frontend/js/pages/dashboard.js`
- Panel admin: `frontend/js/pages/adminAuditLog.js`
- Backend auth: `backend/auth.py`
- Backend scope: `backend/profile_scope.py`

## Nota

Este control es de demostración para hackathon. Para producción se recomienda autenticación real (JWT/OAuth) y autorización en backend por endpoint.
