# Arquitectura de Seguridad — Sistema de Perfiles Aislados

## Diagrama de flujo de seguridad

```mermaid
flowchart TD
    %% ── CLIENTE ────────────────────────────────────────
    subgraph CLIENT["🖥️  Cliente (Browser)"]
        direction TB
        UI["SPA Frontend\n(index.html + JS modules)"]
        LS["localStorage\n profileToken\n profileId\n profileName"]
        MODAL["Profile Selector Modal\n(primera visita / logout)"]

        UI -->|"sin sesión"| MODAL
        MODAL -->|"token guardado"| LS
        LS -->|"token leído al iniciar"| UI
    end

    %% ── TRANSPORTE ─────────────────────────────────────
    subgraph TRANSPORT["🔐  Capa de Transporte"]
        HEADER["X-Profile-Token: {profile_id}:{HMAC}\n\ninyectado por api.js en cada request"]
    end

    CLIENT -->|"fetch + header"| TRANSPORT

    %% ── BACKEND ────────────────────────────────────────
    subgraph BACKEND["⚙️  Backend — FastAPI"]
        direction TB

        subgraph AUTH_LAYER["Capa de Autenticación (get_profile dep.)"]
            T1["1. Leer X-Profile-Token del header"]
            T2["2. Separar profile_id y firma HMAC"]
            T3["3. Cargar Profile desde BD por ID"]
            T4["4. Recomputar HMAC con token_secret del perfil"]
            T5{"5. compare_digest\n¿HMAC válido?"}
            T6["✅ Inyectar Profile en request"]
            T7["❌ HTTP 403 Forbidden"]

            T1 --> T2 --> T3 --> T4 --> T5
            T5 -->|"coincide"| T6
            T5 -->|"no coincide"| T7
        end

        subgraph SCOPE_LAYER["Capa de Aislamiento (ProfileScope)"]
            S1["ProfileScope(db, profile)"]
            S2["scope.siniestros()\n→ WHERE profile_id = ?"]
            S3["scope.invoices()\n→ WHERE profile_id = ?"]
            S4["scope.audit_results()\n→ WHERE profile_id = ?"]
            S5["scope.tariffs()\n→ WHERE profile_id = ?"]
            S6["scope.workshops()\n→ WHERE profile_id = ?"]

            S1 --> S2 & S3 & S4 & S5 & S6
        end

        subgraph ENDPOINTS["Endpoints de negocio"]
            EP1["/api/dashboard"]
            EP2["/api/audit-results"]
            EP3["/api/claims"]
            EP4["/api/tariffs"]
            EP5["/api/siniestros/*"]
            EP6["... todos los demás"]
        end

        subgraph PUBLIC_EP["Endpoints públicos (sin token)"]
            PE1["GET /api/profiles"]
            PE2["POST /api/profiles"]
            PE3["POST /api/profiles/{id}/token\n(login por selección)"]
        end

        T6 --> S1
        S1 --> EP1 & EP2 & EP3 & EP4 & EP5 & EP6
    end

    TRANSPORT --> AUTH_LAYER

    %% ── BASE DE DATOS ───────────────────────────────────
    subgraph DB["🗄️  SQLite — Esquema de Aislamiento"]
        direction LR
        PTABLE["profiles\n id (UUID PK)\n name\n token_secret ← nunca sale de la BD\n is_active"]

        PTABLE -->|"FK profile_id"| DT1["siniestros\n+ profile_id"]
        PTABLE -->|"FK profile_id"| DT2["polizas\n+ profile_id"]
        PTABLE -->|"FK profile_id"| DT3["asegurados_sinteticos\n+ profile_id"]
        PTABLE -->|"FK profile_id"| DT4["workshops\n+ profile_id"]
        PTABLE -->|"FK profile_id"| DT5["invoices\n+ profile_id"]
        PTABLE -->|"FK profile_id"| DT6["tariff_items\n+ profile_id"]
        PTABLE -->|"FK profile_id"| DT7["audit_results\n+ profile_id"]

        DT1 -->|"cascade"| DT8["documentos\n(heredado)"]
        DT5 -->|"cascade"| DT9["invoice_items\n(heredado)"]
        DT7 -->|"cascade"| DT10["audit_findings\n(heredado)"]
    end

    BACKEND -->|"queries filtradas por profile_id"| DB

    %% ── TOKEN FLOW ──────────────────────────────────────
    subgraph TOKEN_GEN["🔑  Generación de Token (sin contraseña)"]
        direction LR
        TG1["Usuario selecciona perfil"] --> TG2
        TG2["POST /api/profiles/{id}/token"] --> TG3
        TG3["Backend carga token_secret del perfil\nde la BD"] --> TG4
        TG4["HMAC-SHA256(profile_id, token_secret)"] --> TG5
        TG5["Token: '{profile_id}:{firma}'"]
        TG5 --> TG6["Almacenado en localStorage"]
    end

    %% ── GARANTÍAS DE SEGURIDAD ──────────────────────────
    subgraph GUARANTEES["🛡️  Garantías de Aislamiento"]
        G1["✅ profile_id no adivinable (UUID v4)"]
        G2["✅ Token no falsificable (HMAC con secret de BD)"]
        G3["✅ Toda query lleva WHERE profile_id = ?"]
        G4["✅ No hay endpoint que devuelva datos cruzados"]
        G5["✅ El cliente no controla el filtrado"]
        G6["✅ token_secret nunca se expone en respuestas"]
    end

    style CLIENT fill:#1e1e3f,stroke:#6366f1,color:#e2e8f0
    style TRANSPORT fill:#1a2744,stroke:#3b82f6,color:#e2e8f0
    style BACKEND fill:#1a2a1a,stroke:#22c55e,color:#e2e8f0
    style DB fill:#2a1a1a,stroke:#f59e0b,color:#e2e8f0
    style TOKEN_GEN fill:#2a1a2a,stroke:#a855f7,color:#e2e8f0
    style GUARANTEES fill:#1a2a2a,stroke:#14b8a6,color:#e2e8f0
    style AUTH_LAYER fill:#0f1f0f,stroke:#4ade80,color:#d1fae5
    style SCOPE_LAYER fill:#0f0f1f,stroke:#818cf8,color:#e0e7ff
    style PUBLIC_EP fill:#1f1f0f,stroke:#fbbf24,color:#fef3c7
```

## Descripción de las capas

### 1. Cliente — Gestión de sesión sin contraseña
- Al primer acceso (o tras cerrar sesión), aparece el **Profile Selector Modal**
- El usuario selecciona un perfil existente (por nombre) o crea uno nuevo
- El backend retorna un **token HMAC firmado** → se guarda en `localStorage`
- Cada request posterior inyecta `X-Profile-Token` via `api.js`

### 2. Capa de autenticación — `get_profile` (FastAPI dependency)
- Extrae el header `X-Profile-Token`
- Parsea `{profile_id}:{signature}`
- Carga el perfil de la BD por `profile_id`
- Recomputa `HMAC(profile_id, profile.token_secret)` y compara con `signature` usando `hmac.compare_digest` (tiempo constante, previene timing attacks)
- Si falla → `HTTP 403`, sin revelar si el ID existe o no

### 3. Capa de aislamiento — `ProfileScope`
- Wrapper de `Session` de SQLAlchemy
- **Toda query** pasa por `scope.entidad().filter(entidad.profile_id == self.profile_id)`
- Ningún endpoint de datos accede directamente a la sesión de BD sin pasar por `scope`
- Los getters individuales (`get_invoice(id)`) también filtran por `profile_id`: imposible acceder a registros de otro perfil incluso conociendo el ID

### 4. Base de datos — Integridad referencial
- `profile_id` como FK en 7 tablas primarias
- Tablas derivadas (`documentos`, `invoice_items`, `audit_findings`) heredan el aislamiento a través de sus padres
- Constraint `UNIQUE (profile_id, code)` en tarifas y `UNIQUE (profile_id, ruc)` en workshops
- Datos pre-existentes migrados al **perfil por defecto** (`00000000-0000-0000-0000-000000000001`)

### 5. Prevención de spoofing
| Vector de ataque | Mitigación |
|---|---|
| Manipular `profile_id` en la URL | `scope.get_X(id)` filtra por `profile_id` del token |
| Forjar un token para otro perfil | HMAC depende del `token_secret` almacenado en BD |
| Enumerar UUIDs de perfiles | UUIDs v4 = 2¹²² combinaciones, no adivinables |
| Timing attack en verificación | `hmac.compare_digest()` en tiempo constante |
| Inyección de header | FastAPI valida tipos estrictamente; header es string opaco |
