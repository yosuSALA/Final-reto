# Diagrama — Arquitectura de Seguridad

> Fuente: [`docs/arquitectura_seguridad.md`](../arquitectura_seguridad.md)

## Diagrama completo de seguridad

```mermaid
flowchart TD
    subgraph CLIENT["🖥️ Cliente (Browser)"]
        UI["SPA Frontend\n(index.html + JS modules)"]
        LS["localStorage\n• profileToken\n• profileId\n• profileName"]
        MODAL["Profile Selector Modal\n(primera visita / logout)"]
        UI -->|"sin sesión"| MODAL
        MODAL -->|"token guardado"| LS
        LS -->|"token leído al iniciar"| UI
    end

    subgraph TRANSPORT["🔐 Capa de Transporte"]
        HEADER["X-Profile-Token: {profile_id}:{HMAC}\nInyectado por api.js en cada request"]
    end

    CLIENT -->|"fetch + header"| TRANSPORT

    subgraph BACKEND["⚙️ Backend — FastAPI"]
        subgraph AUTH["Capa de Autenticación (get_profile dep.)"]
            T1["1. Leer X-Profile-Token del header"]
            T2["2. Separar profile_id y firma HMAC"]
            T3["3. Cargar Profile desde BD por ID"]
            T4["4. Recomputar HMAC\ncon token_secret del perfil"]
            T5{"5. compare_digest\n¿HMAC válido?"}
            T6["✅ Inyectar Profile en request"]
            T7["❌ HTTP 403 Forbidden"]
            T1 --> T2 --> T3 --> T4 --> T5
            T5 -->|"coincide"| T6
            T5 -->|"no coincide"| T7
        end

        subgraph SCOPE["Capa de Aislamiento (ProfileScope)"]
            S1["ProfileScope(db, profile)"]
            S2["scope.siniestros() WHERE profile_id=?"]
            S3["scope.invoices() WHERE profile_id=?"]
            S4["scope.audit_results() WHERE profile_id=?"]
            S5["scope.tariffs() WHERE profile_id=?"]
            S1 --> S2 & S3 & S4 & S5
        end

        T6 --> S1
    end

    TRANSPORT --> AUTH

    subgraph DB["🗄️ SQLite — Esquema de Aislamiento"]
        PTABLE["profiles\n• id (UUID v4 PK)\n• name\n• token_secret (NUNCA expuesto)\n• is_active"]
        PTABLE -->|"FK profile_id"| DT1["siniestros + profile_id"]
        PTABLE -->|"FK profile_id"| DT2["polizas + profile_id"]
        PTABLE -->|"FK profile_id"| DT3["workshops + profile_id"]
        PTABLE -->|"FK profile_id"| DT4["invoices + profile_id"]
        PTABLE -->|"FK profile_id"| DT5["tariff_items + profile_id"]
        PTABLE -->|"FK profile_id"| DT6["audit_results + profile_id"]
    end

    BACKEND -->|"queries filtradas por profile_id"| DB
```

## Generación de token (sin contraseña)

```mermaid
sequenceDiagram
    participant U as 👤 Usuario
    participant FE as SPA Frontend
    participant API as FastAPI
    participant DB as SQLite

    U->>FE: Selecciona perfil en modal
    FE->>API: POST /api/profiles/{id}/token
    API->>DB: SELECT token_secret WHERE id = {profile_id}
    DB-->>API: token_secret (nunca sale de BD)
    API->>API: firma = HMAC-SHA256(profile_id, token_secret)
    API-->>FE: token = "{profile_id}:{firma}"
    FE->>FE: localStorage.setItem('profileToken', token)
    Note over FE: Cada fetch posterior inyecta<br/>X-Profile-Token: {token}
```

## Prevención de vectores de ataque

```mermaid
flowchart LR
    subgraph ATTACKS["Vectores de ataque"]
        A1["Manipular profile_id en URL"]
        A2["Forjar token para otro perfil"]
        A3["Enumerar UUIDs de perfiles"]
        A4["Timing attack en verificación"]
        A5["Inyección de header"]
    end

    subgraph MITIGATIONS["Mitigaciones"]
        M1["scope.get_X(id) filtra por\nprofile_id del token"]
        M2["HMAC depende del token_secret\nalmacenado en BD"]
        M3["UUIDs v4 = 2¹²² combinaciones\nno adivinables"]
        M4["hmac.compare_digest()\nen tiempo constante"]
        M5["FastAPI valida tipos estrictamente\nheader es string opaco"]
    end

    A1 --> M1
    A2 --> M2
    A3 --> M3
    A4 --> M4
    A5 --> M5
```
