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

1. **Borde de Vigencia**: Ocurrió a las 24 horas del inicio de vigencia de la póliza y reclama el 92% de la suma asegurada.
2. **Demora Robo**: Reportado 9 días después de la ocurrencia del robo del automóvil.
3. **Alta Frecuencia**: Asegurado con 4 siniestros acumulados en 12 meses y mora activa en su prima (falla RF03).
4. **Beneficiario Recurrente**: Proveedor "Importadora Autopartes Express" reclama fondos cruzados bajo múltiples pólizas.
5. **Dinámica Sospechosa**: Ocurrió a las 3:30 AM en zona despoblada, sin testigos.
6. **Frecuencia Vehículo**: Reclamos acumulados recurrentes sobre el mismo auto.
7. **Narrativa Clonada**: Descripción copiada textualmente de otro siniestro histórico para cobrar fondos duplicados.
8. **Monto Cercano a Suma Asegurada**: 98% de suma asegurada reclamado.
9. **Fuera de Vigencia**: Accidente de tránsito reportado después del vencimiento de la póliza (falla RF02).
10. **Ramo Inconsistente**: Siniestro de colisión de auto ingresado en póliza contratada del ramo de Salud (falla RF01).

## Motor de IA

Los datos sintéticos son auditados por **DeepSeek V4 Flash** vía OpenCode Go, que analiza:
- Sobrecobros contra tarifario maestro.
- Duplicados e incoherencias mecánicas.
- Inconsistencias entre documentos del expediente.
- Señales de riesgo cruzadas con historial.

## Notas

- Todos los datos son completamente ficticios y no representan asegurados reales.
- Los patrones de fraude plantados siguen la rúbrica oficial del reto HackIAthon 2026.
- El seed se ejecuta automáticamente al iniciar la aplicación.
