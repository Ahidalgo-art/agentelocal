# Runbook — Data governance para Gmail + Calendar

## 1. Objetivo

Establecer reglas específicas de tratamiento de datos para correo y agenda en este proyecto.

## 2. Clasificación de datos

### Nivel A — Credenciales

Incluye:
- refresh token
- access token
- referencias a secretos

Tratamiento:
- cifrado en reposo o uso de secret store local;
- no exponer en logs;
- acceso mínimo.

### Nivel B — Contenido sensible operativo

Incluye:
- cuerpos de correo;
- descripciones de eventos;
- asistentes;
- contexto del borrador.

Tratamiento:
- persistencia justificada por función;
- trazas reducidas;
- purga selectiva configurable.

### Nivel C — Metadata operativa

Incluye:
- ids remotos;
- timestamps;
- labels;
- estado del agente;
- scores y razones.

Tratamiento:
- persistencia amplia permitida para operación y auditoría.

## 3. Reglas

- R1: no loggear cuerpos completos de correo;
- R2: no loggear descripciones completas de eventos salvo entorno de debugging controlado;
- R3: usar hashes para detectar cambios de payload cuando sea suficiente;
- R4: toda exportación fuera del sistema debe pasar por aprobación explícita;
- R5: la auditoría debe capturar hechos, no secretos.

## 4. Purga y retención

- mensajes completos: política configurable por días;
- html bruto: purga preferente frente a texto normalizado;
- audit_event: retención más larga;
- propuestas de draft: conservar por valor de aprendizaje y trazabilidad.

## 5. Respuesta ante incidente

Si se detecta persistencia indebida o filtrado:
1. detener sync si el problema sigue activo;
2. registrar incidente;
3. identificar tablas/campos afectados;
4. ejecutar purga correctiva;
5. revisar masking y niveles de logging.
