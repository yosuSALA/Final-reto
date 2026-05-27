# 💾 Dataset Sintético de Siniestros y Pólizas — Aseguradora del Sur

Este directorio describe la fuente de datos sintética utilizada para entrenar el prototipo y validar las reglas de negocio.

## Estructura de Datos Sintéticos

La base de datos SQLite se crea en `backend/auditor.db` al iniciar la aplicación. Contiene datos de prueba realistas poblados a través de `backend/seed_data.py` y `backend/seed_fraud_data.py`.

### Resumen del Contenido Generado
- **Asegurados Sintéticos**: 17 asegurados con diferentes segmentos (VIP, Estándar, Básico) y niveles de frecuencia de reclamos.
- **Pólizas**: 20 pólizas con vigencias realistas, deducibles, sumas aseguradas y canales de venta.
- **Vehículos**: 12 vehículos mapeados a pólizas de automotores con placa, marca, modelo y año.
- **Siniestros**: 60 reclamos históricos distribuidos entre los ramos de vehículos, salud, vida, hogar y generales.
- **Documentos**: 230+ documentos digitales presentados en los siniestros (Cédulas, Licencias, Denuncias y Presupuestos) con estados de entrega y legibilidad variables.
- **Facturas de Talleres**: Facturas de talleres asociadas a reclamos de automóviles para auditar sobrecostos e incoherencias mecánicas.

## Casos de Prueba de Fraude Plantados

El dataset incluye 10 casos diseñados intencionadamente para activar alertas de alto riesgo (Alerta Roja):
1. **Siniestro SIN-6 (Borde de Vigencia)**: Ocurrió a las 24 horas del inicio de vigencia de la póliza y reclama el 92% de la suma asegurada.
2. **Siniestro SIN-7 (Demora Robo)**: Reportado 9 días después de la ocurrencia del robo del automóvil.
3. **Siniestro SIN-8 (Alta Frecuencia)**: Asegurado Juan Pérez presenta 4 siniestros acumulados en 12 meses y mora activa en su prima (falla RF03).
4. **Siniestro SIN-9 (Beneficiario Recurrente)**: Proveedor "Importadora Autopartes Express" reclama fondos cruzados bajo múltiples pólizas.
5. **Siniestro SIN-10 (Dinámica Sospechosa)**: Ocurrió a las 3:30 AM en zona despoblada de Guayaquil, sin testigos.
6. **Siniestro SIN-11 (Frecuencia Vehículo)**: Reclamos acumulados recurrentes sobre el mismo auto de Roberto Andrade.
7. **Siniestro SIN-12 (Narrativa Clonada)**: Descripción copiada textualmente de otro siniestro histórico para cobrar fondos duplicados.
8. **Siniestro SIN-14 (Fuera de Vigencia)**: Accidente de tránsito reportado después del vencimiento de la póliza (falla RF02).
9. **Siniestro SIN-15 (Ramo Inconsistente)**: Siniestro de colisión de auto ingresado en póliza contratada del ramo de Salud (falla RF01).
