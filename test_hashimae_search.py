#!/usr/bin/env python3
"""Test the specific search issue with '橋前の面積を教えて'."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tools.field_tools import FieldRetrievalTool


async def test_hashimae_search():
    """Test different ways to search for 橋前 (Hashimae)."""
    print("🔍 橋前検索テスト")
    print("=" * 50)
    
    # Initialize the tool
    field_tool = FieldRetrievalTool()
    
    # Test scenarios
    test_cases = [
        {
            "name": "完全一致検索",
            "query_type": "by_name",
            "search_value": "橋前"
        },
        {
            "name": "部分一致検索（橋）",
            "query_type": "by_name", 
            "search_value": "橋"
        },
        {
            "name": "ひらがな検索",
            "query_type": "by_name",
            "search_value": "はしまえ"
        },
        {
            "name": "全圃場検索",
            "query_type": "all",
            "search_value": None
        },
        {
            "name": "圃場コード検索",
            "query_type": "by_code",
            "search_value": "TOYOMIDORI-007"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {test_case['name']} ---")
        print(f"パラメータ: query_type='{test_case['query_type']}', search_value='{test_case['search_value']}'")
        
        try:
            result = await field_tool._arun(
                query_type=test_case['query_type'],
                search_value=test_case['search_value'],
                limit=5
            )
            
            # Check if 橋前 is in the results
            if "橋前" in result:
                print("✅ 橋前が見つかりました！")
                # Extract area information
                lines = result.split('\n')
                for line in lines:
                    if "橋前" in line and "面積" in line:
                        print(f"📏 面積情報: {line.strip()}")
            else:
                print("❌ 橋前が見つかりませんでした")
            
            # Show first few lines of result
            result_lines = result.split('\n')
            print("結果の抜粋:")
            for line in result_lines[:5]:
                if line.strip():
                    print(f"  {line}")
            if len(result_lines) > 5:
                print(f"  ... (残り{len(result_lines)-5}行)")
                
        except Exception as e:
            print(f"❌ エラー: {e}")


if __name__ == "__main__":
    asyncio.run(test_hashimae_search())