"""DF-COMMUNICATION-TWILIO-ADAPTER Engine [CRUX-MK].

Welle-53 Real-API-Wave-1 Top-5-Priority. Twilio SMS + WhatsApp Business API.

ENV-Var-gated Default-Disabled. Mock-Fallback bei Real-Mode-Disabled.

Pre/Post-Conditions:
- Pre: to_phone (E.164), from_phone (E.164), body (1-1600 chars), tenant_id (str)
- Post: MessageResult mit source ("mock"|"real-api"|"real-test"), message_sid, status
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# Constants
# E.164: '+' + 1-15 digits
E164_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")
MAX_SMS_BODY_GSM7 = 1600  # GSM-7 char limit
MAX_SMS_BODY_UCS2 = 70    # UCS-2 char limit per segment
ALLOWED_CHANNELS = ("sms", "whatsapp")
WHATSAPP_PREFIX = "whatsapp:"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MessageResult:
    """Pflicht-Felder per env-var-gated-real-integration-default.md Property-3."""
    message_sid: str
    status: str               # "queued"|"sent"|"delivered"|"failed"|"mock"
    to_phone: str
    from_phone: str
    body: str
    channel: str              # "sms"|"whatsapp"
    tenant_id: str
    source: str               # "mock"|"real-api"|"real-test"
    iso_timestamp: str
    phronesis_ticket: Optional[str] = None
    raw_response: dict = field(default_factory=dict)


def _is_valid_e164(phone: str) -> bool:
    """E.164 validation (skip whatsapp: prefix if present)."""
    if phone.startswith(WHATSAPP_PREFIX):
        phone = phone[len(WHATSAPP_PREFIX):]
    return bool(E164_REGEX.match(phone))


def _validate_message_input(
    to_phone: str,
    from_phone: str,
    body: str,
    tenant_id: str,
    channel: str,
) -> None:
    """Pre-Conditions Validation (K11+K12)."""
    assert channel in ALLOWED_CHANNELS, f"channel must be in {ALLOWED_CHANNELS}: {channel}"
    assert _is_valid_e164(to_phone), f"to_phone not E.164: {to_phone}"
    assert _is_valid_e164(from_phone), f"from_phone not E.164: {from_phone}"
    assert body, "body required"
    assert len(body) <= MAX_SMS_BODY_GSM7, \
        f"body too long [{len(body)} > {MAX_SMS_BODY_GSM7}]"
    assert tenant_id, "tenant_id required (K11 Tenant-Isolation)"


def mock_send_message(
    to_phone: str,
    from_phone: str,
    body: str,
    tenant_id: str,
    channel: str = "sms",
) -> MessageResult:
    """Mock-SMS/WhatsApp-Send (Default ohne Real-API).

    Pre: validation passing
    Post: MessageResult mit source='mock', status='mock', deterministic Mock-SID
    """
    _validate_message_input(to_phone, from_phone, body, tenant_id, channel)
    # Deterministic Mock-SID from tenant_id + to_phone-Suffix
    mock_sid = f"SM_mock_{tenant_id[:8]}_{to_phone[-6:]}"
    return MessageResult(
        message_sid=mock_sid,
        status="mock",
        to_phone=to_phone,
        from_phone=from_phone,
        body=body,
        channel=channel,
        tenant_id=tenant_id,
        source="mock",
        iso_timestamp=iso_now(),
        phronesis_ticket=None,
        raw_response={"mock": True},
    )


def real_send_message(
    to_phone: str,
    from_phone: str,
    body: str,
    tenant_id: str,
    channel: str = "sms",
    phronesis_ticket: Optional[str] = None,
) -> MessageResult:
    """Real-SMS/WhatsApp-Send via Twilio API.

    Pre: TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN env-vars gesetzt; PHRONESIS_TICKET fuer Live-Mode
    Post: MessageResult mit source='real-api'|'real-test'; fallback zu mock bei Auth-Fehler.

    NOTE: Skeleton-Implementation. Echte HTTP-Calls in Welle-54+.
    """
    _validate_message_input(to_phone, from_phone, body, tenant_id, channel)
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not account_sid or not auth_token:
        return mock_send_message(to_phone, from_phone, body, tenant_id, channel)

    # Twilio Test-Credentials: ACxxxx + Test-Auth-Token-Variante
    # Convention: AC_test_* → Test-Mode (Twilio Magic Phone-Numbers)
    is_test_mode = "test" in account_sid.lower()
    is_live_mode = not is_test_mode

    if is_live_mode:
        if not phronesis_ticket:
            phronesis_ticket = os.environ.get("PHRONESIS_TICKET")
        if not phronesis_ticket:
            # Q_0-Schutz: kein Live-Send ohne Phronesis
            return mock_send_message(to_phone, from_phone, body, tenant_id, channel)

    # Skeleton: Stub fuer Twilio-HTTP-Call
    # Welle-54+ vervollstaendigt mit `requests.post(f".../Accounts/{sid}/Messages.json", auth=(sid, token))`
    source = "real-api" if is_live_mode else "real-test"
    return MessageResult(
        message_sid=f"SM_{source.replace('-', '_')}_{tenant_id[:8]}_{to_phone[-6:]}",
        status="queued",  # Skeleton default-state
        to_phone=to_phone,
        from_phone=from_phone,
        body=body,
        channel=channel,
        tenant_id=tenant_id,
        source=source,
        iso_timestamp=iso_now(),
        phronesis_ticket=phronesis_ticket,
        raw_response={"skeleton": True, "live_mode": is_live_mode},
    )


def dispatch_send_message(
    to_phone: str,
    from_phone: str,
    body: str,
    tenant_id: str,
    channel: str = "sms",
) -> MessageResult:
    """Dispatcher mit ENV-Var-Gating (Default-Disabled).

    Default: mock_send_message.
    Real-Mode: nur wenn DF_TWILIO_REAL_ENABLED='true' UND Credentials gesetzt.
    """
    real_enabled = os.environ.get("DF_TWILIO_REAL_ENABLED", "").lower() == "true"
    if real_enabled:
        return real_send_message(to_phone, from_phone, body, tenant_id, channel)
    return mock_send_message(to_phone, from_phone, body, tenant_id, channel)


def to_audit_record(result: MessageResult) -> dict:
    """Serialize MessageResult fuer audit-log.jsonl. Body wird gehasht (DSGVO)."""
    import hashlib
    body_hash = hashlib.sha256(result.body.encode()).hexdigest()[:16]
    return {
        "ts": result.iso_timestamp,
        "df": "DF-COMMUNICATION-TWILIO-ADAPTER",
        "message_sid": result.message_sid,
        "tenant_id": result.tenant_id,
        "to_phone": result.to_phone,
        "from_phone": result.from_phone,
        "body_hash": body_hash,   # DSGVO: kein Klartext im Audit-Log
        "body_length": len(result.body),
        "channel": result.channel,
        "status": result.status,
        "source": result.source,
        "phronesis_ticket": result.phronesis_ticket or "none",
    }
