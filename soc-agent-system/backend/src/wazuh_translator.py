"""Validation and translation helpers for external Wazuh alert ingestion."""
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, field_validator

from models import ThreatSeverity, ThreatSignal, ThreatType

DEFAULT_CUSTOMER_NAME = "SeniorFraudShield"
SUPPORTED_WAZUH_RULE_ID = "100006"
MIN_SUPPORTED_WAZUH_LEVEL = 8


class WazuhValidationError(ValueError):
    """Raised when a Wazuh alert cannot be translated for Wave 1."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.field = field

    def to_detail(self) -> dict:
        detail = {"message": self.message}
        if self.field:
            detail["field"] = self.field
        return detail


class InvalidWazuhAlertError(WazuhValidationError):
    """Raised when an incoming Wazuh payload does not match the expected shape."""


class UnsupportedWazuhAlertError(WazuhValidationError):
    """Raised when a valid Wazuh payload is outside the supported Wave 1 scope."""


class WazuhMitrePayload(BaseModel):
    """MITRE ATT&CK metadata from Wazuh rule."""
    technique: Union[List[str], str, None] = None
    id: Union[List[str], str, None] = None
    tactic: Union[List[str], str, None] = None


class WazuhRulePayload(BaseModel):
    id: str
    level: int
    description: str
    groups: list[str] = Field(default_factory=list)
    firedtimes: int = 1
    mitre: Optional[WazuhMitrePayload] = None

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, value: object) -> object:
        return str(value) if value is not None else value

    @field_validator("groups", mode="before")
    @classmethod
    def normalize_groups(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return [group.strip() for group in value.split(",") if group.strip()]
        return value


class WazuhAgentPayload(BaseModel):
    id: str
    name: str


class WazuhManagerPayload(BaseModel):
    name: str


class WazuhDecoderPayload(BaseModel):
    name: str


class WazuhDataPayload(BaseModel):
    package_name: str


class WazuhAlertPayload(BaseModel):
    id: str
    timestamp: str
    location: str
    full_log: str
    rule: WazuhRulePayload
    agent: WazuhAgentPayload
    manager: WazuhManagerPayload
    decoder: WazuhDecoderPayload
    data: WazuhDataPayload


def severity_hint_from_rule_level(rule_level: int) -> ThreatSeverity:
    """Map Wazuh rule level to the initial AI-SOC severity hint."""
    if rule_level >= 15:
        return ThreatSeverity.CRITICAL
    if rule_level >= 12:
        return ThreatSeverity.HIGH
    if rule_level >= MIN_SUPPORTED_WAZUH_LEVEL:
        return ThreatSeverity.MEDIUM
    return ThreatSeverity.LOW


def parse_wazuh_timestamp(value: str) -> datetime:
    """Parse either the Wave 1 sample format or an ISO-8601 timestamp.

    Returns a timezone-naive UTC datetime to match the rest of the system.
    """
    try:
        return datetime.strptime(value, "%b %d, %Y @ %H:%M:%S.%f")
    except ValueError:
        pass

    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        # Convert to timezone-naive UTC to match system defaults
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError as exc:
        raise WazuhValidationError(
            "Unsupported Wazuh timestamp format",
            field="timestamp",
        ) from exc


def extract_endpoint_name(full_log: str) -> Optional[str]:
    """Extract the leading emulator/device prefix from a Wazuh full_log line."""
    prefix, separator, _ = full_log.partition(":")
    candidate = prefix.strip()
    if not separator or not candidate or " " in candidate:
        return None
    return candidate


def derive_initial_severity_hint(rule_level: int) -> ThreatSeverity:
    """Backward-compatible alias for the route-facing severity helper."""
    return severity_hint_from_rule_level(rule_level)


def extract_mitre_hints_from_wazuh(alert: Union[WazuhAlertPayload, dict]) -> List[str]:
    """
    Extract MITRE ATT&CK technique IDs from Wazuh alert rule metadata.

    Returns list of technique IDs (e.g. ["T1475", "T1533"]) or empty list.
    Never raises exceptions - returns [] on any error.

    Args:
        alert: Wazuh alert payload (either WazuhAlertPayload or dict)

    Returns:
        List of MITRE technique IDs starting with 'T'
    """
    try:
        # Extract mitre field from alert
        if isinstance(alert, dict):
            rule = alert.get("rule", {})
            mitre = rule.get("mitre", {})
        else:
            mitre = alert.rule.mitre if alert.rule.mitre else {}

        if not mitre:
            return []

        # Handle both dict and Pydantic model
        if isinstance(mitre, dict):
            techniques = mitre.get("technique")
        else:
            techniques = getattr(mitre, "technique", None)

        if not techniques:
            return []

        # Normalize to list
        if isinstance(techniques, str):
            techniques = [techniques]
        elif not isinstance(techniques, list):
            return []

        # Filter valid technique IDs (must start with 'T')
        return [t for t in techniques if isinstance(t, str) and t.startswith("T")]

    except Exception:
        # Graceful degradation - never crash the pipeline
        return []


def translate_wazuh_alert(alert: Union[WazuhAlertPayload, dict]) -> ThreatSignal:
    """Translate a supported Wazuh alert into an internal ThreatSignal."""
    if not isinstance(alert, WazuhAlertPayload):
        try:
            alert = WazuhAlertPayload.model_validate(alert)
        except ValidationError as exc:
            raise InvalidWazuhAlertError(
                "Invalid Wazuh alert payload",
            ) from exc

    if alert.rule.id != SUPPORTED_WAZUH_RULE_ID:
        raise UnsupportedWazuhAlertError(
            f"Wave 1 Wazuh ingestion only supports rule.id={SUPPORTED_WAZUH_RULE_ID}",
            field="rule.id",
        )

    severity_hint = severity_hint_from_rule_level(alert.rule.level)
    metadata = {
        "external_alert_id": alert.id,
        "rule_id": alert.rule.id,
        "wazuh_rule_level": alert.rule.level,
        "initial_severity_hint": severity_hint.value,
        "alert_summary": alert.rule.description,
        "rule_groups": alert.rule.groups,
        "repeat_count": alert.rule.firedtimes,
        "wazuh_agent_id": alert.agent.id,
        "wazuh_agent_name": alert.agent.name,
        "wazuh_manager_name": alert.manager.name,
        "decoder_name": alert.decoder.name,
        "package_name": alert.data.package_name,
        "log_message": alert.full_log,
        "wazuh_location": alert.location,
        "source_ip": alert.location,
    }

    endpoint_name = extract_endpoint_name(alert.full_log)
    if endpoint_name:
        metadata["endpoint_name"] = endpoint_name

    # Extract MITRE ATT&CK hints from Wazuh rule metadata
    mitre_hints = extract_mitre_hints_from_wazuh(alert)

    return ThreatSignal(
        threat_type=ThreatType.DEVICE_COMPROMISE,
        customer_name=DEFAULT_CUSTOMER_NAME,
        timestamp=parse_wazuh_timestamp(alert.timestamp),
        metadata=metadata,
        mitre_hints=mitre_hints,
    )