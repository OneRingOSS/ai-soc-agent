# Jaeger Search Guide

Quick reference for finding traces in Jaeger UI.

---

## 🔍 **Automatic Search (Demo Script)**

When you run the demo script with a real API test, it automatically:
1. Extracts the threat ID from the response
2. Opens Jaeger with a pre-filtered search
3. Shows only traces for that specific threat

**Example:**
```
✅ Real API test completed successfully!
   Threat ID: 22b63eed-2ab0-45e6-aefd-68004949912b
   Severity: MEDIUM

   🔍 Opening Jaeger trace for this threat...
   📎 Jaeger URL: http://localhost:16686/search?service=soc-agent-system&tags=%7B%22threat.id%22%3A%2222b63eed-2ab0-45e6-aefd-68004949912b%22%7D
```

---

## 🖱️ **Manual Search in Jaeger UI**

If the auto-open doesn't work or you want to search manually:

### **Step 1: Open Jaeger**
```
http://localhost:16686
```

### **Step 2: Select Service**
- In the "Service" dropdown, select: **`soc-agent-system`**

### **Step 3: Add Tag Filter**
1. Click the **"Tags"** field
2. Enter: `threat.id="YOUR_THREAT_ID"`
   - Example: `threat.id="22b63eed-2ab0-45e6-aefd-68004949912b"`
3. Press Enter

### **Step 4: Click "Find Traces"**
- You should see 1 trace with the operation name: **`analyze_threat`**

---

## 📊 **What You'll See in the Trace**

### **Parent Span: `analyze_threat`**
- **Duration**: 8-15 seconds (with real API)
- **Tags**:
  - `threat.id`: The threat UUID
  - `threat.type`: e.g., "bot_traffic"
  - `threat.severity`: e.g., "MEDIUM"
  - `customer.name`: e.g., "Acme Corp"
  - `source.ip`: e.g., "192.168.1.100"
  - `fp.score`: e.g., 0.15
  - `requires_review`: true/false

### **Child Spans (Parallel Agents)**
These run in parallel (you'll see them overlapping in the timeline):
- `historical_agent.analyze` (~2-3s)
- `config_agent.analyze` (~2-3s)
- `priority_agent.analyze` (~2-3s)
- `network_agent.analyze` (~2-3s)
- `behavior_agent.analyze` (~2-3s)

### **Child Spans (Sequential Analyzers)**
These run after the agents complete:
- `fp_analyzer.analyze` (~1-2s)
- `response_engine.generate_plan` (~1-2s)
- `timeline_builder.build` (~1-2s)

---

## 🎯 **Other Useful Searches**

### **Find All Traces for a Customer**
```
Tags: customer.name="Acme Corp"
```

### **Find All High Severity Threats**
```
Tags: threat.severity="HIGH"
```

### **Find All Bot Traffic Threats**
```
Tags: threat.type="bot_traffic"
```

### **Find Threats Requiring Review**
```
Tags: requires_review=true
```

### **Find Traces with High False Positive Score**
```
Min Duration: 0s
Max Duration: 30s
Lookback: 1h
Tags: fp.score>0.5
```

---

## 🔗 **Trace-to-Logs Correlation**

Each trace has a **trace_id** that's also in the logs!

### **Step 1: Get Trace ID from Jaeger**
- Click on a trace
- Copy the **Trace ID** (32-character hex string)
- Example: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

### **Step 2: Search Logs in Loki/Grafana**
```
http://localhost:3000/explore
```

**LogQL Query:**
```
{job="soc-agent"} |= "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

This shows all log lines for that specific trace!

---

## 💡 **Pro Tips**

1. **Use Lookback Time**: Default is "Last Hour" - adjust if your test was earlier
2. **Sort by Duration**: Find slow traces by sorting by duration (descending)
3. **Compare Traces**: Select multiple traces to compare performance
4. **Deep Linking**: Copy the Jaeger URL to share specific traces with your team
5. **Trace Timeline**: Zoom in/out on the timeline to see parallel vs sequential execution

---

## 🐛 **Troubleshooting**

### **No Traces Found**
- ✅ Check that the backend is running
- ✅ Verify Jaeger is running: `docker ps | grep jaeger`
- ✅ Check the lookback time (try "Last 15 minutes")
- ✅ Verify the service name is exactly: `soc-agent-system`

### **Trace ID Doesn't Match**
- ✅ Make sure you're using the threat ID from the response
- ✅ Check that the backend has the updated code (with `threat.id` attribute)
- ✅ Restart the backend if you just updated the code

### **Auto-Open Doesn't Work**
- ✅ Copy the URL from the terminal output
- ✅ Paste it into your browser manually
- ✅ Check that Jaeger is accessible at http://localhost:16686

---

## 📖 **Example Demo Flow**

1. **Run real API test**: `./run_demo.sh` → Press 'y'
2. **Note the Threat ID**: e.g., `22b63eed-2ab0-45e6-aefd-68004949912b`
3. **Jaeger opens automatically** with the trace
4. **Click on the trace** to see the full timeline
5. **Point out**:
   - "Here's the parent span covering the entire analysis"
   - "These 5 spans are the parallel agents - see how they overlap?"
   - "These 3 spans are sequential - FP analysis, response planning, timeline"
   - "Total time: 12 seconds - most of it is waiting for OpenAI API"
6. **Show tags**: Click "Tags" to show all the metadata
7. **Show logs**: Click "Logs" to see correlated log entries

---

**This makes your observability demo much more impressive!** 🎯

