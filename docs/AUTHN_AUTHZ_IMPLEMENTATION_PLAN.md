# AuthN/AuthZ Implementation Plan (OAuth2/JWT + RBAC)

Date: 21. Oktober 2025  
Scope: Covina Microservices (Main Backend 45678, Ingestion Backend 45679)

---

## Ziele
- Schütze sensible Endpunkte mit OAuth2 + JWT
- Rolle-basierte Autorisierung (RBAC) für admin, manager, user, guest
- Token-Ausstellung via /token (Password Grant für internen Gebrauch)
- Feature-Flag-basierter Rollout (ENABLE_AUTH=true)

## Anforderungen
- 401 für nicht authentifizierte Anfragen, 403 für unzureichende Rechte
- Rollen im JWT (claim: roles), Subject (sub), Issued At (iat), Exp (exp)
- ENV: JWT_SECRET, JWT_ALGORITHM=HS256, JWT_EXPIRES_MINUTES=60
- Backward-Kompatibilität: Dev-Modus ohne Auth (ENABLE_AUTH=false)

## Architektur
- FastAPI OAuth2PasswordBearer für Token-Übergabe (Authorization: Bearer <token>)
- jose für JWT-Encode/Decode
- RBAC-Dependency require_roles([...]) als Endpunkt-Decorator
- Minimaler User-Store (Platzhalter) → später PG-Integration

## Zu schützende Endpunkte (erste Welle)
- Ingestion Backend (45679):
  - POST /upload/*, /jobs/*, /recovery/* → roles: [admin, manager, user]
  - Admin-Only: /recovery/blocked-files, Unblock/Override → roles: [admin]
- Main Backend (45678):
  - /compliance/*, /gdpr/*, /review/* → roles: [admin, manager]

## API-Schnittstellen
- POST /token: username/password → { access_token, token_type }
- GET /me (optional): claims echo (Debug)

## Datenmodell (JWT Claims)
```json
{
  "sub": "user-id-or-name",
  "roles": ["admin", "manager"],
  "scopes": ["upload", "review"],
  "iat": 173,  
  "exp": 173
}
```

## Implementierungsschritte
1) Security-Modul anlegen (`security/auth.py`)
   - Role Enum, TokenData/Principal Models
   - create_access_token(), verify_jwt_token()
   - get_current_user(), require_roles([...]) Dependencies
2) Ingestion/Main Backends: Feature-Flag `ENABLE_AUTH`
   - Wenn true: OAuth2PasswordBearer registrieren
   - Endpunkte sukzessive mit require_roles([...]) schützen
3) /token-Endpunkt (als Startpunkt im Main Backend)
   - Platzhalter-Userstore (in-memory) mit Passwort-Hash (passlib später)
4) Tests
   - Token-Generierung, Expired/Invalid, RBAC 401/403, Happy Paths
5) Rollout
   - .env.production: ENABLE_AUTH=true, JWT_* gesetzt
   - Client-Dokumentation: Authorization Header

## Fehlermodi
- Ungültiger/abgelaufener Token → 401
- Fehlende Rolle → 403
- Fehlende Secrets → Startup-Fehler mit klarer Log-Meldung

## Sicherheitsnotizen
- Passwortspeicherung nur gehasht (passlib, später)
- Secrets nicht im Repo; Rotation dokumentieren
- TLS erzwingen (siehe Secrets & TLS/mTLS Todo)

## Testplan
- Unit: Token Encode/Decode, Exp, Fehlerfälle
- API: /token, /protected, /admin-only
- Last: 500 RPS /token (optional), protected endpoints 200 RPS

## Rollback
- ENABLE_AUTH=false in ENV → Endpunkte wieder offen (nur Dev/Staging)

## Zeitplan
- Tag 1: Security-Modul + /token + Basis-RBAC
- Tag 2: Endpunkt-Migration (Ingestion vorrangig) + Tests
- Tag 3: Main Backend Migration + Doku + Clients

## Akzeptanzkriterien
- Alle sensiblen Endpunkte geschützt, 401/403 korrekt
- Admin-Only-Pfade wirklich exklusiv
- Tests grün, Doku aktualisiert
