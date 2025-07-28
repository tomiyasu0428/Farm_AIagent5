"""Base agent class for all AI agents."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from src.config import settings
from src.models.state import AgriAgentState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, name: str):
        """Initialize base agent."""
        self.name = name
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.google_api_key,
            temperature=0.1
        )
        
        # Add LangSmith metadata for tracing
        if settings.langchain_tracing_v2:
            self.llm = self.llm.with_config({
                "tags": [f"agent:{name}", "farm-ai-agent", "gemini-2.5-flash"],
                "metadata": {"agent_name": name, "model": "gemini-2.5-flash"}
            })
        
        logger.info(f"Initialized {self.name} agent with LangSmith tracing: {settings.langchain_tracing_v2}")
    
    @abstractmethod
    async def process(self, state: AgriAgentState) -> Dict[str, Any]:
        """Process the current state and return updates."""
        pass
    
    async def invoke_llm(self, prompt: str, context: str = "") -> str:
        """Invoke the LLM with given prompt and context."""
        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            messages = [HumanMessage(content=full_prompt)]
            
            response = await self.llm.ainvoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"LLM invocation error in {self.name}: {e}")
            raise
    
    def _extract_last_message(self, state: AgriAgentState) -> str:
        """Extract the last user message from state."""
        if state.get("messages"):
            return state["messages"][-1].content
        return ""
    
    def _format_response(self, content: str) -> Dict[str, Any]:
        """Format agent response."""
        return {
            "messages": [HumanMessage(content=content)],
            "agent_data": {
                "processed_by": self.name,
                "timestamp": self._get_timestamp()
            }
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()