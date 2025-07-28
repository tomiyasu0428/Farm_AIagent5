#!/usr/bin/env python3
"""Debug the field search issue step by step."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import settings
from src.database import init_database, get_database


async def debug_field_search():
    """Debug the field search issue step by step."""
    print("🐛 フィールド検索デバッグ")
    print("=" * 50)
    
    try:
        # Initialize database
        print("1. データベース接続中...")
        await init_database()
        database = get_database()
        print(f"✅ データベース接続成功: {database}")
        
        # Test basic query
        print("\n2. 基本クエリテスト...")
        fields_collection = database.fields
        
        # Count documents
        total_count = await fields_collection.count_documents({})
        print(f"📊 総圃場数: {total_count}")
        
        # Test simple query
        print("\n3. 橋前検索テスト...")
        query = {"name": {"$regex": "橋前", "$options": "i"}}
        print(f"クエリ: {query}")
        
        results = []
        async for doc in fields_collection.find(query):
            results.append(doc)
        
        print(f"結果数: {len(results)}")
        
        if results:
            for result in results:
                print(f"✅ 見つかった圃場:")
                print(f"  名前: {result.get('name')}")
                print(f"  コード: {result.get('field_code')}")
                print(f"  面積: {result.get('area')}")
                print(f"  面積単位: {result.get('area_unit', 'N/A')}")
                print(f"  面積(ha): {result.get('area_ha', 'N/A')}")
        else:
            print("❌ 橋前が見つかりませんでした")
        
        # Test broader search
        print("\n4. 広範囲検索テスト...")
        broader_query = {"name": {"$regex": "橋", "$options": "i"}}
        print(f"クエリ: {broader_query}")
        
        broader_results = []
        async for doc in fields_collection.find(broader_query):
            broader_results.append(doc)
        
        print(f"結果数: {len(broader_results)}")
        for result in broader_results:
            print(f"  - {result.get('name')} ({result.get('field_code')}) - 面積: {result.get('area')}")
            
        # Test the issue with field tool directly
        print("\n5. フィールドツール直接テスト...")
        from src.tools.field_tools import FieldRetrievalTool
        
        tool = FieldRetrievalTool()
        
        # Debug the corrected parameters first
        corrected_params = await tool._validate_and_correct_input("by_name", "橋前", 10)
        print(f"修正されたパラメータ: {corrected_params}")
        
        # Try the actual execution
        try:
            execution_result = await tool._execute_with_correction(**corrected_params)
            print(f"実行結果: {len(execution_result)}件")
            
            if execution_result:
                for result in execution_result:
                    print(f"  - {result.get('name')} ({result.get('field_code')}) - 面積: {result.get('area')}")
            else:
                print("❌ 実行結果が空です")
                
        except Exception as e:
            print(f"❌ 実行エラー: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ デバッグエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_field_search())