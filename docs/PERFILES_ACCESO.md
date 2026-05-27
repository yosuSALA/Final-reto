# Perfiles de Acceso (Demo)

El sistema incluye selector de perfil para simular controles por rol de la Aseguradora del Sur.

## Perfiles disponibles

- `demo_jurado`
- `analista`
- `antifraude`
- `jefatura`
- `auditoria`

## Permisos actuales

| Permiso | demo_jurado | analista | antifraude | jefatura | auditoria |
|---|---|---|---|---|---|
| Ejecutar auditoria masiva | Si | No | Si | Si | Si |
| Decidir (aprobar/rechazar/escalar) | No | No | Si | Si | Si |
| Ver/Gestionar tarifario | No | No | No | Si | Si |
| Notificacion a taller | No | No | No | Si | Si |

## Donde se configura

- UI de perfil: `frontend/index.html`
- Estado perfil: `frontend/js/state.js`
- Reglas de permisos: `frontend/js/auth.js`
- Restriccion de acciones en detalle: `frontend/js/pages/auditDetail.js`
- Restriccion de auditoria masiva: `frontend/js/pages/dashboard.js`

## Nota

Este control es de demostracion para hackathon. Para produccion se recomienda autenticacion real (JWT/OAuth) y autorizacion en backend por endpoint.
