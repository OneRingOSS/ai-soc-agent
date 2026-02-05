# SOC Agent System - Enhanced Logging for Demo

This guide shows you how to add comprehensive logging to visualize the multi-agent system in action during your demo.

---

## Table of Contents

1. [Overview](#overview)
2. [What You'll See](#what-youll-see)
3. [Implementation Steps](#implementation-steps)
4. [Configuration Options](#configuration-options)
5. [Demo Scenarios](#demo-scenarios)
6. [Demo Tips](#demo-tips)
7. [Quick Start](#quick-start)

---

## Overview

The logging enhancements will make your multi-agent SOC system visible and impressive during demos. This is crucial for demonstrating your skills in building sophisticated AI agent systems for security operations.

### What You'll See

- **🎯 Agent dispatch and coordination** - See the coordinator delegating work to specialized agents
- **⚡ Parallel execution** - Watch 5 agents analyze simultaneously
- **📊 Data source queries** - View agents querying historical incidents, configs, infra events, news
- **🌐 LLM interactions** - See prompts being sent and responses received
- **🔬 Synthesis process** - Watch the coordinator combine agent insights
- **⏱️ Performance metrics** - Track timing for each agent and overall analysis

---

## Implementation Steps

### Step 1: Enhanced Coordinator Logging

**File:** `backend/src/agents/coordinator.py`

Add comprehensive logging to show the orchestration flow:

```python
"""Coordinator Agent - Main orchestrator for multi-agent analysis."""
import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

from models import (
    ThreatSignal, ThreatAnalysis, ThreatSeverity,
    AgentAnalysis, MITRETactic, MITRETechnique
)
from config import settings
from mock_data import MockDataStore
from agents.historical_agent import HistoricalAgent
from agents.config_agent import ConfigAgent
from agents.devops_agent import DevOpsAgent
from agents.context_agent import ContextAgent
from agents.priority_agent import PriorityAgent

# Configure logger
logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """Orchestrates parallel analysis across all specialized agents."""
    
    def __init__(
        self, 
        mock_data: Optional[MockDataStore] = None,
        client: Optional[AsyncOpenAI] = None,
        use_mock: bool = False
    ):
        """Initialize coordinator with all specialized agents."""
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.mock_data = mock_data or MockDataStore()
        self.use_mock = use_mock
        
        # Initialize specialized agents
        self.historical_agent = HistoricalAgent(client=self.client)
        self.config_agent = ConfigAgent(client=self.client)
        self.devops_agent = DevOpsAgent(client=self.client)
        self.context_agent = ContextAgent(client=self.client)
        self.priority_agent = PriorityAgent(client=self.client)
        
        logger.info("🎯 Coordinator initialized with 5 specialized agents")
    
    async def analyze_threat(self, signal: ThreatSignal) -> ThreatAnalysis:
        """Perform comprehensive threat analysis using all agents in parallel."""
        logger.info("=" * 80)
        logger.info(f"🚨 NEW THREAT DETECTED: {signal.threat_type.value}")
        logger.info(f"   Customer: {signal.customer_name}")
        logger.info(f"   Signal ID: {signal.id}")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Gather context for each agent
        logger.info("\n📊 GATHERING CONTEXT FOR AGENTS...")
        contexts = self._build_agent_contexts(signal)
        logger.info(f"   ✓ Historical: {len(contexts['historical'].get('similar_incidents', []))} similar incidents found")
        logger.info(f"   ✓ Config: Retrieved settings for {signal.customer_name}")
        logger.info(f"   ✓ DevOps: {len(contexts['devops'].get('infra_events', []))} recent infrastructure events")
        logger.info(f"   ✓ Context: {len(contexts['context'].get('news_items', []))} relevant news items")
        logger.info(f"   ✓ Priority: Context prepared for classification")
        
        # Determine analysis method
        analyze_method = "analyze_mock" if self.use_mock else "analyze"
        mode = "MOCK MODE" if self.use_mock else "LIVE MODE (OpenAI API)"
        
        logger.info(f"\n🤖 DISPATCHING 5 AGENTS IN PARALLEL ({mode})...")
        dispatch_start = time.time()
        
        # Dispatch all agents in parallel
        results = await asyncio.gather(
            self._log_agent_execution(
                "Historical Agent", 
                getattr(self.historical_agent, analyze_method),
                signal, 
                contexts["historical"]
            ),
            self._log_agent_execution(
                "Config Agent",
                getattr(self.config_agent, analyze_method),
                signal,
                contexts["config"]
            ),
            self._log_agent_execution(
                "DevOps Agent",
                getattr(self.devops_agent, analyze_method),
                signal,
                contexts["devops"]
            ),
            self._log_agent_execution(
                "Context Agent",
                getattr(self.context_agent, analyze_method),
                signal,
                contexts["context"]
            ),
            self._log_agent_execution(
                "Priority Agent",
                getattr(self.priority_agent, analyze_method),
                signal,
                contexts["priority"]
            ),
            return_exceptions=True
        )
        
        dispatch_time = (time.time() - dispatch_start) * 1000
        logger.info(f"\n⚡ ALL AGENTS COMPLETED IN {dispatch_time:.0f}ms (parallel execution)")
        
        # Process results
        agent_analyses = {}
        for i, (name, result) in enumerate(zip(
            ["historical", "config", "devops", "context", "priority"],
            results
        )):
            if isinstance(result, Exception):
                logger.error(f"   ❌ {name} agent failed: {str(result)}")
                agent_analyses[name] = AgentAnalysis(
                    agent_name=name,
                    analysis=f"Agent failed: {str(result)}",
                    confidence=0.0,
                    key_findings=["Error"],
                    recommendations=["Manual review required"],
                    processing_time_ms=0
                )
            else:
                agent_analyses[name] = result
        
        # Synthesize final analysis
        logger.info("\n🔬 SYNTHESIZING FINAL ANALYSIS...")
        total_time = int((time.time() - start_time) * 1000)
        
        final_analysis = self._synthesize_analysis(signal, agent_analyses, total_time)
        
        logger.info(f"\n✅ ANALYSIS COMPLETE")
        logger.info(f"   Severity: {final_analysis.severity.value}")
        logger.info(f"   Total Processing Time: {total_time}ms")
        logger.info(f"   Requires Human Review: {final_analysis.requires_human_review}")
        logger.info("=" * 80 + "\n")
        
        return final_analysis
    
    async def _log_agent_execution(
        self,
        agent_name: str,
        analyze_func,
        signal: ThreatSignal,
        context: Dict[str, Any]
    ) -> AgentAnalysis:
        """Wrapper to log individual agent execution."""
        logger.info(f"   🔄 {agent_name} starting...")
        start = time.time()
        
        try:
            result = await analyze_func(signal, context)
            elapsed = (time.time() - start) * 1000
            
            logger.info(f"   ✅ {agent_name} completed in {elapsed:.0f}ms")
            logger.info(f"      Confidence: {result.confidence:.2f}")
            logger.info(f"      Key Findings: {len(result.key_findings)}")
            
            return result
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"   ❌ {agent_name} failed after {elapsed:.0f}ms: {str(e)}")
            raise
    
    def _build_agent_contexts(self, signal: ThreatSignal) -> Dict[str, Dict[str, Any]]:
        """Build context data for each agent."""
        logger.debug(f"Building contexts for {signal.customer_name}...")
        
        # Extract keywords for news search
        keywords = [signal.customer_name, signal.threat_type.value]
        if "crypto" in signal.customer_name.lower():
            keywords.append("bitcoin")
        
        similar_incidents = self.mock_data.get_similar_incidents(
            signal.threat_type, signal.customer_name
        )
        logger.debug(f"   Found {len(similar_incidents)} similar historical incidents")
        
        infra_events = self.mock_data.get_recent_infra_events(60)
        logger.debug(f"   Found {len(infra_events)} recent infrastructure events")
        
        news_items = self.mock_data.get_relevant_news(keywords)
        logger.debug(f"   Found {len(news_items)} relevant news items")
        
        return {
            "historical": {
                "similar_incidents": similar_incidents
            },
            "config": {
                "customer_config": self.mock_data.get_customer_config(signal.customer_name)
            },
            "devops": {
                "infra_events": infra_events
            },
            "context": {
                "news_items": news_items
            },
            "priority": {}
        }
    
    def _synthesize_analysis(
        self,
        signal: ThreatSignal,
        agent_analyses: Dict[str, AgentAnalysis],
        total_time: int
    ) -> ThreatAnalysis:
        """Synthesize all agent analyses into final threat analysis."""
        
        logger.info("   Extracting insights from all agents...")
        
        # Extract priority agent results for severity and MITRE mapping
        priority_analysis = agent_analyses.get("priority")
        
        # Determine severity (default to MEDIUM if priority agent failed)
        severity = ThreatSeverity.MEDIUM
        mitre_tactics = []
        mitre_techniques = []
        customer_narrative = "Analysis completed. Please review agent findings."
        requires_review = False
        
        if priority_analysis and priority_analysis.confidence > 0:
            # Parse severity from analysis if available
            analysis_lower = priority_analysis.analysis.lower()
            if "critical" in analysis_lower:
                severity = ThreatSeverity.CRITICAL
            elif "high" in analysis_lower:
                severity = ThreatSeverity.HIGH
            elif "low" in analysis_lower:
                severity = ThreatSeverity.LOW
            
            logger.info(f"   Priority Agent assessed severity: {severity.value}")
            
            # Check for human review requirement
            requires_review = "review" in analysis_lower or severity == ThreatSeverity.CRITICAL
            if requires_review:
                logger.warning(f"   ⚠️  Human review required")
        
        # Generate executive summary
        all_findings = []
        for name, analysis in agent_analyses.items():
            all_findings.extend(analysis.key_findings)
            logger.debug(f"   {name}: {len(analysis.key_findings)} findings, confidence {analysis.confidence:.2f}")
        
        executive_summary = self._generate_executive_summary(
            signal, severity, all_findings[:5]
        )
        
        logger.info(f"   Generated executive summary: {executive_summary[:80]}...")
        
        return ThreatAnalysis(
            signal=signal,
            severity=severity,
            executive_summary=executive_summary,
            mitre_tactics=mitre_tactics,
            mitre_techniques=mitre_techniques,
            customer_narrative=customer_narrative,
            agent_analyses=agent_analyses,
            total_processing_time_ms=total_time,
            requires_human_review=requires_review
        )
    
    def _generate_executive_summary(
        self,
        signal: ThreatSignal,
        severity: ThreatSeverity,
        key_findings: List[str]
    ) -> str:
        """Generate executive summary from analysis results."""
        findings_text = "; ".join(key_findings) if key_findings else "Standard analysis completed"
        
        return (
            f"{severity.value} severity {signal.threat_type.value.replace('_', ' ')} "
            f"detected for {signal.customer_name}. "
            f"Key findings: {findings_text}."
        )


# Factory function for easy instantiation
def create_coordinator(use_mock: bool = False) -> CoordinatorAgent:
    """Create a coordinator agent instance."""
    return CoordinatorAgent(use_mock=use_mock)
```

---

### Step 2: Enhanced Base Agent Logging

**File:** `backend/src/agents/base_agent.py`

Add detailed logging for individual agent operations:

```python
"""Base agent class for all specialized agents."""
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from openai import AsyncOpenAI
from models import ThreatSignal, AgentAnalysis
from config import settings

# Configure logger
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all SOC agents."""
    
    def __init__(self, name: str, client: Optional[AsyncOpenAI] = None):
        """Initialize base agent."""
        self.name = name
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        logger.debug(f"Initialized {self.name}")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build the user prompt for analysis."""
        pass
    
    async def analyze(
        self, 
        signal: ThreatSignal, 
        context: Dict[str, Any]
    ) -> AgentAnalysis:
        """Perform analysis on the threat signal."""
        start_time = time.time()
        
        logger.debug(f"\n{'─' * 60}")
        logger.debug(f"🤖 {self.name.upper()} - ANALYSIS START")
        logger.debug(f"{'─' * 60}")
        
        try:
            # Build prompts
            system_prompt = self.get_system_prompt()
            user_prompt = self.build_user_prompt(signal, context)
            
            logger.debug(f"📝 System Prompt Length: {len(system_prompt)} chars")
            logger.debug(f"📝 User Prompt Length: {len(user_prompt)} chars")
            
            # Log context data
            if context:
                for key, value in context.items():
                    if isinstance(value, list):
                        logger.debug(f"   Context - {key}: {len(value)} items")
                    else:
                        logger.debug(f"   Context - {key}: {type(value).__name__}")
            
            logger.debug(f"🌐 Calling OpenAI API ({settings.llm_model})...")
            api_start = time.time()
            
            response = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                response_format={"type": "json_object"}
            )
            
            api_time = (time.time() - api_start) * 1000
            logger.debug(f"✅ OpenAI API responded in {api_time:.0f}ms")
            
            result = json.loads(response.choices[0].message.content)
            processing_time = int((time.time() - start_time) * 1000)
            
            analysis = AgentAnalysis(
                agent_name=self.name,
                analysis=result.get("analysis", ""),
                confidence=result.get("confidence", 0.5),
                key_findings=result.get("key_findings", []),
                recommendations=result.get("recommendations", []),
                processing_time_ms=processing_time
            )
            
            logger.debug(f"📊 Analysis Results:")
            logger.debug(f"   Confidence: {analysis.confidence:.2%}")
            logger.debug(f"   Key Findings: {len(analysis.key_findings)}")
            logger.debug(f"   Recommendations: {len(analysis.recommendations)}")
            logger.debug(f"   Processing Time: {processing_time}ms")
            logger.debug(f"{'─' * 60}\n")
            
            return analysis
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"❌ {self.name} analysis failed: {str(e)}")
            logger.debug(f"{'─' * 60}\n")
            
            return AgentAnalysis(
                agent_name=self.name,
                analysis=f"Analysis failed: {str(e)}",
                confidence=0.0,
                key_findings=["Error during analysis"],
                recommendations=["Manual review required"],
                processing_time_ms=processing_time
            )
    
    async def analyze_mock(
        self, 
        signal: ThreatSignal, 
        context: Dict[str, Any]
    ) -> AgentAnalysis:
        """Mock analysis for testing without LLM calls."""
        start_time = time.time()
        
        logger.debug(f"🔧 {self.name} - MOCK ANALYSIS")
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(0.1)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AgentAnalysis(
            agent_name=self.name,
            analysis=f"Mock analysis for {signal.threat_type.value}",
            confidence=0.85,
            key_findings=[f"Mock finding for {self.name}"],
            recommendations=[f"Mock recommendation from {self.name}"],
            processing_time_ms=processing_time
        )
```

---

### Step 3: Configure Logging in Main Application

**File:** `backend/src/main.py`

Add logging configuration at the top of the file:

```python
"""FastAPI application for SOC Agent System."""
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from models import ThreatAnalysis, ThreatSignal, DashboardMetrics, ThreatType
from threat_generator import threat_generator
from agents.coordinator import create_coordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more verbose output
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Reduce noise from other libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ... rest of your main.py code remains the same ...
```

---

### Step 4: Add Advanced Logging Configuration (Optional)

**File:** `backend/src/logging_config.py` (new file)

Create this file for advanced color-coded logging:

```python
"""Logging configuration for different verbosity levels."""
import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(level: str = "INFO", colored: bool = True):
    """
    Setup logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        colored: Whether to use colored output
    """
    log_format = '%(asctime)s | %(levelname)-8s | %(message)s'
    date_format = '%H:%M:%S'
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if colored and sys.stdout.isatty():
        formatter = ColoredFormatter(log_format, datefmt=date_format)
    else:
        formatter = logging.Formatter(log_format, datefmt=date_format)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


# Convenience functions for different demo modes
def demo_mode_minimal():
    """Minimal logging - only show key events."""
    setup_logging("INFO", colored=True)


def demo_mode_detailed():
    """Detailed logging - show all agent activity."""
    setup_logging("DEBUG", colored=True)
    
    # Enable agent-specific loggers
    logging.getLogger("agents.coordinator").setLevel(logging.DEBUG)
    logging.getLogger("agents.base_agent").setLevel(logging.DEBUG)


def demo_mode_production():
    """Production-like logging - structured without colors."""
    setup_logging("INFO", colored=False)
```

To use advanced logging, update `main.py`:

```python
# Replace the basic logging config with:
from logging_config import demo_mode_detailed  # or demo_mode_minimal

# Configure logging for demo
demo_mode_detailed()  # Shows all agent activity

logger = logging.getLogger(__name__)
```

---

## Configuration Options

### Environment Variables

Add these to your `.env` file:

```env
# Logging Configuration
LOG_LEVEL=INFO          # INFO, DEBUG, WARNING, ERROR
LOG_COLORED=true        # Enable colored output
LOG_AGENT_DETAILS=true  # Show detailed agent execution
```

Update `backend/src/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_colored: bool = Field(default=True, env="LOG_COLORED")
    log_agent_details: bool = Field(default=True, env="LOG_AGENT_DETAILS")
```

### Logging Levels

| Level | What You See | Best For |
|-------|-------------|----------|
| **INFO** | Key events, agent start/complete, final results | Standard demos |
| **DEBUG** | All of above + prompt details, API calls, data queries | Detailed technical demos |
| **WARNING** | Errors and warnings only | Production monitoring |

---

## Demo Scenarios

### Scenario 1: Parallel Agent Execution

**Command:**
```bash
export LOG_LEVEL=INFO
python main.py
```

**Output:**
```
09:15:23 | INFO     | ================================================================================
09:15:23 | INFO     | 🚨 NEW THREAT DETECTED: bot_traffic
09:15:23 | INFO     |    Customer: Acme Corp
09:15:23 | INFO     |    Signal ID: abc-123
09:15:23 | INFO     | ================================================================================
09:15:23 | INFO     | 
09:15:23 | INFO     | 📊 GATHERING CONTEXT FOR AGENTS...
09:15:23 | INFO     |    ✓ Historical: 5 similar incidents found
09:15:23 | INFO     |    ✓ Config: Retrieved settings for Acme Corp
09:15:23 | INFO     |    ✓ DevOps: 3 recent infrastructure events
09:15:23 | INFO     |    ✓ Context: 2 relevant news items
09:15:23 | INFO     |    ✓ Priority: Context prepared for classification
09:15:23 | INFO     | 
09:15:23 | INFO     | 🤖 DISPATCHING 5 AGENTS IN PARALLEL (LIVE MODE)...
09:15:23 | INFO     |    🔄 Historical Agent starting...
09:15:23 | INFO     |    🔄 Config Agent starting...
09:15:23 | INFO     |    🔄 DevOps Agent starting...
09:15:23 | INFO     |    🔄 Context Agent starting...
09:15:23 | INFO     |    🔄 Priority Agent starting...
09:15:24 | INFO     |    ✅ Historical Agent completed in 850ms
09:15:24 | INFO     |       Confidence: 0.87
09:15:24 | INFO     |       Key Findings: 3
09:15:24 | INFO     |    ✅ Config Agent completed in 920ms
09:15:24 | INFO     |       Confidence: 0.92
09:15:24 | INFO     |       Key Findings: 2
09:15:24 | INFO     |    ✅ DevOps Agent completed in 780ms
09:15:24 | INFO     |       Confidence: 0.75
09:15:24 | INFO     |       Key Findings: 1
09:15:24 | INFO     |    ✅ Context Agent completed in 890ms
09:15:24 | INFO     |       Confidence: 0.88
09:15:24 | INFO     |       Key Findings: 2
09:15:24 | INFO     |    ✅ Priority Agent completed in 950ms
09:15:24 | INFO     |       Confidence: 0.91
09:15:24 | INFO     |       Key Findings: 4
09:15:24 | INFO     | 
09:15:24 | INFO     | ⚡ ALL AGENTS COMPLETED IN 952ms (parallel execution)
09:15:24 | INFO     | 
09:15:24 | INFO     | 🔬 SYNTHESIZING FINAL ANALYSIS...
09:15:24 | INFO     |    Extracting insights from all agents...
09:15:24 | INFO     |    Priority Agent assessed severity: HIGH
09:15:24 | WARNING  |    ⚠️  Human review required
09:15:24 | INFO     |    Generated executive summary: HIGH severity bot traffic detected...
09:15:24 | INFO     | 
09:15:24 | INFO     | ✅ ANALYSIS COMPLETE
09:15:24 | INFO     |    Severity: HIGH
09:15:24 | INFO     |    Total Processing Time: 1124ms
09:15:24 | INFO     |    Requires Human Review: True
09:15:24 | INFO     | ================================================================================
```

---

### Scenario 2: Detailed Agent Activity

**Command:**
```bash
export LOG_LEVEL=DEBUG
python main.py
```

**Output (excerpt):**
```
09:20:15 | DEBUG    | ────────────────────────────────────────────────────────────────
09:20:15 | DEBUG    | 🤖 HISTORICAL AGENT - ANALYSIS START
09:20:15 | DEBUG    | ────────────────────────────────────────────────────────────────
09:20:15 | DEBUG    | 📝 System Prompt Length: 423 chars
09:20:15 | DEBUG    | 📝 User Prompt Length: 1024 chars
09:20:15 | DEBUG    |    Context - similar_incidents: 5 items
09:20:15 | DEBUG    | 🌐 Calling OpenAI API (gpt-4-turbo-preview)...
09:20:16 | DEBUG    | ✅ OpenAI API responded in 845ms
09:20:16 | DEBUG    | 📊 Analysis Results:
09:20:16 | DEBUG    |    Confidence: 87.00%
09:20:16 | DEBUG    |    Key Findings: 3
09:20:16 | DEBUG    |    Recommendations: 2
09:20:16 | DEBUG    |    Processing Time: 850ms
09:20:16 | DEBUG    | ────────────────────────────────────────────────────────────────
```

---

## Demo Tips

### 1. Terminal Setup

**Open two terminals side-by-side:**

```
┌─────────────────────────────────┬─────────────────────────────────┐
│                                 │                                 │
│  Terminal 1: Backend Logs       │  Terminal 2: Frontend           │
│  (Shows agent activity)         │  (Visual dashboard)             │
│                                 │                                 │
│  $ cd backend                   │  $ cd frontend                  │
│  $ source venv/bin/activate     │  $ npm run dev                  │
│  $ export LOG_LEVEL=INFO        │                                 │
│  $ cd src                       │  Browser opens automatically    │
│  $ python main.py               │                                 │
│                                 │                                 │
│  Watch agent logs flow here →  │  ← Trigger threats here         │
│                                 │                                 │
└─────────────────────────────────┴─────────────────────────────────┘
```

### 2. Key Points to Highlight During Demo

**Architecture:**
- ✅ "Notice the multi-agent architecture with 5 specialized agents"
- ✅ "Each agent has a specific responsibility: Historical, Config, DevOps, Context, Priority"

**Performance:**
- ✅ "All 5 agents start simultaneously - this is parallel execution"
- ✅ "Total analysis completes in under 1 second despite calling 5 LLMs"
- ✅ "Sequential execution would take 5x longer"

**Intelligence:**
- ✅ "Historical agent found 5 similar past incidents to learn from"
- ✅ "Config agent checks customer-specific policies"
- ✅ "DevOps agent correlates with infrastructure events"
- ✅ "Context agent provides business intelligence from news"
- ✅ "Priority agent synthesizes everything and assigns severity"

**Production-Ready:**
- ✅ "Mock mode allows testing without API costs"
- ✅ "Structured logging for monitoring and debugging"
- ✅ "Async/await for high-performance concurrent execution"

### 3. Trigger Specific Scenarios

Use the dashboard buttons to demonstrate different threat types:

| Button | Threat Type | Highlight This |
|--------|-------------|----------------|
| **Bot Attack** | bot_traffic | Historical agent finds patterns, Config checks rate limits |
| **Rate Limit** | rate_limit_breach | Config agent identifies policy violations |
| **Trigger Random** | Any type | Shows system handling diverse threats |

### 4. For Technical Interviews

**Emphasize these technical decisions:**

1. **Why multi-agent?** 
   - "Single-agent LLMs struggle with complex tasks. Multi-agent architecture allows specialization and parallel execution."

2. **Why parallel execution?**
   - "LLM calls are I/O bound. Running them in parallel with asyncio.gather() dramatically improves throughput."

3. **Why context gathering?**
   - "Context-aware agents make better decisions. We provide historical patterns, configs, infrastructure state, and business context."

4. **Why structured output?**
   - "JSON response format ensures reliable parsing for downstream systems. Critical for automation."

5. **Why logging at this level?**
   - "In production, these logs enable monitoring, debugging, and performance analysis. Essential for SOC operations."

---

## Quick Start

### Standard Demo Mode

```bash
# Terminal 1: Backend with enhanced logging
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
export LOG_LEVEL=INFO
cd src
python main.py

# Terminal 2: Frontend
cd frontend
npm run dev

# Open browser to http://localhost:3000
# Click "Trigger Random" or "Bot Attack" buttons
# Watch the agent logs in Terminal 1!
```

### Detailed Debug Mode

```bash
# For maximum visibility during technical demos
export LOG_LEVEL=DEBUG
export LOG_AGENT_DETAILS=true
cd src
python main.py
```

### Quick Test Without OpenAI

```bash
# Uses mock mode (no API key required)
export OPENAI_API_KEY=""
cd src
python main.py
# System will automatically use mock agents
```

---

## Troubleshooting

### Issue: No logs appearing

**Solution:**
```bash
# Ensure logging is configured before other imports
# Check that LOG_LEVEL is set
export LOG_LEVEL=INFO
```

### Issue: Too much noise from libraries

**Solution:** The logging config already suppresses httpx, httpcore, openai. To suppress more:
```python
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
```

### Issue: Colors not showing

**Solution:** Some terminals don't support ANSI colors. Set:
```bash
export LOG_COLORED=false
```

---

## What This Demonstrates

### For SOC Operations

- ✅ **Triage automation** - Agents automatically analyze and prioritize threats
- ✅ **Context enrichment** - Multiple data sources provide comprehensive view
- ✅ **Pattern recognition** - Historical analysis identifies recurring issues
- ✅ **False positive reduction** - Business context helps distinguish real threats
- ✅ **Severity assessment** - Automated classification with MITRE mapping

### For Your Skills

- ✅ **Multi-agent AI systems** - Designing and implementing agent orchestration
- ✅ **Async/concurrent programming** - Python asyncio for parallel execution
- ✅ **LLM integration** - OpenAI API with structured outputs
- ✅ **System architecture** - Scalable, production-ready design
- ✅ **Observability** - Comprehensive logging and monitoring

---

## Next Steps

1. **Run the basic setup** - Get INFO-level logging working
2. **Try DEBUG mode** - See the detailed agent activity
3. **Customize for your use case** - Add more agents or data sources
4. **Practice your demo** - Know which scenarios to show
5. **Prepare talking points** - Be ready to explain design decisions

---

**Ready to impress? Fire up those terminals and show off your multi-agent SOC system!** 🚀

*For questions or issues, refer to the main README.md or check the code comments.*
