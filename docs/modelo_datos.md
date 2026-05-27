# 📊 Modelo de Datos — Aseguradora del Sur

El esquema de la base de datos se ha normalizado y diseñado bajo SQLAlchemy para SQLite. El modelo contiene 8 tablas principales que cubren todos los campos solicitados por la rúbrica del reto.

## Tablas y Campos

### 1. `siniestros` (Siniestro)
Representa el reclamo o evento reportado por el cliente.
- `id_siniestro` (Integer, PK): Identificador único de siniestro.
- `id_poliza` (String, FK): Relación con la póliza.
- `id_asegurado` (String, FK): Relación con el asegurado sintético.
- `ramo` (Enum): Ramo del siniestro (`Vehículos`, `Salud`, `Vida`, `Generales`, `Hogar`, `Otro`).
- `cobertura` (Enum): Cobertura aplicada (`Choque`, `Robo`, `Atención médica`, `Incendio`, `Daño`, `Otro`).
- `fecha_ocurrencia` (DateTime): Fecha y hora del accidente.
- `fecha_reporte` (DateTime): Fecha y hora en que se reportó a la aseguradora.
- `monto_reclamado` (Float): Monto inicial solicitado.
- `monto_estimado` (Float): Reserva estimada por el liquidador.
- `monto_pagado` (Float): Monto efectivamente liquidado.
- `estado` (Enum): Estado administrativo (`Reserva`, `Pago Total`, `Pago Parcial`, `Anticipo`, `Negativa`, `Liquidado`, etc.).
- `sucursal` (String): Sucursal/ciudad física donde se procesa.
- `descripcion` (Text): Descripción textual del incidente.
- `documentos_completos` (Integer): Flag (0 = Incompleto, 1 = Completo).
- `beneficiario` (String): Nombre del beneficiario de los fondos.
- `dias_desde_inicio_poliza` (Integer): Días transcurridos desde que empezó la póliza hasta el siniestro.
- `dias_desde_fin_poliza` (Integer): Días restantes hasta que termine la póliza.
- `dias_entre_ocurrencia_reporte` (Integer): Días de demora en reportar.
- `historial_siniestros_asegurado` (Integer): Frecuencia histórica.
- `etiqueta_fraude_simulada` (Integer): 0 para normal, 1 para sospechoso (simulado).
- `fraud_score` (Float): Score ponderado calculado por el motor (0-100).
- `fraud_classification` (String): Semáforo del siniestro (`Verde`, `Amarillo`, `Rojo`).
- `fraud_indicators` (Text): JSON serializado con las alertas y puntajes acumulados.
- `fraud_rules_failed` (Text): JSON serializado de las reglas de negocio incumplidas.
- `vehiculo_id` (Integer, FK): Relación con el vehículo (opcional).

### 2. `polizas` (Poliza)
Contratos y términos de la póliza de seguro.
- `id_poliza` (String, PK): Código único de póliza (ej. POL-50001).
- `id_asegurado` (String, FK): Asegurado titular del contrato.
- `ramo` (Enum): Ramo de cobertura.
- `fecha_inicio` (DateTime): Inicio de vigencia.
- `fecha_fin` (DateTime): Fin de vigencia.
- `prima` (Float): Costo del seguro.
- `suma_asegurada` (Float): Límite máximo de cobertura.
- `deducible` (Float): Monto a asumir por el asegurado.
- `canal_venta` (String): Canal comercial.
- `ciudad` (String): Ciudad de suscripción.
- `estado_poliza` (String): Estado de la póliza (`Vigente`, `Suspendida`, `Anulada`).

### 3. `asegurados_sinteticos` (AseguradoSintetico)
Titular de las pólizas y siniestros.
- `id_asegurado` (String, PK): Código o cédula del asegurado.
- `nombre` (String): Nombre completo.
- `segmento` (String): Categorización del cliente (`VIP`, `Estándar`, `Básico`).
- `antiguedad` (Integer): Años del cliente en la aseguradora.
- `ciudad` (String): Ciudad de residencia.
- `numero_polizas` (Integer): Cantidad de pólizas activas.
- `reclamos_12m` (Integer): Reclamos hechos en el último año.
- `mora_actual` (Integer): Flag (0 = Al día, 1 = En mora).
- `score_cliente_simulado` (Float): Score de reputación del asegurado.

### 4. `vehiculos` (Vehiculo)
Vehículo amparado por pólizas del ramo de Vehículos.
- `id` (Integer, PK): Identificador autoincremental.
- `id_poliza` (String, FK): Póliza que asegura al vehículo.
- `placa` (String): Placa del auto.
- `chasis` (String): Número de chasis.
- `motor` (String): Número de motor.
- `marca` (String): Marca.
- `modelo` (String): Modelo.
- `anio` (Integer): Año de fabricación.

### 5. `documentos` (Documento)
Archivos y evidencias presentados para la liquidación.
- `id_documento` (Integer, PK): ID autoincremental.
- `id_siniestro` (Integer, FK): Siniestro asociado.
- `tipo_documento` (String): Tipo (`Cédula`, `Licencia`, `Denuncia`, etc.).
- `entregado` (Integer): Flag (0 = No, 1 = Sí).
- `legible` (Integer): Flag (0 = Ilegible, 1 = Legible).
- `fecha_emision` (DateTime): Fecha del documento.
- `inconsistencia_detectada` (Integer): Flag de sospecha (0 = No, 1 = Sí).
- `observacion` (Text): Detalles y notas técnicas.
