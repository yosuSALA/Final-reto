# Diagrama — Perfiles de Acceso

> Fuente: [`docs/PERFILES_ACCESO.md`](../PERFILES_ACCESO.md)

## Matriz de permisos por perfil

```mermaid
graph LR
    subgraph AUTONOMIA["Autonomía (capacidad de acción)"]
        AUT_LOW["🔵 Solo lectura"]
        AUT_HIGH["🔴 Control total"]
    end

    subgraph PERFILES_SCOPE["Alcance por perfil"]
        ANALISTA["analista\nSolo lectura\nVista parcial"]
        DEMO["demo_jurado\nLectura + auditoría masiva\nVista completa"]
        ANTIFRAUDE["antifraude\nDecisiones + auditoría\nVista alta"]
        JEFATURA["jefatura\nTarifario + notificaciones\nVista alta"]
        AUDITORIA["auditoria\nAcceso completo\nTodos los permisos"]
    end

    AUT_LOW --> ANALISTA --> DEMO --> ANTIFRAUDE --> JEFATURA --> AUDITORIA --> AUT_HIGH
```

## Flujo de selección de perfil y autenticación

```mermaid
flowchart TD
    START([🌐 Primer acceso a la SPA]) --> CHECK_LS{"¿profileToken\nen localStorage?"}
    CHECK_LS -->|"No"| MODAL["🪟 Profile Selector Modal\nLista de perfiles disponibles"]
    CHECK_LS -->|"Sí"| VALIDATE_TOKEN["🔐 Validar token HMAC\nvia GET /api/profiles/{id}"]

    MODAL --> SELECT["👤 Usuario selecciona perfil"]
    SELECT --> POST_TOKEN["POST /api/profiles/{id}/token"]
    POST_TOKEN --> BACKEND_HMAC["Backend:\n1. Carga profile.token_secret\n2. HMAC-SHA256(profile_id, secret)\n3. Retorna '{id}:{firma}'"]
    BACKEND_HMAC --> SAVE_LS["💾 Guardar en localStorage\nprofileToken, profileId, profileName"]
    SAVE_LS --> LOAD_APP

    VALIDATE_TOKEN -->|"Válido"| LOAD_APP
    VALIDATE_TOKEN -->|"Inválido / Expirado"| MODAL

    LOAD_APP["🚀 Cargar aplicación\napplyProfileUI() → badge de perfil"]
    LOAD_APP --> INJECT["api.js inyecta\nX-Profile-Token en cada fetch"]
    INJECT --> BACKEND_VERIFY["Backend: get_profile() dependency\n1. Leer header\n2. hmac.compare_digest()\n3. HTTP 403 si falla"]
```

## Permisos detallados por perfil

```mermaid
block-beta
    columns 6
    H1["Permiso"]:1 H2["demo_jurado"]:1 H3["analista"]:1 H4["antifraude"]:1 H5["jefatura"]:1 H6["auditoria"]:1

    P1["Auditoría masiva"]:1 V1["✅"]:1 V2["❌"]:1 V3["✅"]:1 V4["✅"]:1 V5["✅"]:1
    P2["Aprobar/Rechazar/Escalar"]:1 V6["❌"]:1 V7["❌"]:1 V8["✅"]:1 V9["✅"]:1 V10["✅"]:1
    P3["Ver/Gestionar tarifario"]:1 V11["❌"]:1 V12["❌"]:1 V13["❌"]:1 V14["✅"]:1 V15["✅"]:1
    P4["Notificación a taller"]:1 V16["❌"]:1 V17["❌"]:1 V18["❌"]:1 V19["✅"]:1 V20["✅"]:1
```

## Archivos de implementación

```mermaid
graph LR
    AUTH_JS["frontend/js/auth.js\n• generateProfileToken()\n• verifyProfileToken()\n• showProfileSelector()\n• applyProfileUI()"]
    STATE_JS["frontend/js/state.js\n• activeProfile\n• profilePermissions"]
    DETAIL_JS["frontend/js/pages/auditDetail.js\n• Restringe Aprobar/Rechazar/Escalar"]
    DASH_JS["frontend/js/pages/dashboard.js\n• Restringe auditoría masiva"]
    BACKEND["backend/auth.py\n• new_token_secret()\n• generate_profile_token()\n• verify_profile_token()"]
    MAIN_PY["backend/main.py\n• get_profile() dependency\n• ProfileScope en endpoints"]

    AUTH_JS --> STATE_JS
    STATE_JS --> DETAIL_JS
    STATE_JS --> DASH_JS
    AUTH_JS -->|"X-Profile-Token header"| BACKEND
    BACKEND --> MAIN_PY
```
