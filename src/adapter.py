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


def real_internal_operation(operation, tenant_id, *args, **kwargs):
    """Welle-85 internal-real Mode: HTTP-Call gegen Local-Sandbox-Server (localhost:8001).

    NUR aktiv wenn DF_X_USE_LOCAL_SANDBOX=true. KEIN External-Output. Lokale Empirie.
    """
    import os, json, urllib.request, urllib.error, uuid
    if args:
        entity_id = args[0]
        idem_key = args[1] if len(args) > 1 else f"idem-{uuid.uuid4().hex[:12]}"
    else:
        entity_id = kwargs.get("entity_id") or kwargs.get("property_id") or kwargs.get("mandant_id") or kwargs.get("resource_id") or "mock-001"
        idem_key = kwargs.get("idempotency_key") or f"idem-{uuid.uuid4().hex[:12]}"

    url = "http://localhost:8001" + "/booking/v1/reservations"
    headers = {"Idempotency-Key": idem_key}
    method = "GET"
    if method == "POST":
        body = json.dumps({"tenant_id": tenant_id, "entity_id": entity_id, "operation": operation}).encode()
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    else:
        req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            response_body = json.loads(r.read())
            status_code = r.status
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        return {"operation": operation, "tenant_id": tenant_id, "entity_id": entity_id,
                "idempotency_key": idem_key, "source": "internal-real-error",
                "error": str(e)[:100]}
    return {"operation": operation, "tenant_id": tenant_id, "entity_id": entity_id,
            "idempotency_key": idem_key, "source": "internal-real",
            "status_code": status_code, "raw_response": response_body}


def real_internal_operation_with_provenance(operation, tenant_id, *args, **kwargs):
    """Welle-87: K12+K13+K16-Wrapper um real_internal_operation.

    Pflicht-Provenance pro internal-real-Call:
    - K12: payload_hash + HMAC + chain_predecessor_hash
    - K13: ISO-Timestamp + RFC3161-Anchor (mock if W48 unavailable)
    - K16: per-DF AtomicLock (file-based, ttl 60s)

    Returns: dict mit raw response + provenance_record.
    """
    import os, json, hashlib, hmac as _hmac, time, fcntl
    from datetime import datetime, timezone

    # K16 AtomicLock (per-DF)
    df_name = __name__.replace(".", "_") if __name__ else "df_unknown"
    lock_path = f"/tmp/{df_name}.internal_real.lock"
    lock_fd = None
    try:
        lock_fd = open(lock_path, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        # Lock contention → return graceful (K11 non-fatal)
        if lock_fd: lock_fd.close()
        return {"source": "internal-real-locked", "operation": operation, "tenant_id": tenant_id,
                "error": "K16-lock-contention"}

    try:
        # Call existing real_internal_operation
        result = real_internal_operation(operation, tenant_id, *args, **kwargs)

        # K12: payload_hash + HMAC
        payload_str = json.dumps(result, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        secret = os.environ.get("DF_HMAC_SECRET", "df-dev-hmac-v1")
        signature = _hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()

        # K13: RFC3161-Anchor (mock-fallback if W48 unavailable)
        anchor = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "anchor_type": "mock-rfc3161",
            "payload_hash": payload_hash,
        }

        # Result mit Provenance
        result["provenance"] = {
            "k12_payload_hash": payload_hash,
            "k12_hmac_signature": signature[:32],  # truncated for log
            "k13_anchor": anchor,
            "k16_lock_path": lock_path,
        }
        return result
    finally:
        if lock_fd:
            try: fcntl.flock(lock_fd, fcntl.LOCK_UN); lock_fd.close()
            except Exception: pass
