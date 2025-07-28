#!/usr/bin/env python3
"""MongoDB database schema checker and explorer."""

import sys
import os
import asyncio
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import settings
from src.database import init_database, get_database
from motor.motor_asyncio import AsyncIOMotorClient


async def check_database_schema():
    """Check current MongoDB database schema and collections."""
    print("🔍 MongoDB データベーススキーマチェック")
    print(f"データベース: {settings.mongodb_database}")
    print("=" * 50)
    
    try:
        # Initialize database connection
        await init_database()
        database = get_database()
        
        # Get all collections
        collections = await database.list_collection_names()
        print(f"\n📋 既存コレクション数: {len(collections)}")
        
        if not collections:
            print("⚠️  データベースにコレクションがありません")
            print("\n📝 期待されるコレクション構造:")
            expected_collections = [
                "farmers - 農家マスター (主キー: line_user_id)",
                "groups - グループチャット管理",
                "fields - 圃場マスター", 
                "tasks - タスク管理",
                "work_logs - 作業履歴 (自然言語→構造化データのコア)",
                "farm_data - 時系列データ (センサー・気象・手動入力)",
                "agent_states - LangGraph状態永続化",
                "materials - 資材マスター (オプション)",
                "crops - 作物マスター (オプション)"
            ]
            for col in expected_collections:
                print(f"  • {col}")
        else:
            print("\n📂 コレクション詳細:")
            for collection_name in sorted(collections):
                await check_collection_details(database, collection_name)
        
        # Check indexes
        print("\n🗂️ インデックス情報:")
        for collection_name in sorted(collections):
            await check_collection_indexes(database, collection_name)
            
    except Exception as e:
        print(f"❌ データベースアクセスエラー: {e}")
        print("\n💡 確認事項:")
        print("  1. .env ファイルのMONGODB_URIが正しく設定されているか")
        print("  2. MongoDB Atlasクラスターが稼働しているか")
        print("  3. ネットワーク接続が正常か")


async def check_collection_details(database, collection_name):
    """Check details of a specific collection."""
    try:
        collection = database[collection_name]
        
        # Get document count
        count = await collection.count_documents({})
        
        # Get sample document
        sample_doc = await collection.find_one({})
        
        print(f"\n  📄 {collection_name}:")
        print(f"    ドキュメント数: {count}")
        
        if sample_doc:
            print(f"    サンプルフィールド: {list(sample_doc.keys())}")
            # Show first few fields with types
            field_info = []
            for key, value in list(sample_doc.items())[:5]:
                if key != '_id':
                    field_info.append(f"{key}({type(value).__name__})")
            if field_info:
                print(f"    フィールド詳細: {', '.join(field_info)}")
        else:
            print("    📝 空のコレクション")
            
    except Exception as e:
        print(f"    ❌ コレクション詳細取得エラー: {e}")


async def check_collection_indexes(database, collection_name):
    """Check indexes for a specific collection."""
    try:
        collection = database[collection_name]
        indexes = await collection.index_information()
        
        if len(indexes) > 1:  # _id_ index always exists
            print(f"\n  🗂️ {collection_name} インデックス:")
            for index_name, index_info in indexes.items():
                if index_name != '_id_':  # Skip default _id index
                    keys = index_info.get('key', [])
                    unique = index_info.get('unique', False)
                    unique_str = " (unique)" if unique else ""
                    print(f"    • {index_name}: {keys}{unique_str}")
                    
    except Exception as e:
        print(f"    ❌ インデックス情報取得エラー: {e}")


async def create_sample_data():
    """Create sample data for testing (optional)."""
    print("\n🎯 サンプルデータ作成")
    response = input("サンプルデータを作成しますか？ (y/N): ")
    
    if response.lower() != 'y':
        return
    
    try:
        database = get_database()
        
        # Create sample farmer
        sample_farmer = {
            "line_user_id": "sample_user_123",
            "name": "田中太郎", 
            "role": "owner",
            "is_active": True,
            "profile": {
                "farm_type": "vegetable",
                "experience_level": "intermediate",
                "custom_fields": {},
                "terminology": {}
            },
            "created_at": datetime.utcnow()
        }
        
        await database.farmers.insert_one(sample_farmer)
        print("✅ サンプル農家データを作成しました")
        
        # Create sample field
        field_result = await database.fields.insert_one({
            "field_code": "F01",
            "name": "第1圃場",
            "farmer_line_id": "sample_user_123", 
            "area": 1.5,
            "location": {"lat": 35.6762, "lon": 139.6503},
            "soil_type": "砂壌土",
            "current_cultivation": {
                "crop_name": "トマト",
                "variety": "桃太郎",
                "planting_date": "2024-03-15",
                "growth_stage": "開花期"
            },
            "created_at": datetime.utcnow()
        })
        field_id = field_result.inserted_id
        print("✅ サンプル圃場データを作成しました")
        
        # Create sample work log (core collection)
        sample_work_log = {
            "log_id": "LOG-20250728-SAMPLE",
            "user_id": "sample_user_123",
            "work_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "original_message": "トマトハウスで防除作業をしました",
            "extracted_data": {
                "field_id": field_id,
                "field_name": "第1圃場",
                "crop_name": "トマト",
                "work_details": {
                    "work_duration": 120
                },
                "quality_info": {
                    "crop_condition": "健全",
                    "weather_condition": "曇り"
                }
            },
            "category": "防除",
            "tags": ["防除", "トマト", "予防"],
            "confidence": 0.85,
            "status": "confirmed",
            "source": "line_bot",
            "version": 1.0
        }
        
        await database.work_logs.insert_one(sample_work_log)
        print("✅ サンプル作業ログデータを作成しました")
        
        # Create sample task
        sample_task = {
            "field_id": field_id,
            "title": "トマト追肥作業",
            "description": "第1圃場のトマトに追肥を行う",
            "status": "pending",
            "scheduled_date": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        
        await database.tasks.insert_one(sample_task)
        print("✅ サンプルタスクデータを作成しました")
        
        print("🎉 サンプルデータの作成が完了しました")
        
    except Exception as e:
        print(f"❌ サンプルデータ作成エラー: {e}")


if __name__ == "__main__":
    asyncio.run(check_database_schema())
    
    # Optionally create sample data
    create_sample = input("\nサンプルデータ作成機能を実行しますか？ (y/N): ")
    if create_sample.lower() == 'y':
        asyncio.run(create_sample_data())