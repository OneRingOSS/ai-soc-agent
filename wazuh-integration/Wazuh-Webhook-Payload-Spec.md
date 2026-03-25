# Wazuh Webhook Payload Specification for AI-SOC Integration

## Purpose

This document defines the **exact JSON payload format** that Wazuh must send to the AI-SOC ingestion endpoint. This specification is derived from the integration tests that verify the Wazuh → AI-SOC contract.

## AI-SOC Ingestion Endpoint

**URL:** `POST /api/threats/ingest/wazuh`  
**Content-Type:** `application/json`  
**Expected Response:** `202 Accepted`

## Required Payload Schema

### Top-Level Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | ✅ Yes | Unique Wazuh alert ID | `"1774133781.1718"` |
| `timestamp` | string | ✅ Yes | Alert timestamp (see formats below) | `"Mar 21, 2026 @ 15:56:21.984"` |
| `location` | string | ✅ Yes | Source IP/location (mapped to `source_ip`) | `"192.168.65.1"` |
| `full_log` | string | ✅ Yes | Complete log message (used to extract endpoint) | `"emulator-5554: D/BackupManagerService..."` |
| `rule` | object | ✅ Yes | Rule information (see below) | `{...}` |
| `agent` | object | ✅ Yes | Wazuh agent information (see below) | `{...}` |
| `manager` | object | ✅ Yes | Wazuh manager information (see below) | `{...}` |
| `decoder` | object | ✅ Yes | Decoder information (see below) | `{...}` |
| `data` | object | ✅ Yes | Decoded data fields (see below) | `{...}` |

### `rule` Object

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | ✅ Yes | Rule ID (must be `"100006"` for Wave 1) | `"100006"` |
| `level` | integer | ✅ Yes | Severity level (8-15+) | `15` |
| `description` | string | ✅ Yes | Human-readable description | `"Malicious Android app installed: sk.madzik.android.logcatudp"` |
| `groups` | array[string] | ✅ Yes | Rule groups/tags | `["android", "package", "installandroid_install"]` |
| `firedtimes` | integer | ✅ Yes | Number of times rule has fired | `3` |

**Note:** `rule.groups` can be either:
- Array: `["android", "package", "installandroid_install"]`
- Comma-separated string: `"android, package, installandroid_install"` (will be parsed)

### `agent` Object

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | ✅ Yes | Wazuh agent ID | `"000"` |
| `name` | string | ✅ Yes | Wazuh agent name | `"wazuh.manager"` |

### `manager` Object

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `name` | string | ✅ Yes | Wazuh manager name | `"wazuh.manager"` |

### `decoder` Object

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `name` | string | ✅ Yes | Decoder name | `"android_decoder_03"` |

### `data` Object (Rule 100006 Specific)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `package_name` | string | ✅ Yes | Android package name | `"sk.madzik.android.logcatudp"` |

## Complete Example Payload

### Minimal Valid Payload (Wave 1)

```json
{
  "id": "1774133781.1718",
  "timestamp": "Mar 21, 2026 @ 15:56:21.984",
  "location": "192.168.65.1",
  "full_log": "emulator-5554: D/BackupManagerService( 1198): Received broadcast Intent { act=android.intent.action.PACKAGE_ADDED dat=package:sk.madzik.android.logcatudp flg=0x4000010 (has extras) }",
  "rule": {
    "id": "100006",
    "level": 15,
    "description": "Malicious Android app installed: sk.madzik.android.logcatudp",
    "groups": ["android", "package", "installandroid_install"],
    "firedtimes": 3
  },
  "agent": {
    "id": "000",
    "name": "wazuh.manager"
  },
  "manager": {
    "name": "wazuh.manager"
  },
  "decoder": {
    "name": "android_decoder_03"
  },
  "data": {
    "package_name": "sk.madzik.android.logcatudp"
  }
}
```

### Extended Payload (with optional fields)

```json
{
  "input": {"type": "log"},
  "id": "1774133781.1718",
  "timestamp": "Mar 21, 2026 @ 15:56:21.984",
  "location": "192.168.65.1",
  "full_log": "emulator-5554: D/BackupManagerService( 1198): Received broadcast Intent { act=android.intent.action.PACKAGE_ADDED dat=package:sk.madzik.android.logcatudp flg=0x4000010 (has extras) }",
  "rule": {
    "id": "100006",
    "level": 15,
    "description": "Malicious Android app installed: sk.madzik.android.logcatudp",
    "groups": "android, package, installandroid_install",
    "firedtimes": 3,
    "mail": true
  },
  "agent": {
    "id": "000",
    "name": "wazuh.manager"
  },
  "manager": {
    "name": "wazuh.manager"
  },
  "decoder": {
    "name": "android_decoder_03"
  },
  "data": {
    "package_name": "sk.madzik.android.logcatudp"
  },
  "_index": "wazuh-alerts-4.x-2026.03.21"
}
```

**Note:** Optional fields like `input`, `rule.mail`, and `_index` are ignored by AI-SOC but won't cause errors.

## Timestamp Format Support

AI-SOC accepts two timestamp formats:

### Format 1: Custom Wazuh Format (Preferred)
```
"Mar 21, 2026 @ 15:56:21.984"
```
**Pattern:** `%b %d, %Y @ %H:%M:%S.%f`

### Format 2: ISO-8601
```
"2026-03-21T15:56:21.984Z"
"2026-03-21T15:56:21.984+00:00"
```

**Note:** The `Z` suffix is automatically converted to `+00:00` for parsing.

## Severity Level Mapping

AI-SOC maps Wazuh `rule.level` to internal severity:

| Wazuh Level | AI-SOC Severity | Description |
|-------------|-----------------|-------------|
| 15+ | `CRITICAL` | Immediate action required |
| 12-14 | `HIGH` | High priority investigation |
| 8-11 | `MEDIUM` | Medium priority review |
| < 8 | `LOW` | Low priority (not forwarded in Wave 1) |

**Wave 1 Filter:** Only alerts with `rule.level >= 8` should be forwarded.

## Field Extraction and Mapping

### Endpoint Name Extraction

AI-SOC extracts the endpoint/device name from `full_log` by parsing the prefix before the first colon:

**Example:**
```
Input:  "emulator-5554: D/BackupManagerService( 1198): ..."
Output: "emulator-5554"
```

**Extraction Logic:**
- Split on first `:`
- Trim whitespace
- Reject if contains spaces or no colon found
- Store in `metadata.endpoint_name`

### Source IP Mapping

The `location` field is mapped to **both**:
- `metadata.source_ip` (primary field for analysis)
- `metadata.wazuh_location` (preserved for traceability)

## Expected AI-SOC Response

### Success Response (202 Accepted)

```json
{
  "id": "threat_abc123...",
  "threat_type": "device_compromise",
  "customer_name": "SeniorFraudShield",
  "timestamp": "2026-03-21T15:56:21.984000",
  "metadata": {
    "external_alert_id": "1774133781.1718",
    "rule_id": "100006",
    "wazuh_rule_level": 15,
    "initial_severity_hint": "CRITICAL",
    "alert_summary": "Malicious Android app installed: sk.madzik.android.logcatudp",
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
    "log_message": "emulator-5554: D/BackupManagerService( 1198): ..."
  }
}
```

**Note:** The response is the **normalized ThreatSignal**, not the full analysis. The full analysis happens asynchronously.

### Error Responses

#### 422 Unprocessable Entity - Unsupported Rule

```json
{
  "detail": {
    "message": "Wave 1 Wazuh ingestion only supports rule.id=100006",
    "field": "rule.id"
  }
}
```

**Cause:** `rule.id` is not `"100006"`

#### 422 Unprocessable Entity - Invalid Payload

```json
{
  "detail": {
    "message": "Invalid Wazuh alert payload"
  }
}
```

**Causes:**
- Missing required fields
- Invalid field types (e.g., `rule.level` is string instead of int)
- Malformed JSON structure

#### 422 Unprocessable Entity - Unsupported Timestamp

```json
{
  "detail": {
    "message": "Unsupported Wazuh timestamp format",
    "field": "timestamp"
  }
}
```

**Cause:** Timestamp doesn't match supported formats

## Validation Rules

### Required Field Validation

All fields marked as **Required** in the schema must be present. Missing fields will result in `422 Invalid Wazuh alert payload`.

### Type Validation

| Field | Expected Type | Invalid Examples |
|-------|---------------|------------------|
| `rule.id` | string | `100006` (number) ❌ |
| `rule.level` | integer | `"15"` (string) ❌ |
| `rule.groups` | array or string | `null` ❌ |
| `rule.firedtimes` | integer | `"3"` (string) ❌ |

### Rule ID Validation (Wave 1)

**Valid:** `rule.id = "100006"` (string)
**Invalid:** Any other value

**Note:** Future waves will support additional rule IDs.

## Integration Test Contract

The following tests verify the Wazuh → AI-SOC contract:

### Test 1: Valid Alert Acceptance
```python
# Send valid rule 100006 alert
response = POST /api/threats/ingest/wazuh
assert response.status_code == 202
assert response.json()["threat_type"] == "device_compromise"
assert response.json()["customer_name"] == "SeniorFraudShield"
```

### Test 2: Unsupported Rule Rejection
```python
# Send alert with rule.id = "999999"
response = POST /api/threats/ingest/wazuh
assert response.status_code == 422
assert "rule.id=100006" in response.json()["detail"]["message"]
```

### Test 3: Invalid Payload Rejection
```python
# Send malformed payload
response = POST /api/threats/ingest/wazuh with {"rule": "invalid"}
assert response.status_code == 422
assert "Invalid Wazuh alert payload" in response.json()["detail"]["message"]
```

### Test 4: Field Mapping Verification
```python
# Verify all fields are correctly mapped
signal = translate_wazuh_alert(sample_alert)
assert signal.metadata["source_ip"] == "192.168.65.1"
assert signal.metadata["wazuh_location"] == "192.168.65.1"
assert signal.metadata["package_name"] == "sk.madzik.android.logcatudp"
assert signal.metadata["endpoint_name"] == "emulator-5554"
assert signal.metadata["initial_severity_hint"] == "CRITICAL"
```

## Wazuh Integration Configuration

### Recommended Wazuh Integration Block

```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>http://localhost:8000/api/threats/ingest/wazuh</hook_url>
  <level>8</level>
  <rule_id>100006</rule_id>
  <alert_format>json</alert_format>
</integration>
```

### Verification: Check Wazuh Sends Correct Format

After configuring Wazuh integration, verify the webhook payload matches this spec:

1. **Trigger a test alert** (install malicious app on emulator)
2. **Capture the webhook payload** (check Wazuh integration logs or use a request inspector)
3. **Compare against the "Complete Example Payload" above**
4. **Verify all required fields are present**
5. **Verify field types match the schema**

### Common Wazuh Integration Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Missing `data.package_name` | 422 error | Verify decoder extracts package name |
| `rule.id` is integer | 422 error | Wazuh should send as string `"100006"` |
| `rule.groups` is null | 422 error | Ensure rule has groups defined |
| Timestamp format mismatch | 422 error | Use supported formats (see above) |

## Testing the Integration

### Manual Test with curl

```bash
curl -X POST http://localhost:8000/api/threats/ingest/wazuh \
  -H "Content-Type: application/json" \
  -d '{
    "id": "1774133781.1718",
    "timestamp": "Mar 21, 2026 @ 15:56:21.984",
    "location": "192.168.65.1",
    "full_log": "emulator-5554: D/BackupManagerService( 1198): Received broadcast Intent { act=android.intent.action.PACKAGE_ADDED dat=package:sk.madzik.android.logcatudp flg=0x4000010 (has extras) }",
    "rule": {
      "id": "100006",
      "level": 15,
      "description": "Malicious Android app installed: sk.madzik.android.logcatudp",
      "groups": ["android", "package", "installandroid_install"],
      "firedtimes": 3
    },
    "agent": {"id": "000", "name": "wazuh.manager"},
    "manager": {"name": "wazuh.manager"},
    "decoder": {"name": "android_decoder_03"},
    "data": {"package_name": "sk.madzik.android.logcatudp"}
  }'
```

**Expected Output:**
```json
{
  "id": "threat_...",
  "threat_type": "device_compromise",
  "customer_name": "SeniorFraudShield",
  ...
}
```

### Automated Test Suite

Run the AI-SOC integration tests to verify the contract:

```bash
cd soc-agent-system/backend
source venv/bin/activate
pytest tests/test_wazuh_ingestion.py -v
pytest tests/test_wazuh_translator.py -v
```

**Expected:** All 16 tests pass (9 translator + 7 ingestion)

## Summary Checklist for Wazuh Agent

✅ **Payload Format:**
- [ ] All required fields present (id, timestamp, location, full_log, rule, agent, manager, decoder, data)
- [ ] `rule.id` is string `"100006"`
- [ ] `rule.level` is integer (15 for malicious app)
- [ ] `rule.groups` is array of strings
- [ ] `data.package_name` is present
- [ ] Timestamp matches supported format

✅ **Webhook Configuration:**
- [ ] URL: `http://localhost:8000/api/threats/ingest/wazuh`
- [ ] Method: POST
- [ ] Content-Type: application/json
- [ ] Filter: `level >= 8` and `rule_id = 100006`

✅ **Verification:**
- [ ] Test alert triggers webhook
- [ ] AI-SOC returns 202 Accepted
- [ ] Alert appears in AI-SOC dashboard
- [ ] No 422 validation errors

## Reference Files

- **Integration Tests:** `soc-agent-system/backend/tests/test_wazuh_ingestion.py`
- **Translator Tests:** `soc-agent-system/backend/tests/test_wazuh_translator.py`
- **Translator Implementation:** `soc-agent-system/backend/src/wazuh_translator.py`
- **API Endpoint:** `soc-agent-system/backend/src/main.py` (line 289-320)
- **Wave 3 Configuration Spec:** `wazuh-integration/Wave-3-Spec.md`

