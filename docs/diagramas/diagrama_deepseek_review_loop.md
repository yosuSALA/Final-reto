# Diagrama — DeepSeek Review Loop

> Fuente: [`docs/DEEPSEEK_REVIEW_LOOP.md`](../DEEPSEEK_REVIEW_LOOP.md)

## Ciclo de revisión agéntica con DeepSeek

```mermaid
flowchart TD
    START([🚀 Código / documentación\nlisto para revisión]) --> DEEPSEEK_CALL

    subgraph LOOP["🔄 DeepSeek Review Loop (OpenCode Go)"]
        DEEPSEEK_CALL["📤 Enviar al agente DeepSeek\nv4 Flash (OpenCode Go)\nModelo: deepseek-v4-flash"]

        DEEPSEEK_CALL --> REVIEW_TASK["Tarea de revisión:\n1. Revisar código, endpoints,\n   frontend y documentación\n2. Marcar: CUMPLE / PARCIAL / NO CUMPLE\n3. Agregar evidencia concreta\n   (archivo + línea)\n4. Proponer ajuste puntual si no cumple\n5. Solo hallazgos verificables"]

        REVIEW_TASK --> OUTPUT["📋 Output estructurado:\n• Tabla de cumplimiento\n• Evidencia por archivo\n• Gap detectado\n• Corrección propuesta"]

        OUTPUT --> HUMAN_CHECK{"¿Hallazgos\nresueltos?"}
        HUMAN_CHECK -->|"Pendientes P0/P1"| FIX["🛠️ Desarrollador\ncorrige gaps"]
        FIX --> DEEPSEEK_CALL
        HUMAN_CHECK -->|"Aceptable para demo"| DONE
    end

    DONE(["✅ Listo para presentación\nal jurado"])
```

## Configuración del agente (variables de entorno)

```mermaid
flowchart LR
    subgraph ENV[".env / .env.example"]
        E1["OPENCODE_GO_API_KEY\nClave para OpenCode Go"]
        E2["OPENCODE_GO_API_BASE\nURL base de la API"]
        E3["OPENCODE_GO_MODEL\n= deepseek-v4-flash"]
        E4["PORT = 8010"]
        E5["HOST = 127.0.0.1"]
    end

    ENV --> OPENCODE["OpenCode Go\nCLI agéntico"]
    OPENCODE -->|"modelo configurado"| DEEPSEEK_API["DeepSeek API\ndeepseek-v4-flash"]
    DEEPSEEK_API --> REVIEW["Revisión de código\nsin alucinaciones de contexto\nlargo (modelo eficiente)"]
```

## Protocolo de revisión estructurada

```mermaid
flowchart TD
    PROMPT["📝 Prompt de revisión"] --> STEPS

    subgraph STEPS["Pasos del agente"]
        S1["1️⃣ Revisar código fuente\nbackend/ + frontend/"]
        S2["2️⃣ Revisar endpoints REST\nbuscar en main.py"]
        S3["3️⃣ Revisar documentación\ndocs/*.md"]
        S4["4️⃣ Marcar cada requisito\nCUMPLE / PARCIAL / NO CUMPLE"]
        S5["5️⃣ Evidencia concreta\narchivo:línea"]
        S6["6️⃣ Si no cumple:\narchivo + cambio esperado"]
        S1 --> S2 --> S3 --> S4 --> S5 --> S6
    end

    STEPS --> OUTPUT["📊 MATRIZ_CUMPLIMIENTO_RETO.md\nGenerada automáticamente\npor el agente"]
```
