"""LangSmith configuration utilities for enhanced tracing."""

import os
import logging
from typing import Dict, Any, Optional
from functools import wraps
from src.config import settings

logger = logging.getLogger(__name__)


def get_langsmith_config(
    tags: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None,
    run_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get LangSmith configuration for tracing.
    
    Args:
        tags: List of tags for the run
        metadata: Metadata dictionary
        run_name: Custom run name
    
    Returns:
        Configuration dictionary for LangSmith tracing
    """
    if not settings.langchain_tracing_v2:
        return {}
    
    config = {}
    
    if tags:
        config["tags"] = tags
    
    if metadata:
        config["metadata"] = metadata
    
    if run_name:
        config["run_name"] = run_name
    
    return config


def trace_agent_call(agent_name: str):
    """
    Decorator to add LangSmith tracing to agent calls.
    
    Args:
        agent_name: Name of the agent for tracing
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if settings.langchain_tracing_v2:
                # Add tracing metadata to the function call
                config = get_langsmith_config(
                    tags=[f"agent:{agent_name}", "farm-ai-agent"],
                    metadata={
                        "agent_name": agent_name,
                        "function": func.__name__
                    },
                    run_name=f"{agent_name}_{func.__name__}"
                )
                
                # If the function has a state parameter, add user info
                if args and hasattr(args[0], 'get'):
                    state = args[0]
                    if isinstance(state, dict) and 'user_id' in state:
                        config.setdefault("metadata", {})["user_id"] = state['user_id']
                
                logger.debug(f"Tracing {agent_name}.{func.__name__} with config: {config}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def trace_tool_call(tool_name: str):
    """
    Decorator to add LangSmith tracing to tool calls.
    
    Args:
        tool_name: Name of the tool for tracing
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if settings.langchain_tracing_v2:
                config = get_langsmith_config(
                    tags=[f"tool:{tool_name}", "farm-ai-tool"],
                    metadata={
                        "tool_name": tool_name,
                        "function": func.__name__,
                        "args": str(kwargs) if kwargs else "no_args"
                    },
                    run_name=f"{tool_name}_{func.__name__}"
                )
                
                logger.debug(f"Tracing {tool_name}.{func.__name__} with config: {config}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def init_langsmith_environment():
    """Initialize LangSmith environment variables."""
    if settings.langchain_tracing_v2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        
        if settings.langchain_api_key:
            os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        
        if settings.langchain_project:
            os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
            
        if settings.langchain_endpoint:
            os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
        
        logger.info(f"LangSmith initialized: project={settings.langchain_project}")
        return True
    
    logger.info("LangSmith tracing disabled")
    return False


# Session tracking for LangSmith
class LangSmithSessionTracker:
    """Track user sessions for LangSmith tracing."""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def start_session(self, user_id: str, session_data: Optional[Dict[str, Any]] = None):
        """Start a new user session."""
        if not settings.langchain_tracing_v2:
            return
        
        self.active_sessions[user_id] = {
            "start_time": self._get_timestamp(),
            "message_count": 0,
            "session_data": session_data or {}
        }
        logger.debug(f"Started LangSmith session for user {user_id}")
    
    def update_session(self, user_id: str, message_count_increment: int = 1):
        """Update session metrics."""
        if not settings.langchain_tracing_v2 or user_id not in self.active_sessions:
            return
        
        self.active_sessions[user_id]["message_count"] += message_count_increment
        self.active_sessions[user_id]["last_activity"] = self._get_timestamp()
    
    def get_session_metadata(self, user_id: str) -> Dict[str, Any]:
        """Get session metadata for tracing."""
        if user_id not in self.active_sessions:
            return {"session_status": "new"}
        
        session = self.active_sessions[user_id]
        return {
            "session_status": "active",
            "session_start": session["start_time"],
            "message_count": session["message_count"],
            "last_activity": session.get("last_activity", session["start_time"])
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# Global session tracker instance
session_tracker = LangSmithSessionTracker()