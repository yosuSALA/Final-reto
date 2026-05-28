# Diagrama — Reglas de Negocio y Scoring Antifraude

> Fuente: [`docs/reglas_negocio.md`](../reglas_negocio.md)

## Pipeline de evaluación de fraude

```mermaid
flowchart TD
    START([🚀 Siniestro recibido]) --> RF_CHECK

    subgraph RF["Reglas Críticas RF01–RF07 (excluyentes)"]
        RF_CHECK{Evaluar reglas\ncríticas}
        RF_CHECK -->|RF01 Falla| ROJO_DIRECTO["🔴 Score = 85+\nRojo directo\nRF01: Ramo/Cobertura inválidos"]
        RF_CHECK -->|RF02 Falla| ROJO_DIRECTO2["🔴 Score = 85+\nRojo directo\nRF02: Póliza fuera de vigencia"]
        RF_CHECK -->|RF03 Alerta| AMARILLO_FLAG["⚠️ Flag mora\nRF03: Prima en mora"]
        RF_CHECK -->|RF04 Falla| DOC_FAIL["⚠️ Flag docs\nRF04: Documentación mínima"]
        RF_CHECK -->|RF05 Falla| DEDUC_FAIL["⚠️ Flag deducible\nRF05: Monto ≤ deducible"]
        RF_CHECK -->|RF06 Falla| SUMA_FAIL["⚠️ Flag suma\nRF06: Monto > suma asegurada"]
        RF_CHECK -->|RF07 Falla| TALLER_FAIL["⚠️ Flag taller\nRF07: RUC inválido / taller suspendido"]
        RF_CHECK -->|Todas pasan| SENALES
    end

    subgraph SENALES["14 Señales Ponderadas (score acumulativo)"]
        direction LR
        S01["S01 Borde vigencia\n±15 días → +8\n±30 días → +4"]
        S02["S02 Demora reporte Robo\n>3 días → +8\n>1 día → +4"]
        S03["S03 Freq. asegurado\n>3 reclamos/12m → +8\n≥2 → +4"]
        S04["S04 Freq. vehículo\n≥2 prev → +6\n1 prev → +3"]
        S05["S05 Freq. conductor\nalta frec. + conductor adicional"]
        S06["S06 Solo RC\n≥2 RC mismo asegurado → +6"]
        S07["S07 Beneficiario recurrente\n≥2 pólizas → +10\n1 póliza extra → +5"]
        S08["S08 Docs incompletos\ndocs_completos==0 → +4"]
        S09["S09 Dinámica sospechosa\nmadrugada / sin testigos → +6"]
        S10["S10 Sin tercero\nchoque objeto fijo / volcamiento → +6"]
        S11["S11 Doc inconsistente\nfactura < fecha siniestro → +10"]
        S12["S12 Reporte tardío\n>30 días → +5\n>15 días → +3"]
        S13["S13 Narrativas coincidentes\nSequenceMatcher ≥ 75% → +8"]
        S14["S14 Monto ≈ suma asegurada\n≥90% → +5\n≥75% → +3"]
    end

    SENALES --> NORMALIZE["📊 Normalizar\nscore_raw / 98 × 100"]
    NORMALIZE --> SEMAFORO

    subgraph SEMAFORO["Semáforo de Riesgo"]
        SEMAFORO_CHECK{Score\nnormalizado}
        SEMAFORO_CHECK -->|"0 – 40"| VERDE["🟢 VERDE\nFlujo de liquidación normal"]
        SEMAFORO_CHECK -->|"41 – 75"| AMARILLO["🟡 AMARILLO\nEscalar a Unidad Antifraude\nVerificación documental"]
        SEMAFORO_CHECK -->|"76 – 100"| ROJO["🔴 ROJO\nBloquear caso\nInspección física especializada"]
    end

    ROJO_DIRECTO --> SEMAFORO_CHECK
    ROJO_DIRECTO2 --> SEMAFORO_CHECK
    AMARILLO_FLAG --> NORMALIZE
    DOC_FAIL --> NORMALIZE
    DEDUC_FAIL --> NORMALIZE
    SUMA_FAIL --> NORMALIZE
    TALLER_FAIL --> NORMALIZE
```

## Detalle de señales (pesos máximos)

```mermaid
xychart-beta horizontal
    title "Pesos máximos de señales de fraude (sobre 98 pts totales)"
    x-axis ["S07 Beneficiario rec.", "S11 Doc. inconsistente", "S01 Borde vigencia", "S02 Demora robo", "S03 Freq. asegurado", "S05 Freq. conductor", "S13 Narrativas", "S04 Freq. vehículo", "S06 Solo RC", "S09 Dinámica", "S10 Sin tercero", "S12 Reporte tardío", "S14 Monto cercano", "S08 Docs incompletos"]
    y-axis "Puntos" 0 --> 10
    bar [10, 10, 8, 8, 8, 8, 8, 6, 6, 6, 6, 5, 5, 4]
```

## Reglas críticas (RF) — tabla de decisión

```mermaid
flowchart LR
    subgraph RF_TABLE["Reglas Críticas — Condición y Efecto"]
        RF01["RF01\nRamo siniestro ≠ ramo póliza\n→ Rojo automático"]
        RF02["RF02\nfecha_ocurrencia fuera de vigencia\n→ Rojo automático"]
        RF03["RF03\nmora_actual == 1\n→ Flag de alerta"]
        RF04["RF04\nFalta Cédula / Licencia /\nDenuncia / Presupuesto\n→ Flag docs"]
        RF05["RF05\nmonto_reclamado ≤ deducible\n→ Reclamo no procede"]
        RF06["RF06\nmonto_reclamado > suma_asegurada\n→ Excede cobertura"]
        RF07["RF07\nRUC taller ≠ 13 dígitos\no taller suspendido\n→ Flag proveedor"]
    end
```
