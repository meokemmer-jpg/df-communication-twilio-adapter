# df-communication-twilio-adapter — Output [CRUX-MK]
*Autonom aktiviert 2026-06-05T13:01:56.734706+00:00 | ollama-local/qwen2.5:14b-instruct*

# DF-COMMUNICATION-TWILIO-ADAPTER [CRUX-MK]

## Schnittstellendokumentation

### Senden von Nachrichten (`send_message`)

**URL:** `POST /v1/Accounts/{Sid}/Messages.json`

**Parameter:**

- **To**: Empfänger (E.164 Format)
- **From**: Absender (muss vor der Live-Aktivierung im Twilio-Konto registr
registriert sein)
- **Body**: Nachrichtentext (maximal 1600 Zeichen gemäß GSM-7 Kodierung)
- **Channel**: `sms` oder `whatsapp`

**Beispielanfrage:**

```json
{
    "To": "+4915234567890",
    "From": "+15005550006",  # Testnummer für Sandbox-Modus
    "Body": "Willkommen zum Twilio-SMS-WHATSAPP Test! Hier ist eine Prüfung
Prüfungs-Nachricht.",
    "Channel": "sms"
}
```

### Umgebungsvorbereitung

**1. Twilio-Konto erwerben:**

Gehen Sie zur [Twilio-Console](https://www.twilio.com/console), erstellen S
Sie ein Konto und erhalten Sie die Account-SID, den Auth-Token sowie eine r
registrierte Nummer.

**2. Umgebungsvariablen setzen:**

Führen Sie die folgenden Befehle aus:

```bash
export DF_TWILIO_REAL_ENABLED=true  # um reale Nachrichten zu senden (optio
(optional für Sandbox-Modus)
export TWILIO_ACCOUNT_SID=ACxxxx...
export TWILIO_AUTH_TOKEN=xxxx...    # nur in einem sicheren Umfeld speicher
speichern
```

**3. Live-Aktivierung:**

Fügen Sie den Phronesis-Ticket-Befehl hinzu:

```bash
export PHRONESIS_TICKET=PT-2026-05-13-W53-002  # nur für Live-Sendungen
```

### Beispielanwendungen

**SMS-Nachricht senden:**

```python
from df_communication_twilio_adapter import send_message

send_message(to="+4915234567890", from_="+15005550006", body="Willkommen!",
body="Willkommen!", channel="sms")
```

**WhatsApp-Nachricht senden:**

```python
from df_communication_twilio_adapter import send_message

send_message(to="+4915234567890", from_="+15005550006", body="Willkommen zu
zum WhatsApp-Test!", channel="whatsapp")
```

### Integration in eine existierende Anwendung

**Paket installieren:**

```bash
pip install df_communication_twilio_adapter==0.1.0
```

**Integration einrichten:**

```python
import os
from df_communication_twilio_adapter import send_message, init_twilio_adapt
init_twilio_adapter

# Umgebungsvariablen setzen (siehe oben)
init_twilio_adapter(os.environ)

send_message(to="+4915234567890", from_="+15005550006", body="Integration T
Test!", channel="sms")
```

### Tests

**Ablauf der Tests:**

```bash
cd ~/Projects/dark-factories/df-communication-twilio-adapter
python -m pytest tests/ -v
```

**Pflichttests:**

1. Default-Mock (ohne Umgebungsvariablen)
2. Test-SID für Sandbox-Modus (Umgebungsvariable gesetzt)
3. Fehlender Phronesis-Ticket in Live-Modus (Mock-Fallback)
4. Korrekte Live-Aktivierung mit PHRONESIS
5. E.164-Formatprüfung
6. WhatsApp-Prefix für E.164-Nr.
7. Ungültige Nummer ablehnen
8. Nachrichtenlänge über 1600 Zeichen ablehnen
9. Channel-Whitelist (nur sms, whatsapp)
10. Pflicht zur Tenant-ID-Angabe

### rho-Schaetzung

**Jährlicher Gewinn:** ~80k EUR (Pre-Stay-Erinnerungen + Upsell + Post-Stay
Post-Stay-Bewertungsanfragen)

**Kosten:** ~€0.05 pro SMS in Deutschland, ~€0.005 pro WhatsApp-Business-Na
WhatsApp-Business-Nachricht

**Marge pro Monat:** 600 Nachrichten = €30/Monat Marginalkosten

**Validierung:** Ungeprüft bis zum Pilot mit einer Laufzeit von mindestens 
30 Tagen