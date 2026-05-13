# DF-COMMUNICATION-TWILIO-ADAPTER [CRUX-MK]

**Welle-53 Real-API-Wave-1 Top-5-Priority Foundation-DF**
**Version:** 0.1.0-SKELETON
**Status:** SKELETON-CONDITIONAL
**Domain:** communication / sms-whatsapp

## Scope

Real-API-Adapter fuer Twilio Messaging (SMS + WhatsApp Business).
ENV-Var-Gated Default-Disabled. **KEIN Live-Send ohne PHRONESIS_TICKET** (Q_0-Schutz).
Test-Credentials (AC_test_*) erlaubt ohne Phronesis fuer Dev/Sandbox.

## Operations

- `send_message`: POST /v1/Accounts/{Sid}/Messages.json
- E.164-Phone-Validation (Pflicht)
- Body-Length-Limit (1600 GSM-7 char)
- Channel: sms | whatsapp (Whitelist)
- DSGVO: Body wird als SHA256-Hash im Audit-Log gespeichert (kein Klartext)

## Real-API-Activation-Workflow

1. **Twilio-Console:** Account-SID + Auth-Token + From-Phone-Number erwerben
2. **Phronesis-Approval** (nur Live-Mode)
3. **ENV-Vars setzen:**
   ```bash
   export DF_TWILIO_REAL_ENABLED=true
   export TWILIO_ACCOUNT_SID=ACxxxx...
   export TWILIO_AUTH_TOKEN=xxxx...
   export PHRONESIS_TICKET=PT-2026-05-13-W53-002  # nur Live-Mode
   ```
4. **Twilio-Magic-Numbers:** +15005550006 (Test-OK), +15005550001 (Test-Invalid)
5. **WhatsApp-Sandbox:** Twilio WhatsApp Sandbox-Mode fuer Dev (Self-Join via Twilio-Console)

## Strict-Conditions-Konformitaet

- KEIN Live-Send ohne PHRONESIS_TICKET (Q_0-Schutz)
- E.164-Phone-Format Pflicht (K12 non-LLM-validation)
- Body-Length-Limit (1600 GSM-7) Pflicht
- Channel-Whitelist [sms, whatsapp]
- Tenant-Isolation Pflicht (K11, hotel_id)
- DSGVO: body-hash statt body im Audit-Log

## CRUX-Bindung

- **K_0:** indirekt (Upsell-Revenue via WhatsApp-Business)
- **Q_0:** Gast-Privacy via E.164-Validation + DSGVO-Body-Hash
- **W_0:** Hotel-Front-Desk-Zeit reduziert
- **L_Martin:** Live-Mode explicit Phronesis-Trigger

## rho-Schaetzung

- **Annual:** ~80k EUR (Pre-Stay-Reminder + Upsell + Post-Stay Review-Request)
- **Cost:** ~€0.05 per SMS (DE), ~€0.005 per WhatsApp-Business
- **Lambda:** ~600/Mo = ~€30/Mo Marginal-Cost
- **Validation:** unvalidated bis Pilot 30+ Tage

## Tests

```bash
cd ~/Projects/dark-factories/df-communication-twilio-adapter
python -m pytest tests/ -v
```

13 Pflicht-Tests:
1. Default-Mock (no ENV) → mock
2. ENV-True + Test-SID → real-test
3. ENV-True + Live-SID ohne PHRONESIS → mock-fallback
4. ENV-True + Live-SID + PHRONESIS → real-api
5. E.164-Validation
6. E.164-Validation WhatsApp-Prefix
7. Invalid to_phone Reject
8. Body-Length > 1600 Reject
9. Channel-Whitelist
10. Tenant-ID Pflicht
11. Empty-Body Reject
12. WhatsApp-Channel erlaubt
13. Audit-Record DSGVO (body-hash, kein Klartext)

## Promotion-Pfad

- v0.1.0-SKELETON (jetzt): Mock + E.164-Validation + Skeleton-Stub
- v0.2.0 (Welle-54): Cross-LLM-Wargame + Real-HTTP-Implementation
- v0.3.0 (Welle-55+): Twilio-Sandbox-Pilot 30 Tage
- v1.0.0: PRODUCTION-READY-CONDITIONAL (Live-Pilot Year-1)

## Beziehung zu anderen Rules+Skills

- **Verstaerkt** `rules/env-var-gated-real-integration-default.md`
- **Verstaerkt** `rules/df-akzeptanz-kriterien.md` K11-K16 + LC1-LC5
- **Komplementaer zu** `df-pms-opera-adapter` (Pre-Stay-Reminder-Pipeline)
- **Komplementaer zu** `df-communication-sendgrid-adapter` (Multi-Channel: SMS + Email)

[CRUX-MK]
