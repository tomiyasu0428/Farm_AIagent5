#!/usr/bin/env python3
"""Test LangChain field retrieval tool with self-correction."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_field_tool():
    """Test the field retrieval tool directly."""
    print("🔧 LangChain圃場取得ツール単体テスト")
    print("=" * 50)
    
    try:
        from src.database import init_database
        from src.tools.field_tools import FieldRetrievalTool
        
        # Initialize database
        await init_database()
        print("✅ データベース接続成功")
        
        # Create tool instance
        field_tool = FieldRetrievalTool()
        print("✅ FieldRetrievalTool初期化成功")
        
        # Test different query scenarios
        test_scenarios = [
            {
                "name": "全圃場取得",
                "query_type": "all",
                "search_value": None,
                "limit": 5
            },
            {
                "name": "圃場名検索",
                "query_type": "by_name", 
                "search_value": "ハウス",
                "limit": 3
            },
            {
                "name": "作物検索",
                "query_type": "by_crop",
                "search_value": "トマト", 
                "limit": 3
            },
            {
                "name": "自己修正テスト（不正なクエリタイプ）",
                "query_type": "invalid_type",
                "search_value": None,
                "limit": 3
            },
            {
                "name": "自己修正テスト（範囲外limit）",
                "query_type": "all",
                "search_value": None,
                "limit": 999
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n--- テスト {i}: {scenario['name']} ---")
            print(f"パラメータ: query_type={scenario['query_type']}, search_value={scenario['search_value']}, limit={scenario['limit']}")
            
            try:
                # Execute tool
                result = await field_tool._arun(
                    query_type=scenario['query_type'],
                    search_value=scenario['search_value'],
                    limit=scenario['limit']
                )
                
                print("🎯 実行結果:")
                # Show first 200 characters of result
                print(f"   {result[:200]}...")
                if len(result) > 200:
                    print(f"   (全{len(result)}文字)")
                
                # Check if structured data is included
                if "構造化データ" in result:
                    print("   ✅ 構造化データ含有確認")
                
            except Exception as e:
                print(f"   ❌ エラー: {e}")
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        print(f"\n🎉 全{len(test_scenarios)}シナリオのテスト完了")
        
    except Exception as e:
        print(f"❌ テスト初期化エラー: {e}")
        import traceback
        traceback.print_exc()


async def test_with_read_agent():
    """Test field tool integrated with ReadAgent."""
    print("\n" + "=" * 50)
    print("🤖 ReadAgent統合テスト")
    print("=" * 50)
    
    try:
        from src.database import init_database
        from src.agents.read_agent import ReadAgent
        from src.models.state import AgriAgentState
        from langchain_core.messages import HumanMessage
        
        # Initialize database
        await init_database()
        
        # Create ReadAgent
        read_agent = ReadAgent()
        print("✅ ReadAgent with LangChain tools 初期化成功")
        
        # Test scenarios focusing on field queries
        field_test_scenarios = [
            {
                "name": "圃場状況問い合わせ",
                "message": "圃場の状況を教えてください"
            },
            {
                "name": "トマト栽培圃場検索",
                "message": "トマトを栽培している畑はありますか？"
            },
            {
                "name": "ハウス情報問い合わせ",
                "message": "ハウスの情報を知りたいです"
            },
            {
                "name": "非圃場クエリ（フォールバック確認）",
                "message": "農薬の情報を教えて"
            }
        ]
        
        for i, scenario in enumerate(field_test_scenarios, 1):
            print(f"\n--- ReadAgent テスト {i}: {scenario['name']} ---")
            print(f"入力: 「{scenario['message']}」")
            
            # Create test state
            test_state: AgriAgentState = {
                "messages": [HumanMessage(content=scenario['message'])],
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
            
            try:
                # Process with ReadAgent
                result = await read_agent.process(test_state)
                
                if result.get('messages'):
                    response = result['messages'][-1].content
                    print(f"🤖 応答: {response[:150]}...")
                    
                    # Check what method was used
                    extracted_data = result.get('extracted_data', {})
                    tools_used = extracted_data.get('tools_used', [])
                    if tools_used:
                        print(f"   🔧 使用ツール: {tools_used}")
                    else:
                        print(f"   📊 直接DB検索: {extracted_data.get('query_type', 'unknown')}")
                
            except Exception as e:
                print(f"   ❌ エラー: {e}")
            
            await asyncio.sleep(1)  # Rate limiting for LLM calls
        
        print(f"\n🎉 ReadAgent統合テスト完了")
        
    except Exception as e:
        print(f"❌ ReadAgent統合テストエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🌾 LangChain圃場ツール検証テスト開始...")
    
    # Run both tests
    asyncio.run(test_field_tool())
    asyncio.run(test_with_read_agent())