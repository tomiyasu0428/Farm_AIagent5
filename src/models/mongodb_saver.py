"""MongoDB-based checkpoint saver for LangGraph."""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
try:
    from langgraph.checkpoint import BaseCheckpointSaver
except ImportError:
    # For newer versions of langgraph
    try:
        from langgraph.checkpoint.base import BaseCheckpointSaver
    except ImportError:
        # Fallback - create a simple base class
        class BaseCheckpointSaver:
            async def aput(self, config, checkpoint, metadata):
                raise NotImplementedError
            
            async def aget(self, config):
                raise NotImplementedError
            
            async def alist(self, config, limit=None, before=None):
                raise NotImplementedError
from langchain_core.runnables import RunnableConfig

from src.database import get_database

logger = logging.getLogger(__name__)


class MongoDBSaver(BaseCheckpointSaver):
    """MongoDB implementation of LangGraph checkpoint saver."""
    
    def __init__(self):
        """Initialize MongoDB saver."""
        self.database = None
    
    async def initialize(self):
        """Initialize database connection."""
        self.database = get_database()
    
    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> RunnableConfig:
        """Save checkpoint to MongoDB."""
        if not self.database:
            await self.initialize()
        
        thread_id = config.get("configurable", {}).get("thread_id")
        
        if not thread_id:
            raise ValueError("thread_id is required in config")
        
        document = {
            "thread_id": thread_id,
            "checkpoint": checkpoint,
            "metadata": metadata,
            "updated_at": datetime.utcnow()
        }
        
        try:
            await self.database.agent_states.replace_one(
                {"thread_id": thread_id},
                document,
                upsert=True
            )
            logger.debug(f"Saved checkpoint for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise
        
        return config
    
    async def aget(self, config: RunnableConfig) -> Optional[Dict[str, Any]]:
        """Retrieve checkpoint from MongoDB."""
        if not self.database:
            await self.initialize()
        
        thread_id = config.get("configurable", {}).get("thread_id")
        
        if not thread_id:
            return None
        
        try:
            document = await self.database.agent_states.find_one(
                {"thread_id": thread_id}
            )
            
            if document:
                logger.debug(f"Retrieved checkpoint for thread {thread_id}")
                return {
                    "checkpoint": document.get("checkpoint"),
                    "metadata": document.get("metadata", {})
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve checkpoint: {e}")
            return None
    
    async def alist(
        self,
        config: RunnableConfig,
        limit: Optional[int] = None,
        before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List checkpoints (not implemented for this simple version)."""
        return []