"""Tests for Wazuh alert translation into ThreatSignal."""
from copy import deepcopy
from datetime import datetime
import sys

import pytest

sys.path.insert(0, 'src')

from models import ThreatSeverity, ThreatType
from wazuh_translator import (
    InvalidWazuhAlertError,
    UnsupportedWazuhAlertError,
    extract_mitre_hints_from_wazuh,
    severity_hint_from_rule_level,
    translate_wazuh_alert,
)


def build_sample_wazuh_alert():
    """Return a representative Wazuh alert payload for rule 100006."""
    return {
        "input": {"type": "log"},
        "agent": {"name": "wazuh.manager", "id": "000"},
        "manager": {"name": "wazuh.manager"},
        "data": {"package_name": "sk.madzik.android.logcatudp"},
        "rule": {
            "firedtimes": 3,
            "mail": True,
            "level": 15,
            "description": "Malicions Android app installed: sk.madzik.android.logcatudp",
            "groups": "android, package, installandroid_install",
            "id": "100006",
        },
        "location": "192.168.65.1",
        "decoder": {"name": "android_decoder_03"},
        "id": "1774133781.1718",
        "full_log": "emulator-5554: D/BackupManagerService( 1198): Received broadcast Intent { act=android.intent.action.PACKAGE_ADDED dat=package:sk.madzik.android.logcatudp flg=0x4000010 (has extras) }",
        "timestamp": "Mar 21, 2026 @ 15:56:21.984",
        "_index": "wazuh-alerts-4.x-2026.03.21",
    }


def test_translate_wazuh_rule_100006_to_threat_signal():
    """Supported Wazuh alerts should map to a curated ThreatSignal."""
    signal = translate_wazuh_alert(build_sample_wazuh_alert())

    assert signal.customer_name == "SeniorFraudShield"
    assert signal.threat_type == ThreatType.DEVICE_COMPROMISE
    assert signal.timestamp == datetime(2026, 3, 21, 15, 56, 21, 984000)
    assert signal.metadata == {
        "external_alert_id": "1774133781.1718",
        "rule_id": "100006",
        "wazuh_rule_level": 15,
        "initial_severity_hint": ThreatSeverity.CRITICAL.value,
        "alert_summary": "Malicions Android app installed: sk.madzik.android.logcatudp",
        "rule_groups": ["android", "package", "installandroid_install"],
        "repeat_count": 3,
        "wazuh_agent_id": "000",
        "wazuh_agent_name": "wazuh.manager",
        "wazuh_manager_name": "wazuh.manager",
        "decoder_name": "android_decoder_03",
        "package_name": "sk.madzik.android.logcatudp",
        "source_ip": "192.168.65.1",
        "wazuh_location": "192.168.65.1",
        "endpoint_name": "emulator-5554",
        "log_message": "emulator-5554: D/BackupManagerService( 1198): Received broadcast Intent { act=android.intent.action.PACKAGE_ADDED dat=package:sk.madzik.android.logcatudp flg=0x4000010 (has extras) }",
    }


@pytest.mark.parametrize(
    ("rule_level", "expected_hint"),
    [
        (15, ThreatSeverity.CRITICAL),
        (12, ThreatSeverity.HIGH),
        (8, ThreatSeverity.MEDIUM),
        (7, ThreatSeverity.LOW),
    ],
)
def test_severity_hint_from_rule_level(rule_level, expected_hint):
    """Wazuh rule levels should map to the expected severity hints."""
    assert severity_hint_from_rule_level(rule_level) == expected_hint


@pytest.mark.parametrize(
    "payload",
    [
        "not-a-dict",
        {"rule": "not-a-dict"},
        {"rule": {"id": "100006", "level": "critical"}, "timestamp": "Mar 21, 2026 @ 15:56:21.984"},
    ],
)
def test_translate_rejects_invalid_payload_shapes(payload):
    """Malformed payloads should raise an invalid alert error."""
    with pytest.raises(InvalidWazuhAlertError):
        translate_wazuh_alert(payload)


def test_translate_rejects_unsupported_rule_ids():
    """Structurally valid but unsupported rules should be rejected cleanly."""
    payload = deepcopy(build_sample_wazuh_alert())
    payload["rule"]["id"] = "999999"

    with pytest.raises(UnsupportedWazuhAlertError):
        translate_wazuh_alert(payload)


# MITRE Extraction Tests


def test_extract_mitre_hints_with_technique_list():
    """Test extraction of MITRE techniques from list."""
    alert = {
        "rule": {
            "id": "100006",
            "level": 15,
            "description": "Test",
            "mitre": {"technique": ["T1475", "T1533"]}
        }
    }

    hints = extract_mitre_hints_from_wazuh(alert)

    assert hints == ["T1475", "T1533"]


def test_extract_mitre_hints_with_single_technique_string():
    """Test extraction with single technique as string."""
    alert = {
        "rule": {
            "mitre": {"technique": "T1046"}
        }
    }

    hints = extract_mitre_hints_from_wazuh(alert)

    assert hints == ["T1046"]


def test_extract_mitre_hints_no_mitre_field():
    """Test graceful handling when mitre field is missing."""
    alert = {
        "rule": {
            "id": "100006",
            "level": 15,
            "description": "Test"
        }
    }

    hints = extract_mitre_hints_from_wazuh(alert)

    assert hints == []


def test_extract_mitre_hints_invalid_technique_format():
    """Test graceful handling of malformed technique data."""
    alert = {
        "rule": {
            "mitre": {"technique": 12345}  # Invalid type
        }
    }

    hints = extract_mitre_hints_from_wazuh(alert)

    assert hints == []


def test_extract_mitre_hints_filters_non_t_prefixed():
    """Test that non-T-prefixed IDs are filtered out."""
    alert = {
        "rule": {
            "mitre": {"technique": ["T1475", "INVALID", "T1533", "123"]}
        }
    }

    hints = extract_mitre_hints_from_wazuh(alert)

    assert hints == ["T1475", "T1533"]


def test_translate_includes_mitre_hints():
    """Test that translate_wazuh_alert includes mitre_hints in signal."""
    alert = deepcopy(build_sample_wazuh_alert())
    alert["rule"]["mitre"] = {"technique": ["T1475", "T1533"]}

    signal = translate_wazuh_alert(alert)

    assert signal.mitre_hints == ["T1475", "T1533"]


def test_translate_empty_mitre_hints_when_no_mitre():
    """Test that translate returns empty mitre_hints when no MITRE data."""
    alert = build_sample_wazuh_alert()
    # No mitre field in alert

    signal = translate_wazuh_alert(alert)

    assert signal.mitre_hints == []