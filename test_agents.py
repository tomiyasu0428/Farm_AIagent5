#!/usr/bin/env python3
"""Test individual agents without LangGraph."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_individual_agents():
    """Test individual agents without the graph framework."""
    print("🤖 個別エージェントテスト開始...")
    
    try:
        # Initialize database
        from src.database import init_database
        await init_database()
        print("✅ データベース接続成功")
        
        # Test SupervisorAgent
        from src.agents.supervisor import SupervisorAgent
        from src.models.state import AgriAgentState
        from langchain_core.messages import HumanMessage
        
        supervisor = SupervisorAgent()
        print("✅ SupervisorAgent初期化成功")
        
        # Create test state
        test_state: AgriAgentState = {
            "messages": [HumanMessage(content="こんにちは")],
            "user_id": "test_user_123",
            "thread_id": "test_thread_123",
            "next_agent": "",
            "pending_confirmation": {},
            "awaiting_confirmation": False,
            "extracted_data": {},
            "query_results": [],
            "error_message": None,
            "retry_count": 0,
            "agent_data": {},
            "timestamp": "2025-01-28T00:00:00Z",
            "session_metadata": {}
        }
        
        print("\n--- SupervisorAgent テスト ---")
        result = await supervisor.process(test_state)
        print(f"結果: {result}")
        
        # Test ReadAgent if routed there
        if result.get("next_agent") == "ReadAgent":
            print("\n--- ReadAgent テスト ---")
            from src.agents.read_agent import ReadAgent
            
            read_agent = ReadAgent()
            read_result = await read_agent.process(test_state)
            print(f"ReadAgent結果: {read_result}")
        
        print("\n🎉 個別エージェントテスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_individual_agents())