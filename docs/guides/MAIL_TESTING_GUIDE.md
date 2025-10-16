# 📧 Covina Mail Server Test & Setup

## Übersicht der Mail-Test Tools

### 🧪 Test-Scripts

1. **`simple_mail_test.py`** - Einfacher interaktiver Mail-Test
   - ✅ Schneller Verbindungstest
   - ✅ Test-E-Mail versenden
   - ✅ Interaktive Konfiguration
   - ✅ Funktioniert mit allen SMTP-Servern

2. **`test_mail_connection.py`** - Umfassender Mail-System Test
   - ✅ Template-basierte E-Mails
   - ✅ Integration mit Covina Mail Service
   - ✅ Detaillierte HTML-E-Mails
   - ✅ Umgebungsvariablen-Prüfung

### 🔧 Setup-Tools

3. **`setup_gmail.bat`** - Gmail SMTP Setup (Windows)
   - ✅ Automatische Gmail-Konfiguration
   - ✅ Umgebungsvariablen setzen
   - ✅ Direkte Verbindungstest
   - ✅ App-Passwort Anleitung

## 🚀 Schnellstart

### Option 1: Einfacher Test
```bash
# Interaktiver Test ohne Vorkonfiguration
python simple_mail_test.py
```

### Option 2: Gmail Setup (Windows)
```bash
# Gmail automatisch konfigurieren und testen
.\setup_gmail.bat
```

### Option 3: Manuelle Konfiguration
```bash
# Umgebungsvariablen setzen
$env:SMTP_SERVER='smtp.gmail.com'
$env:SMTP_USER='ihre-email@gmail.com'
$env:SMTP_PASSWORD='ihr-app-passwort'

# Test ausführen
python test_mail_connection.py
```

## 📧 Unterstützte Mail-Provider

### Gmail (Empfohlen)
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
```
**Setup:** App-Passwort erstellen → https://support.google.com/accounts/answer/185833

### Outlook/Hotmail
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

### Yahoo Mail
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

### Custom SMTP
```bash
SMTP_SERVER=mail.ihre-domain.de
SMTP_PORT=587 # oder 465, 25
SMTP_USE_TLS=true # oder false
```

## 🔍 Test-Ergebnisse verstehen

### ✅ Erfolgreiche Verbindung
```
✅ SMTP-Verbindung hergestellt
✅ TLS-Verschlüsselung aktiviert  
✅ Authentifizierung erfolgreich
✅ Test-E-Mail erfolgreich gesendet!
```

### ❌ Häufige Fehler

1. **Connection refused (Port 587/465/25)**
   - Firewall blockiert SMTP-Ports
   - ISP blockiert SMTP-Verkehr
   - Falscher SMTP-Server/Port

2. **Authentication failed**
   - Falsches Passwort
   - 2FA aktiviert → App-Passwort erforderlich
   - Account-Sicherheitseinstellungen

3. **TLS/SSL Errors**
   - Falsche Verschlüsselungseinstellungen
   - Veraltete TLS-Version
   - Zertifikatsprobleme

## 🛠️ Troubleshooting

### Gmail-spezifische Probleme
1. **"Less secure app access"** - Nicht mehr unterstützt!
   - ✅ **Lösung:** App-Passwort verwenden
   
2. **2-Factor Authentication**
   - ✅ **Lösung:** App-Passwort erstellen

3. **"Username and Password not accepted"**
   - ✅ Prüfen Sie das App-Passwort
   - ✅ E-Mail-Adresse vollständig eingeben

### Allgemeine Netzwerk-Probleme
1. **Proxy-Server**
   ```bash
   # Proxy-Einstellungen für Python
   $env:HTTP_PROXY='http://proxy:port'
   $env:HTTPS_PROXY='http://proxy:port'
   ```

2. **Corporate Firewall**
   - IT-Abteilung kontaktieren
   - Alternative Ports testen (465, 25)

3. **IPv6 vs IPv4**
   - Server-Adresse explizit verwenden
   - `smtp.gmail.com` → `74.125.133.108`

## 📋 Konfigurationsdatei

Für permanente Konfiguration erstellen Sie `.env` Datei:

```env
# .env Datei für Covina Mail-Konfiguration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=ihre-email@gmail.com
SMTP_PASSWORD=ihr-app-passwort
SMTP_USE_TLS=true
SMTP_SENDER_NAME=Covina System
TEST_RECIPIENT=admin@firma.de
NOTIFICATION_RECIPIENTS=admin@firma.de,team@firma.de
```

## 🎯 Integration in Covina Backend

Nach erfolgreichem Test ist das Mail-System bereit für:

1. **Job-Completion Benachrichtigungen**
2. **Error-Alerts**
3. **System-Status Updates**
4. **Batch-Processing Reports**

Das Backend lädt automatisch die Umgebungsvariablen und verwendet das konfigurierte Mail-System für alle Benachrichtigungen.

---

## 📞 Support

Bei Problemen:
1. **Mail-Test Logs** sammeln
2. **Umgebungsvariablen** prüfen
3. **Provider-Dokumentation** konsultieren
4. **Netzwerk-Konfiguration** überprüfen