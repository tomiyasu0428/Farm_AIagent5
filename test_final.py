#!/usr/bin/env python3
"""Final test of updated schema."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_final():
    """Final test with updated schema."""
    print("🔍 最終動作確認テスト...")
    
    try:
        from src.database import init_database, get_database
        from src.agents.supervisor import SupervisorAgent
        from src.agents.read_agent import ReadAgent
        from src.models.state import AgriAgentState
        from langchain_core.messages import HumanMessage
        
        await init_database()
        print("✅ データベース接続成功")
        
        database = get_database()
        collections = await database.list_collection_names()
        print(f"✅ コレクション数: {len(collections)}")
        
        # Quick agent test
        supervisor = SupervisorAgent()
        read_agent = ReadAgent()
        
        test_state: AgriAgentState = {
            "messages": [HumanMessage(content="今日のタスクを教えて")],
            "user_id": "test_user_001",
            "thread_id": "test_thread_001",
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
        
        # Test routing
        result = await supervisor.process(test_state)
        print(f"✅ Supervisor動作: {result.get('next_agent', 'direct_response')}")
        
        if result.get('next_agent') == 'ReadAgent':
            read_result = await read_agent.process(test_state)
            print(f"✅ ReadAgent動作: データ取得{len(read_result.get('query_results', []))}件")
        
        print("🎉 全テスト成功")
        
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    asyncio.run(test_final())