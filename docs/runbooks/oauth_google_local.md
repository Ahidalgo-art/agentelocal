# Runbook — OAuth Google local

## 1. Objetivo

Operar correctamente el alta, renovación y recuperación de credenciales OAuth para Gmail + Google Calendar en entorno local.

## 2. Señales de funcionamiento correcto

- la cuenta aparece activa en `workspace_account`;
- existe credencial válida o referencia equivalente en `oauth_credential_ref`;
- el hash de scopes coincide con la configuración esperada;
- los syncs incrementales pueden ejecutarse.

## 3. Alta inicial

1. Registrar la aplicación OAuth para uso local.
2. Configurar redirect URI apropiada para aplicación instalada.
3. Solicitar scopes mínimos necesarios.
4. Completar consentimiento.
5. Persistir referencia de credenciales.
6. Ejecutar sync inicial completo.
7. Verificar tablas pobladas y cursores persistidos.

## 4. Operación normal

- refrescar access token cuando corresponda;
- registrar estado de expiración;
- no exponer tokens en logs;
- invalidar la sesión local si el refresh falla por revocación o cambio de scopes.

## 5. Síntomas frecuentes y diagnóstico

### Síntoma: `reauth_required`

Posibles causas:
- revocación manual del acceso;
- cambio de scopes;
- app OAuth reconfigurada;
- refresh token inválido.

Acciones:
- marcar cuenta como no operable para sync/draft;
- emitir `audit_event`;
- lanzar flujo de reautorización.

### Síntoma: Gmail funciona pero Calendar no

Posibles causas:
- scopes parciales;
- consentimiento incompleto;
- credencial antigua.

Acciones:
- comparar scopes efectivos;
- forzar reauth con set correcto.

## 6. Verificaciones post-incidente

- sync Gmail OK
- sync Calendar OK
- cursores actualizados
- creación de draft de prueba OK en entorno seguro
- auditoría del incidente cerrada
