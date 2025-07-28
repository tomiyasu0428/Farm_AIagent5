#!/usr/bin/env python3
"""Complete test of the search issue and solution."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import settings
from src.database import init_database, get_database
from src.tools.field_tools import FieldRetrievalTool
from src.agents.read_agent import ReadAgent


async def complete_test():
    """Complete test showing the issue and solution."""
    print("🔬 完全テスト: 橋前の面積検索問題")
    print("=" * 60)
    
    try:
        await init_database()
        
        # 1. Database direct test
        print("1. 📊 データベース直接検索:")
        database = get_database()
        hashimae = await database.fields.find_one({"name": "橋前"})
        if hashimae:
            print(f"✅ 橋前圃場が存在: 面積 {hashimae.get('area_ha', 0)} ha")
        else:
            print("❌ 橋前圃場が見つかりません")
        
        # 2. Field tool test
        print("\n2. 🔧 フィールドツール検索:")
        field_tool = FieldRetrievalTool()
        result = await field_tool._arun(query_type="by_name", search_value="橋前", limit=5)
        if "橋前" in result and "7.9" in result:
            print("✅ フィールドツールで正常に検索可能")
            print("   面積: 7.9 ha が正しく取得できました")
        else:
            print("❌ フィールドツールで検索失敗")
        
        # 3. Agent keyword detection test  
        print("\n3. 🤖 エージェントキーワード検出テスト:")
        read_agent = ReadAgent()
        
        test_messages = [
            "橋前の面積を教えて",
            "橋前って何ヘクタール？", 
            "橋前の圃場の面積は？",
            "橋前畑の大きさ",
            "TOYOMIDORI-007の面積"
        ]
        
        for msg in test_messages:
            is_field = await read_agent._is_field_query(msg)
            print(f"   '{msg}' → {'✅ 圃場クエリ' if is_field else '❌ 圃場外クエリ'}")
        
        # 4. Show the root cause
        print("\n4. 🔍 問題の根本原因:")
        print("   ReadAgent._is_field_query() の判定キーワード:")
        field_keywords = ["圃場", "畑", "田", "ハウス", "field", "場所", "土地", "栽培", "作物"]
        print(f"   {field_keywords}")
        print("   '橋前の面積を教えて' にはこれらのキーワードが含まれていないため、")
        print("   field_toolが使用されず、従来のクエリ方式で検索されています。")
        
        # 5. Show areas and search capability
        print("\n5. 📋 全圃場の面積データ:")
        all_fields = []
        async for field in database.fields.find({}, {"name": 1, "area_ha": 1, "area": 1}).limit(10):
            all_fields.append(field)
        
        for field in all_fields:
            name = field.get('name', 'N/A')
            area_ha = field.get('area_ha', 0)
            area_sqm = field.get('area', 0)
            print(f"   • {name}: {area_ha} ha ({area_sqm} ㎡)")
        
        print("\n6. 💡 解決方法:")
        print("   A) ReadAgent._is_field_query() のキーワードリストに '面積' を追加")
        print("   B) またはフィールド名での直接検索も圃場クエリと判定するロジックを追加")
        print("   C) フィールドツールの検索精度を向上させる")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(complete_test())