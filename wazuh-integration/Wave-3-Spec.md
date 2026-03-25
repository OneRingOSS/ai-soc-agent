# Wave 3: Wazuh Outbound Alert Forwarding

## Goal

Configure the Wazuh Manager to automatically forward medium-and-higher severity alerts (starting with rule 100006) to the AI-SOC ingestion endpoint in real-time.

## Context

**Completed:**
- ✅ Wave 1: AI-SOC ingestion endpoint (`POST /api/threats/ingest/wazuh`) and Wazuh-to-ThreatSignal translator
- ✅ Wave 2: Analysis/storage/streaming pipeline integration (already wired in Wave 1)

**This Wave:**
- Configure Wazuh Manager to forward alerts to AI-SOC
- Filter alerts by rule ID and severity level
- Ensure reliable delivery without breaking existing Wazuh workflows

## Technical Approach

### Option 1: Wazuh Integration Module (Recommended)

Use Wazuh's built-in integration framework to forward alerts to external webhooks.

**Advantages:**
- Native Wazuh feature (no custom code)
- Automatic retry logic
- Filtering by rule ID and level
- Easy to enable/disable

**Configuration Location:** `/var/ossec/etc/ossec.conf`

### Option 2: Custom Script Integration

Use Wazuh's active response mechanism to trigger a custom script on alert.

**Advantages:**
- More control over payload transformation
- Can add custom logic (batching, rate limiting)

**Disadvantages:**
- Requires custom script maintenance
- More complex debugging

## Implementation Plan

### Step 1: Configure Wazuh Integration Module

Add the following to `/var/ossec/etc/ossec.conf` in the `<ossec_config>` section:

```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>http://localhost:8000/api/threats/ingest/wazuh</hook_url>
  <level>8</level>
  <rule_id>100006</rule_id>
  <alert_format>json</alert_format>
</integration>
```

**Configuration Parameters:**
- `hook_url`: AI-SOC ingestion endpoint (adjust host/port as needed)
- `level`: Minimum severity level (8 = MEDIUM, matches Wave 1 spec)
- `rule_id`: Specific rule to forward (100006 for Android malicious app install)
- `alert_format`: JSON format (required for AI-SOC ingestion)

### Step 2: Restart Wazuh Manager

```bash
systemctl restart wazuh-manager
```

### Step 3: Verify Configuration

Check Wazuh Manager logs for integration initialization:

```bash
tail -f /var/ossec/logs/ossec.log | grep -i integration
```

Expected output:
```
INFO: Integration 'custom-webhook' enabled for rule '100006' with minimum level '8'
```

## Acceptance Criteria

### Functional Requirements

1. **Alert Forwarding:**
   - Wazuh Manager forwards rule 100006 alerts to `POST /api/threats/ingest/wazuh`
   - Only alerts with `rule.level >= 8` are forwarded
   - Alerts are sent in real-time (within 1 second of detection)

2. **Payload Format:**
   - Forwarded alerts match the `WazuhAlertPayload` schema from Wave 1
   - All required fields are present: `id`, `timestamp`, `location`, `full_log`, `rule`, `agent`, `manager`, `decoder`, `data`

3. **Error Handling:**
   - If AI-SOC endpoint is unavailable, Wazuh logs the error but continues normal operation
   - Failed deliveries are logged in `/var/ossec/logs/integrations.log`

4. **Non-Regression:**
   - Existing Wazuh alerting (email, Slack, etc.) continues to work
   - Wazuh dashboard/indexer still receives all alerts
   - No performance degradation in Wazuh Manager

### Test Deliverables

1. **Integration Test: Alert Delivery**
   - Trigger a rule 100006 alert from Android emulator
   - Verify alert appears in AI-SOC within 2 seconds
   - Verify alert is visible in AI-SOC dashboard/WebSocket stream

2. **Integration Test: Filtering**
   - Trigger a low-severity alert (level < 8)
   - Verify it is NOT forwarded to AI-SOC
   - Trigger a rule 100006 alert (level 15)
   - Verify it IS forwarded to AI-SOC

3. **Integration Test: Error Handling**
   - Stop AI-SOC backend
   - Trigger a rule 100006 alert
   - Verify error is logged in `/var/ossec/logs/integrations.log`
   - Verify Wazuh Manager continues normal operation
   - Restart AI-SOC backend
   - Verify next alert is delivered successfully

4. **Smoke Test: End-to-End**
   - Install malicious app on Android emulator
   - Verify alert flows: Emulator → Wazuh Manager → AI-SOC → Analysis → Storage → WebSocket
   - Verify alert appears in AI-SOC dashboard with correct metadata

## Configuration Reference

### AI-SOC Endpoint Details

**URL:** `http://localhost:8000/api/threats/ingest/wazuh`  
**Method:** `POST`  
**Content-Type:** `application/json`  
**Expected Response:** `202 Accepted`

**Sample Request Body:**
```json
{
  "id": "1774133781.1718",
  "timestamp": "Mar 21, 2026 @ 15:56:21.984",
  "location": "192.168.65.1",
  "full_log": "emulator-5554: D/BackupManagerService( 1198): Received broadcast Intent { act=android.intent.action.PACKAGE_ADDED dat=package:sk.madzik.android.logcatudp flg=0x4000010 (has extras) }",
  "rule": {
    "id": "100006",
    "level": 15,
    "description": "Malicions Android app installed: sk.madzik.android.logcatudp",
    "groups": "android, package, installandroid_install",
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

### Wazuh Integration Configuration Options

**Basic Configuration (Wave 3 Minimum):**
```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>http://localhost:8000/api/threats/ingest/wazuh</hook_url>
  <level>8</level>
  <rule_id>100006</rule_id>
  <alert_format>json</alert_format>
</integration>
```

**Extended Configuration (Future Waves):**
```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>http://localhost:8000/api/threats/ingest/wazuh</hook_url>
  <level>8</level>
  <rule_id>100006,100007,100008</rule_id>  <!-- Multiple rules -->
  <alert_format>json</alert_format>
  <max_log>165</max_log>  <!-- Max log size in KB -->
  <options>{"retry_attempts": 3, "timeout": 5}</options>  <!-- Optional -->
</integration>
```

**Production Configuration (with Authentication - Future):**
```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>https://ai-soc.example.com/api/threats/ingest/wazuh</hook_url>
  <api_key>your-api-key-here</api_key>  <!-- Future enhancement -->
  <level>8</level>
  <rule_id>100006</rule_id>
  <alert_format>json</alert_format>
</integration>
```

## Verification Plan

### Pre-Flight Checks

1. **AI-SOC Backend Running:**
   ```bash
   curl -X GET http://localhost:8000/health
   # Expected: {"status": "healthy"}
   ```

2. **Wazuh Manager Running:**
   ```bash
   systemctl status wazuh-manager
   # Expected: active (running)
   ```

3. **Network Connectivity:**
   ```bash
   curl -X POST http://localhost:8000/api/threats/ingest/wazuh \
     -H "Content-Type: application/json" \
     -d '{"test": "connectivity"}'
   # Expected: 422 (validation error, but proves connectivity)
   ```

### Test Execution Steps

#### Test 1: Manual Alert Injection

**Purpose:** Verify Wazuh can reach AI-SOC endpoint

**Steps:**
1. Create test alert JSON file: `/tmp/test_alert.json`
2. Send via curl:
   ```bash
   curl -X POST http://localhost:8000/api/threats/ingest/wazuh \
     -H "Content-Type: application/json" \
     -d @/tmp/test_alert.json
   ```
3. Verify response: `202 Accepted`
4. Check AI-SOC logs for successful ingestion

**Expected Result:** Alert appears in AI-SOC threat store

#### Test 2: Live Alert Forwarding

**Purpose:** Verify end-to-end Wazuh → AI-SOC flow

**Steps:**
1. Monitor AI-SOC logs:
   ```bash
   tail -f soc-agent-system/backend/logs/app.log
   ```
2. Monitor Wazuh integration logs:
   ```bash
   tail -f /var/ossec/logs/integrations.log
   ```
3. Trigger rule 100006 from Android emulator:
   ```bash
   adb shell pm install /path/to/malicious.apk
   ```
4. Verify alert appears in both logs within 2 seconds

**Expected Result:**
- Wazuh logs: `INFO: Alert sent to custom-webhook`
- AI-SOC logs: `INFO: Received Wazuh alert for rule 100006`

#### Test 3: Filtering Verification

**Purpose:** Verify only configured rules/levels are forwarded

**Steps:**
1. Trigger a low-severity alert (level < 8)
2. Verify it does NOT appear in AI-SOC
3. Trigger rule 100006 (level 15)
4. Verify it DOES appear in AI-SOC

**Expected Result:** Only rule 100006 with level >= 8 is forwarded

#### Test 4: Resilience Testing

**Purpose:** Verify Wazuh continues operating if AI-SOC is down

**Steps:**
1. Stop AI-SOC backend:
   ```bash
   cd soc-agent-system/backend
   pkill -f "uvicorn main:app"
   ```
2. Trigger rule 100006 alert
3. Check Wazuh integration logs for error
4. Verify Wazuh Manager still running
5. Restart AI-SOC backend
6. Trigger another alert
7. Verify successful delivery

**Expected Result:**
- Error logged but Wazuh continues
- Next alert delivered successfully after AI-SOC restart

## Rollback Plan

### Disable Integration

**Option 1: Comment out configuration**
```xml
<!--
<integration>
  <name>custom-webhook</name>
  ...
</integration>
-->
```

**Option 2: Remove configuration entirely**

Then restart Wazuh Manager:
```bash
systemctl restart wazuh-manager
```

### Verify Rollback

```bash
tail -f /var/ossec/logs/ossec.log | grep -i integration
# Expected: No integration messages
```

## Troubleshooting Guide

### Issue: Alerts not forwarding

**Symptoms:** No alerts appearing in AI-SOC

**Diagnosis:**
1. Check Wazuh integration logs:
   ```bash
   tail -100 /var/ossec/logs/integrations.log
   ```
2. Check Wazuh Manager logs:
   ```bash
   tail -100 /var/ossec/logs/ossec.log | grep -i integration
   ```
3. Verify configuration syntax:
   ```bash
   /var/ossec/bin/wazuh-logtest
   ```

**Solutions:**
- Verify `hook_url` is correct
- Check AI-SOC backend is running
- Verify network connectivity
- Check firewall rules

### Issue: 422 Validation Errors

**Symptoms:** AI-SOC returns 422 Unprocessable Entity

**Diagnosis:**
1. Check AI-SOC logs for validation error details
2. Compare Wazuh payload to expected schema

**Solutions:**
- Verify Wazuh alert includes all required fields
- Check field types match schema (e.g., `rule.level` is int, not string)
- Verify `rule.id` is "100006" (string)

### Issue: Performance Degradation

**Symptoms:** Wazuh Manager slow or high CPU usage

**Diagnosis:**
1. Check integration frequency:
   ```bash
   grep "custom-webhook" /var/ossec/logs/integrations.log | wc -l
   ```
2. Monitor Wazuh Manager resources:
   ```bash
   top -p $(pgrep wazuh-manager)
   ```

**Solutions:**
- Add rate limiting to integration
- Increase `level` threshold to reduce volume
- Consider async/batched delivery (future enhancement)

## Future Enhancements

### Phase 1 (Post-Wave 3)
- Add API key authentication
- Support multiple rule IDs in single integration
- Add retry logic with exponential backoff

### Phase 2
- Batch multiple alerts into single request
- Add rate limiting/throttling
- Support HTTPS with TLS verification

### Phase 3
- Add alert enrichment before forwarding
- Support custom field mapping
- Add metrics/monitoring dashboard

## Commit Checkpoint

After all Wave 3 tests pass, create a commit in the **Wazuh project** (if configuration is version-controlled) or document the configuration change:

**Commit Message:**
```
feat(wazuh): Add AI-SOC integration for rule 100006 forwarding

- Configure Wazuh integration module to forward alerts
- Filter by rule_id=100006 and level>=8
- Target endpoint: POST /api/threats/ingest/wazuh
- Verified end-to-end delivery and error handling

Tests:
- ✅ Manual alert injection
- ✅ Live alert forwarding
- ✅ Filtering verification
- ✅ Resilience testing
```

## Success Criteria Summary

✅ **Configuration Complete:**
- Wazuh integration module configured in `ossec.conf`
- Wazuh Manager restarted successfully
- Integration logs show successful initialization

✅ **Functional Verification:**
- Rule 100006 alerts forwarded to AI-SOC in real-time
- Alerts appear in AI-SOC dashboard within 2 seconds
- Low-severity alerts correctly filtered out

✅ **Resilience Verification:**
- Wazuh continues operating if AI-SOC is down
- Errors logged appropriately
- Recovery after AI-SOC restart

✅ **Non-Regression:**
- Existing Wazuh workflows unaffected
- No performance degradation
- All existing alerts still processed

## Handoff Notes

**For the Wazuh Configuration Agent:**

1. **Primary Task:** Configure Wazuh Manager integration in `/var/ossec/etc/ossec.conf`
2. **Test Environment:** Wazuh and AI-SOC running on same host (localhost)
3. **Target Endpoint:** `http://localhost:8000/api/threats/ingest/wazuh`
4. **Verification:** Run all 4 integration tests and confirm success
5. **Documentation:** Update Wazuh deployment docs with integration configuration

**Key Files:**
- Configuration: `/var/ossec/etc/ossec.conf`
- Logs: `/var/ossec/logs/integrations.log`, `/var/ossec/logs/ossec.log`
- Test alerts: Use existing Android emulator setup

**Dependencies:**
- AI-SOC backend must be running (Wave 1 complete)
- Android emulator configured with Wazuh agent
- Rule 100006 decoder already configured

**Success Indicator:**
Run the Android malicious app install test and see the alert flow through the entire pipeline: Emulator → Wazuh → AI-SOC → Analysis → Dashboard.

