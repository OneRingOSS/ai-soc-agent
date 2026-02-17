# Jaeger Search Guide

Quick reference for finding traces in Jaeger UI.

---

## 🔍 **Automatic Search (Demo Script)**

When you run the demo script with a real API test, it automatically:
1. Extracts the threat ID from the response
2. Opens Jaeger UI with the service pre-selected
3. Provides instructions for finding the specific trace

**Example:**
```
✅ Real API test completed successfully!
   Threat ID: 22b63eed-2ab0-45e6-aefd-68004949912b
   Severity: high

   🔍 Opening Jaeger to view the trace...

   📎 To find this specific trace in Jaeger:
      1. Click on 'Tags' in the left sidebar
      2. Add tag: threat.id = 22b63eed-2ab0-45e6-aefd-68004949912b
      3. Click 'Find Traces'

   Or search by operation: 'analyze_threat'
```

---

## 🖱️ **Manual Search in Jaeger UI**

### **Method 1: Search by Operation (RECOMMENDED)**

This is the easiest and most reliable method:

1. **Open Jaeger**: http://localhost:16686
2. **Select Service**: `soc-agent-system`
3. **Select Operation**: `analyze_threat` (from dropdown)
4. **Click "Find Traces"**
5. **Look for the most recent trace** with 8-15 second duration (real API) or <200ms (mock)

### **Method 2: Search by Tag (Advanced)**

⚠️ **Note**: Tag-based search in Jaeger UI can be unreliable. Use Method 1 if possible.

1. **Open Jaeger**: http://localhost:16686
2. **Select Service**: `soc-agent-system`
3. **Click "Tags"** field in the left sidebar
4. **Enter**: `threat.id` (key) and paste your threat ID (value)
5. **Click "Find Traces"**

If no results appear, use Method 1 instead.

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

