"""LangGraph configuration and main processing graph."""

import logging
from datetime import datetime
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from src.models.state import AgriAgentState
from src.models.mongodb_saver import MongoDBSaver
from src.agents.supervisor import SupervisorAgent
from src.agents.read_agent import ReadAgent
from src.utils.langsmith_config import session_tracker

logger = logging.getLogger(__name__)

# Initialize agents
supervisor_agent = SupervisorAgent()
read_agent = ReadAgent()

# Initialize checkpoint saver
checkpoint_saver = MongoDBSaver()


def create_graph():
    """Create and configure the LangGraph workflow."""
    
    # Create the state graph
    graph = StateGraph(AgriAgentState)
    
    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("read_agent", read_agent_node)
    
    # Add conditional edges
    graph.add_conditional_edges(
        "supervisor",
        lambda state: "read_agent" if state.get("next_agent") == "ReadAgent" else END,
        {
            "read_agent": "read_agent",
            END: END
        }
    )
    
    # ReadAgent always goes to END
    graph.add_edge("read_agent", END)
    
    # Set entry point
    graph.set_entry_point("supervisor")
    
    # Compile the graph
    return graph.compile()


async def supervisor_node(state: AgriAgentState) -> Dict[str, Any]:
    """Supervisor node processing."""
    try:
        logger.info("Processing message in supervisor node")
        result = await supervisor_agent.process(state)
        
        # Update state with supervisor results
        updated_state = {**state}
        for key, value in result.items():
            if key == "messages":
                updated_state["messages"] = state.get("messages", []) + value
            else:
                updated_state[key] = value
        
        return updated_state
        
    except Exception as e:
        logger.error(f"Error in supervisor node: {e}")
        return {
            **state,
            "error_message": str(e),
            "messages": state.get("messages", []) + [
                HumanMessage(content="システムエラーが発生しました。")
            ]
        }


async def read_agent_node(state: AgriAgentState) -> Dict[str, Any]:
    """Read agent node processing."""
    try:
        logger.info("Processing message in read agent node")
        result = await read_agent.process(state)
        
        # Update state with read agent results
        updated_state = {**state}
        for key, value in result.items():
            if key == "messages":
                updated_state["messages"] = state.get("messages", []) + value
            else:
                updated_state[key] = value
        
        return updated_state
        
    except Exception as e:
        logger.error(f"Error in read agent node: {e}")
        return {
            **state,
            "error_message": str(e),
            "messages": state.get("messages", []) + [
                HumanMessage(content="データ取得中にエラーが発生しました。")
            ]
        }


# Remove end_node as we use END from StateGraph


# Create the graph instance
app_graph = create_graph()


async def process_user_message(user_id: str, message: str) -> str:
    """Process user message through the LangGraph workflow."""
    try:
        # Initialize checkpoint saver
        await checkpoint_saver.initialize()
        
        # Create initial state
        initial_state: AgriAgentState = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "thread_id": user_id,  # Use user_id as thread_id for now
            "next_agent": "",
            "pending_confirmation": {},
            "awaiting_confirmation": False,
            "extracted_data": {},
            "query_results": [],
            "error_message": None,
            "retry_count": 0,
            "agent_data": {},
            "timestamp": datetime.utcnow().isoformat(),
            "session_metadata": {}
        }
        
        # Configuration for checkpointing and LangSmith tracing
        session_metadata = session_tracker.get_session_metadata(user_id)
        config = {
            "configurable": {
                "thread_id": user_id
            },
            "tags": ["farm-ai-agent", "langgraph-workflow", f"user:{user_id}"],
            "metadata": {
                "user_id": user_id,
                "message": message[:100],  # First 100 chars for privacy
                "workflow": "agri-agent-graph",
                **session_metadata
            }
        }
        
        # Run the graph
        logger.info(f"Processing message from user {user_id}: {message}")
        
        # Run the graph with config
        final_state = await app_graph.ainvoke(initial_state, config)
        
        # Extract response from final state
        if final_state.get("messages"):
            response = final_state["messages"][-1].content
        else:
            response = "申し訳ございません。回答の生成に失敗しました。"
        
        logger.info(f"Generated response for user {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing user message: {e}")
        return "申し訳ございません。システムエラーが発生しました。しばらく後にもう一度お試しください。"