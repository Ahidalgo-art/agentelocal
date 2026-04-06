# Política de secretos y configuración por entorno

## Objetivo
Evitar exposición de secretos y eliminar defaults inseguros en entornos no `dev`.

## Reglas
1. Nunca guardar secretos en el repositorio.
2. Toda variable sensible debe provenir de secret manager o variables de entorno del entorno de despliegue.
3. En `prod` y `preprod`, el arranque debe fallar si falta cualquier secreto requerido.
4. Defaults de conveniencia solo permitidos en `local/dev` y claramente identificados.
5. Rotación de credenciales obligatoria y auditable.

## Clasificación mínima
- **Secreto:** API keys, tokens, credenciales DB, webhook secrets.
- **Config no secreta:** puertos, flags de feature, niveles de log.

## Matriz de entorno
| Variable | Local/Dev | Test/CI | Preprod/Prod |
|---|---|---|---|
| Credenciales sensibles | Permitido via `.env.local` no versionado | Secrets CI | Secret manager obligatorio |
| Defaults inseguros | Permitidos para acelerar desarrollo | Desaconsejado | Prohibido |
| Fail-fast por secreto faltante | Recomendado | Recomendado | Obligatorio |

## Controles de verificación
- Checklist en PR para cambios de configuración.
- Escaneo de secretos en CI.
- Validación de variables obligatorias en arranque.

## Evidencia mínima
- Lista de variables obligatorias por entorno.
- Resultado de escaneo de secretos en CI.
- Evidencia de fail-fast en entorno no dev (si falta secreto).

## Variables obligatorias por entorno

### Local/Dev
- `ENVIRONMENT`
- `DATABASE_URL`

### Test/CI
- `ENVIRONMENT=test`
- `DATABASE_URL` (inyectada por secrets del pipeline)

### Preprod/Prod
- `ENVIRONMENT` (`preprod` o `prod`)
- `DATABASE_URL` (secret manager obligatorio)
- Cualquier credencial de integración habilitada (ejemplo: Google OAuth)

## Implementación mínima en AgenteLocal
- Plantilla segura versionada: `backend/.env.example`.
- Archivos de secretos locales excluidos de git: `.gitignore` (`.env`, `backend/.env`, variantes).
- Fail-fast de base de datos: la app lanza error si `DATABASE_URL` no está configurada.

## Checklist operativo de validación
1. Confirmar que no hay secretos reales en archivos versionados.
2. Confirmar que `.env` y `backend/.env` están ignorados por git.
3. Confirmar que `backend/.env.example` existe y no contiene valores sensibles reales.
4. Ejecutar arranque en entorno no dev sin `DATABASE_URL` y validar fail-fast controlado.
5. Registrar evidencia en PR (comandos ejecutados + resultados).
