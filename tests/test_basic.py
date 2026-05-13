"""Basic Tests fuer DF-COMMUNICATION-TWILIO-ADAPTER [CRUX-MK].

Per env-var-gated-real-integration-default.md Pflicht-Tests:
1. Default-Mock-Test
2. ENV-True + test-credentials → real-test
3. ENV-True + live-credentials ohne PHRONESIS → mock-fallback (Q_0-Schutz)
4. E.164-Validation (to_phone + from_phone)
5. Body-Length-Validation
6. Channel-Whitelist (sms/whatsapp)
7. Tenant-ID-Pflicht
8. Audit-Record DSGVO (body-hash statt body)
"""
from __future__ import annotations

import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.adapter import (
    ALLOWED_CHANNELS,
    MAX_SMS_BODY_GSM7,
    MessageResult,
    mock_send_message,
    real_send_message,
    dispatch_send_message,
    to_audit_record,
    _is_valid_e164,
)


def _clear_env(monkeypatch):
    monkeypatch.delenv("DF_TWILIO_REAL_ENABLED", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("PHRONESIS_TICKET", raising=False)


def test_default_mock_no_env(monkeypatch):
    """Default-Mock: keine ENV-Var → mock_send_message."""
    _clear_env(monkeypatch)
    result = dispatch_send_message(
        to_phone="+4915112345678",
        from_phone="+4915198765432",
        body="Test message",
        tenant_id="hildesheim",
    )
    assert result.source == "mock"
    assert result.status == "mock"
    assert result.message_sid.startswith("SM_mock_")
    assert result.channel == "sms"


def test_env_true_test_mode(monkeypatch):
    """ENV=true + Test-SID → real-test."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("DF_TWILIO_REAL_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC_test_dummy")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")
    result = dispatch_send_message(
        to_phone="+15005550006",  # Twilio Magic Test-Number
        from_phone="+15005550006",
        body="Test SMS",
        tenant_id="hildesheim",
    )
    assert result.source == "real-test"


def test_env_true_live_without_phronesis_fallback(monkeypatch):
    """ENV=true + Live-SID ohne PHRONESIS → mock-fallback (Q_0-Schutz)."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("DF_TWILIO_REAL_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxlive")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "live_dangerous_token")
    # NO PHRONESIS_TICKET
    result = dispatch_send_message(
        to_phone="+4915112345678",
        from_phone="+4915198765432",
        body="Live attempt",
        tenant_id="hildesheim",
    )
    assert result.source == "mock", "Live ohne Phronesis MUSS mock-fallback (Q_0)"


def test_env_true_live_with_phronesis(monkeypatch):
    """ENV=true + Live-SID + PHRONESIS → real-api."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("DF_TWILIO_REAL_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxlive")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "live_token")
    monkeypatch.setenv("PHRONESIS_TICKET", "PT-2026-05-13-W53-002")
    result = dispatch_send_message(
        to_phone="+4915112345678",
        from_phone="+4915198765432",
        body="Live with phronesis",
        tenant_id="hildesheim",
    )
    assert result.source == "real-api"
    assert result.phronesis_ticket == "PT-2026-05-13-W53-002"


def test_e164_validation():
    """E.164 Phone-Format Validation."""
    assert _is_valid_e164("+4915112345678") is True
    assert _is_valid_e164("+15005550006") is True
    assert _is_valid_e164("4915112345678") is False  # missing +
    assert _is_valid_e164("+0123") is False  # starts with 0 after +
    assert _is_valid_e164("") is False


def test_e164_validation_whatsapp_prefix():
    """E.164 mit whatsapp:-Prefix erlaubt."""
    assert _is_valid_e164("whatsapp:+4915112345678") is True


def test_validation_invalid_to_phone():
    """Invalid to_phone wird abgelehnt."""
    with pytest.raises(AssertionError):
        mock_send_message("0151234", "+4915198765432", "Test", "t1", "sms")


def test_validation_body_too_long():
    """Body > 1600 GSM-7 Zeichen abgelehnt."""
    long_body = "x" * (MAX_SMS_BODY_GSM7 + 1)
    with pytest.raises(AssertionError):
        mock_send_message("+4915112345678", "+4915198765432", long_body, "t1", "sms")


def test_validation_channel_whitelist():
    """Channel muss in ALLOWED_CHANNELS."""
    with pytest.raises(AssertionError):
        mock_send_message("+4915112345678", "+4915198765432", "Test", "t1", "email")


def test_validation_missing_tenant_id():
    """tenant_id Pflicht (K11)."""
    with pytest.raises(AssertionError):
        mock_send_message("+4915112345678", "+4915198765432", "Test", "", "sms")


def test_validation_empty_body():
    """Body Pflicht."""
    with pytest.raises(AssertionError):
        mock_send_message("+4915112345678", "+4915198765432", "", "t1", "sms")


def test_whatsapp_channel():
    """WhatsApp-Channel erlaubt."""
    result = mock_send_message(
        to_phone="whatsapp:+4915112345678",
        from_phone="whatsapp:+4915198765432",
        body="WhatsApp message",
        tenant_id="hildesheim",
        channel="whatsapp",
    )
    assert result.channel == "whatsapp"
    assert result.source == "mock"


def test_audit_record_dsgvo_body_hash():
    """Audit-Record loggt body_hash statt body (DSGVO)."""
    result = mock_send_message(
        "+4915112345678", "+4915198765432",
        "Sensitive PII data", "tenant_dsgvo", "sms",
    )
    rec = to_audit_record(result)
    assert "body" not in rec, "body MUSS NICHT im Audit (DSGVO)"
    assert "body_hash" in rec
    assert "body_length" in rec
    assert rec["body_length"] == len("Sensitive PII data")
    assert rec["df"] == "DF-COMMUNICATION-TWILIO-ADAPTER"
