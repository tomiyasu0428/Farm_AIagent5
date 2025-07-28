#!/usr/bin/env python3
"""Examine actual field data in MongoDB to understand structure and search issues."""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import settings
from src.database import init_database, get_database
from motor.motor_asyncio import AsyncIOMotorClient


async def examine_fields_collection():
    """Examine the actual field documents in MongoDB."""
    print("🔍 圃場データベース調査")
    print(f"データベース: {settings.mongodb_database}")
    print("=" * 60)
    
    try:
        # Initialize database connection
        await init_database()
        database = get_database()
        
        # Check if fields collection exists
        collections = await database.list_collection_names()
        if 'fields' not in collections:
            print("❌ 'fields' コレクションが存在しません")
            print(f"既存のコレクション: {collections}")
            return
        
        # Get collection info
        fields_collection = database.fields
        total_count = await fields_collection.count_documents({})
        print(f"📊 総圃場数: {total_count}")
        
        if total_count == 0:
            print("⚠️ 圃場データがありません")
            return
        
        print("\n" + "="*60)
        print("📄 サンプル圃場データ (最大10件)")
        print("="*60)
        
        # Get sample documents
        sample_docs = []
        async for doc in fields_collection.find({}).limit(10):
            sample_docs.append(doc)
        
        for i, doc in enumerate(sample_docs, 1):
            print(f"\n--- 圃場 {i} ---")
            print(f"ID: {doc.get('_id')}")
            print(f"名前: {doc.get('name', 'N/A')}")
            print(f"圃場コード: {doc.get('field_code', 'N/A')}")
            print(f"面積: {doc.get('area', 'N/A')}")
            print(f"土壌タイプ: {doc.get('soil_type', 'N/A')}")
            
            # Current cultivation info
            current_cultivation = doc.get('current_cultivation')
            if current_cultivation:
                print(f"現在栽培:")
                print(f"  作物名: {current_cultivation.get('crop_name', 'N/A')}")
                print(f"  品種: {current_cultivation.get('variety', 'N/A')}")
                print(f"  栽植日: {current_cultivation.get('planting_date', 'N/A')}")
                print(f"  成長段階: {current_cultivation.get('growth_stage', 'N/A')}")
            else:
                print("現在栽培: なし")
            
            # Location info
            location = doc.get('location')
            if location:
                print(f"位置: 緯度 {location.get('lat', 'N/A')}, 経度 {location.get('lon', 'N/A')}")
            
            # Show all fields in the document
            print(f"全フィールド: {list(doc.keys())}")
        
        print("\n" + "="*60)
        print("🔍 「橋前」検索テスト")
        print("="*60)
        
        # Test different search patterns for "橋前"
        search_tests = [
            {"name": {"$regex": "橋前", "$options": "i"}},
            {"name": {"$regex": "はしまえ", "$options": "i"}},
            {"name": {"$regex": "ハシマエ", "$options": "i"}},
            {"field_code": {"$regex": "橋前", "$options": "i"}},
            {"$text": {"$search": "橋前"}},  # If text index exists
        ]
        
        for i, query in enumerate(search_tests, 1):
            try:
                print(f"\n--- 検索テスト {i}: {query} ---")
                results = []
                async for doc in fields_collection.find(query).limit(5):
                    results.append(doc)
                
                if results:
                    print(f"✅ 結果: {len(results)}件")
                    for result in results:
                        print(f"  - {result.get('name', 'N/A')} ({result.get('field_code', 'N/A')}) - 面積: {result.get('area', 'N/A')}")
                else:
                    print("❌ 結果: 0件")
                    
            except Exception as e:
                print(f"❌ エラー: {e}")
        
        print("\n" + "="*60)
        print("📋 フィールド名一覧")
        print("="*60)
        
        # Get all field names for reference
        all_fields = []
        async for doc in fields_collection.find({}, {"name": 1, "field_code": 1, "area": 1}):
            all_fields.append({
                "name": doc.get('name', 'N/A'),
                "field_code": doc.get('field_code', 'N/A'),
                "area": doc.get('area', 'N/A')
            })
        
        print(f"全圃場名リスト ({len(all_fields)}件):")
        for field in sorted(all_fields, key=lambda x: x['name']):
            print(f"  • {field['name']} ({field['field_code']}) - {field['area']}ha")
        
        print("\n" + "="*60)
        print("🗂️ インデックス情報")
        print("="*60)
        
        # Check indexes
        indexes = await fields_collection.index_information()
        print("既存インデックス:")
        for index_name, index_info in indexes.items():
            keys = index_info.get('key', [])
            unique = index_info.get('unique', False)
            unique_str = " (unique)" if unique else ""
            print(f"  • {index_name}: {keys}{unique_str}")
        
    except Exception as e:
        print(f"❌ データベースアクセスエラー: {e}")
        print("\n💡 確認事項:")
        print("  1. .env ファイルのMONGODB_URIが正しく設定されているか")
        print("  2. MongoDB Atlasクラスターが稼働しているか")
        print("  3. ネットワーク接続が正常か")


if __name__ == "__main__":
    asyncio.run(examine_fields_collection())