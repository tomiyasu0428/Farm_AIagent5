#!/usr/bin/env python3
"""Detailed agent testing with various scenarios."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_detailed_scenarios():
    """Test agents with various farming scenarios."""
    print("🌾 詳細農業シナリオテスト開始...")
    
    try:
        # Initialize database
        from src.database import init_database
        await init_database()
        
        from src.agents.supervisor import SupervisorAgent
        from src.agents.read_agent import ReadAgent
        from src.models.state import AgriAgentState
        from langchain_core.messages import HumanMessage
        
        supervisor = SupervisorAgent()
        read_agent = ReadAgent()
        
        test_scenarios = [
            {
                "name": "挨拶テスト",
                "message": "こんにちは",
                "expected_agent": "Supervisor"
            },
            {
                "name": "圃場情報問い合わせ",
                "message": "圃場の状況を教えて",
                "expected_agent": "ReadAgent"
            },
            {
                "name": "作業履歴問い合わせ",
                "message": "最近の作業記録はありますか？",
                "expected_agent": "ReadAgent"
            },
            {
                "name": "タスク確認",
                "message": "今日やるべき作業は何ですか？",
                "expected_agent": "ReadAgent"
            },
            {
                "name": "農薬情報問い合わせ",
                "message": "使える農薬の情報を教えて",
                "expected_agent": "ReadAgent"
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n--- テスト {i}: {scenario['name']} ---")
            print(f"入力: 「{scenario['message']}」")
            
            # Create test state
            test_state: AgriAgentState = {
                "messages": [HumanMessage(content=scenario['message'])],
                "user_id": "test_user_001",  # Updated to match new user schema
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
            
            # Test supervisor routing
            supervisor_result = await supervisor.process(test_state)
            
            if "next_agent" in supervisor_result:
                print(f"📍 ルーティング: {supervisor_result['next_agent']}")
                
                if supervisor_result['next_agent'] == "ReadAgent":
                    # Test ReadAgent
                    read_result = await read_agent.process(test_state)
                    if read_result.get('messages'):
                        response = read_result['messages'][-1].content
                        print(f"🤖 ReadAgent応答: {response[:100]}...")
                        print(f"📊 データ取得件数: {len(read_result.get('query_results', []))}")
                    
            elif "messages" in supervisor_result:
                # Direct supervisor response
                response = supervisor_result['messages'][-1].content
                print(f"🤖 Supervisor応答: {response[:100]}...")
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        print(f"\n🎉 全{len(test_scenarios)}シナリオのテスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_detailed_scenarios())