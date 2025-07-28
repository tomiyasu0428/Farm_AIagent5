#!/usr/bin/env python3
"""Get detailed information about the 橋前 field."""

import sys
import os
import asyncio
import json

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import settings
from src.database import init_database, get_database
from src.tools.field_tools import FieldRetrievalTool


async def get_hashimae_details():
    """Get detailed information about the 橋前 field."""
    print("📋 橋前圃場詳細情報")
    print("=" * 50)
    
    try:
        # Initialize database
        await init_database()
        database = get_database()
        
        # Find 橋前 field
        fields_collection = database.fields
        hashimae_field = await fields_collection.find_one({"name": "橋前"})
        
        if not hashimae_field:
            print("❌ 橋前圃場が見つかりませんでした")
            return
        
        print("✅ 橋前圃場の詳細情報:")
        print(json.dumps(hashimae_field, ensure_ascii=False, indent=2, default=str))
        
        # Calculate area in different units
        area_sqm = hashimae_field.get('area', 0)
        area_ha = hashimae_field.get('area_ha', 0)
        area_unit = hashimae_field.get('area_unit', '不明')
        
        print("\n📏 面積情報:")
        print(f"  基本面積: {area_sqm} ({area_unit})")
        print(f"  面積(ha): {area_ha} ha")
        
        if area_sqm and area_unit == '㎡':
            calculated_ha = area_sqm / 10000
            print(f"  計算値(ha): {calculated_ha} ha")
        
        # Test with the field tool
        print("\n🔧 フィールドツールテスト:")
        field_tool = FieldRetrievalTool()
        
        # Test different search types
        test_cases = [
            ("by_name", "橋前"),
            ("by_name", "橋"),
            ("by_code", "TOYOMIDORI-007"),
            ("all", None)
        ]
        
        for query_type, search_value in test_cases:
            print(f"\n--- {query_type} + {search_value} ---")
            try:
                result = await field_tool._arun(query_type=query_type, search_value=search_value, limit=5)
                
                # Check if result contains area information
                if "橋前" in result:
                    print("✅ 橋前が見つかりました")
                    # Extract area info from result
                    lines = result.split('\n')
                    for line in lines:
                        if "橋前" in line and ("面積" in line or "ha" in line):
                            print(f"📏 面積情報: {line.strip()}")
                else:
                    print("❌ 橋前が見つかりませんでした")
                    
                # Show structured data section
                if "構造化データ" in result:
                    structured_section = result.split("--- 構造化データ ---")[1]
                    try:
                        structured_data = json.loads(structured_section)
                        for field in structured_data.get('fields', []):
                            if field.get('name') == '橋前':
                                print(f"📊 構造化面積: {field.get('area')}")
                    except:
                        pass
                        
            except Exception as e:
                print(f"❌ エラー: {e}")
        
        # Test what users would actually see
        print("\n👤 ユーザー向け質問応答テスト:")
        user_queries = [
            ("橋前の面積を教えて", "by_name", "橋前"),
            ("橋前の面積は？", "by_name", "橋前"),
            ("TOYOMIDORI-007の面積", "by_code", "TOYOMIDORI-007"),
        ]
        
        for user_query, query_type, search_value in user_queries:
            print(f"\n🗣️ ユーザー質問: '{user_query}'")
            print(f"   検索パラメータ: {query_type}, {search_value}")
            
            try:
                result = await field_tool._arun(query_type=query_type, search_value=search_value, limit=10)
                
                # Extract the answer for the user
                if "橋前" in result:
                    print("✅ 回答可能")
                    lines = result.split('\n')
                    for line in lines:
                        if "橋前" in line and "面積" in line:
                            print(f"💬 回答例: 橋前圃場の面積は {area_ha} ha (79,000㎡) です。")
                            break
                else:
                    print("❌ 回答不可 - 圃場が見つかりません")
                    
            except Exception as e:
                print(f"❌ エラー: {e}")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(get_hashimae_details())