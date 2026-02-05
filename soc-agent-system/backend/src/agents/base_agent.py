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

        logger.debug(f"[{self.name}] Building prompts for {signal.threat_type.value}")
        system_prompt = self.get_system_prompt()
        user_prompt = self.build_user_prompt(signal, context)

        logger.debug(f"[{self.name}] Calling OpenAI API (model: {settings.llm_model})")
        logger.debug(f"[{self.name}] System prompt length: {len(system_prompt)} chars")
        logger.debug(f"[{self.name}] User prompt length: {len(user_prompt)} chars")

        try:
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

            logger.debug(f"[{self.name}] Received response from OpenAI")
            result = json.loads(response.choices[0].message.content)
            processing_time = int((time.time() - start_time) * 1000)

            logger.debug(f"[{self.name}] Parsed response - Confidence: {result.get('confidence', 0.5):.2f}")

            return AgentAnalysis(
                agent_name=self.name,
                analysis=result.get("analysis", ""),
                confidence=result.get("confidence", 0.5),
                key_findings=result.get("key_findings", []),
                recommendations=result.get("recommendations", []),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
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

        logger.debug(f"[{self.name}] Running in MOCK mode (no API calls)")
        logger.debug(f"[{self.name}] Analyzing {signal.threat_type.value} for {signal.customer_name}")

        # Simulate processing time
        import asyncio
        await asyncio.sleep(0.1)

        processing_time = int((time.time() - start_time) * 1000)

        logger.debug(f"[{self.name}] Mock analysis complete - simulated {processing_time}ms processing")

        return AgentAnalysis(
            agent_name=self.name,
            analysis=f"Mock analysis for {signal.threat_type.value}",
            confidence=0.85,
            key_findings=[f"Mock finding for {self.name}"],
            recommendations=[f"Mock recommendation from {self.name}"],
            processing_time_ms=processing_time
        )

