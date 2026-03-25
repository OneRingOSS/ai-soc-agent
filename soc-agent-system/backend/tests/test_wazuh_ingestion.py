"""Wave 1 tests for the additive Wazuh ingestion contract."""
import copy
import sys

import pytest

sys.path.insert(0, 'src')

from models import ThreatType
from wazuh_translator import (
    DEFAULT_CUSTOMER_NAME,
    InvalidWazuhAlertError,
    UnsupportedWazuhAlertError,
    translate_wazuh_alert,
)


@pytest.fixture
def sample_wazuh_alert():
    return {
        "id": "1774133781.1718",
        "timestamp": "Mar 21, 2026 @ 15:56:21.984",
        "location": "192.168.65.1",
        "full_log": "emulator-5554: D/BackupManagerService( 1198): Received broadcast Intent { act=android.intent.action.PACKAGE_ADDED dat=package:sk.madzik.android.logcatudp flg=0x4000010 (has extras) }",
        "rule": {
            "id": "100006",
            "level": 15,
            "description": "Malicious Android app installed: sk.madzik.android.logcatudp",
            "groups": ["android", "package", "installandroid_install"],
            "firedtimes": 3,
        },
        "agent": {"id": "000", "name": "wazuh.manager"},
        "manager": {"name": "wazuh.manager"},
        "decoder": {"name": "android_decoder_03"},
        "data": {"package_name": "sk.madzik.android.logcatudp"},
    }


def test_translate_wazuh_alert_maps_rule_100006(sample_wazuh_alert):
    signal = translate_wazuh_alert(sample_wazuh_alert)

    assert signal.threat_type == ThreatType.DEVICE_COMPROMISE
    assert signal.customer_name == DEFAULT_CUSTOMER_NAME
    assert signal.metadata["source_ip"] == "192.168.65.1"
    assert signal.metadata["wazuh_location"] == "192.168.65.1"
    assert signal.metadata["package_name"] == "sk.madzik.android.logcatudp"
    assert signal.metadata["initial_severity_hint"] == "CRITICAL"
    assert signal.metadata["endpoint_name"] == "emulator-5554"
    assert "rule" not in signal.metadata
    assert "agent" not in signal.metadata
    assert "data" not in signal.metadata


def test_translate_wazuh_alert_rejects_unsupported_rule(sample_wazuh_alert):
    unsupported = copy.deepcopy(sample_wazuh_alert)
    unsupported["rule"]["id"] = "999999"

    with pytest.raises(UnsupportedWazuhAlertError, match="rule.id=100006"):
        translate_wazuh_alert(unsupported)


def test_translate_wazuh_alert_rejects_invalid_payload_shape():
    with pytest.raises(InvalidWazuhAlertError, match="Invalid Wazuh alert payload"):
        translate_wazuh_alert({"rule": "invalid"})


def test_wazuh_ingestion_endpoint_returns_normalized_signal(test_client, sample_wazuh_alert):
    response = test_client.post("/api/threats/ingest/wazuh", json=sample_wazuh_alert)

    assert response.status_code == 202
    data = response.json()
    assert data["customer_name"] == DEFAULT_CUSTOMER_NAME
    assert data["threat_type"] == "device_compromise"
    assert data["metadata"]["source_ip"] == "192.168.65.1"
    assert data["metadata"]["initial_severity_hint"] == "CRITICAL"


def test_wazuh_ingestion_endpoint_returns_clear_validation_error(test_client, sample_wazuh_alert):
    invalid = copy.deepcopy(sample_wazuh_alert)
    invalid["rule"]["id"] = "200000"

    response = test_client.post("/api/threats/ingest/wazuh", json=invalid)

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "message": "Wave 1 Wazuh ingestion only supports rule.id=100006",
        "field": "rule.id",
    }


def test_wazuh_ingestion_endpoint_returns_clear_malformed_payload_error(test_client):
    response = test_client.post("/api/threats/ingest/wazuh", json={"rule": "invalid"})

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "message": "Invalid Wazuh alert payload",
    }


def test_wazuh_ingestion_endpoint_keeps_trigger_route_unchanged(test_client):
    response = test_client.post("/api/threats/trigger", json={"threat_type": "bot_traffic"})

    assert response.status_code == 200
    assert response.json()["signal"]["threat_type"] == "bot_traffic"