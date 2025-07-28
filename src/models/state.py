"""State definitions for LangGraph agents."""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
import operator


class AgriAgentState(TypedDict):
    """State shared across all agents in the agricultural AI system."""
    
    # Message history for the conversation
    messages: Annotated[List[BaseMessage], operator.add]
    
    # User identification
    user_id: str
    thread_id: str
    
    # Agent routing
    next_agent: str
    
    # Human-in-the-loop confirmation
    pending_confirmation: Dict[str, Any]
    awaiting_confirmation: bool
    
    # Data extraction and processing
    extracted_data: Dict[str, Any]
    query_results: List[Dict[str, Any]]
    
    # Error handling
    error_message: Optional[str]
    retry_count: int
    
    # Agent-specific data
    agent_data: Dict[str, Any]
    
    # Metadata
    timestamp: str
    session_metadata: Dict[str, Any]