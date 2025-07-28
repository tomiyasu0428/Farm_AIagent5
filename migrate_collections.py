#!/usr/bin/env python3
"""Collection consolidation migration script."""

import sys
import os
import asyncio
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def migrate_collections():
    """Migrate and consolidate collections."""
    from src.database import init_database, get_database
    
    print("🔄 コレクション統合マイグレーション開始...")
    print("=" * 60)
    
    await init_database()
    database = get_database()
    
    # Step 1: Migrate users (farmers + workers → users)
    await migrate_users(database)
    
    # Step 2: Migrate tasks (auto_tasks + scheduled_tasks + tasks → tasks)  
    await migrate_tasks(database)
    
    # Step 3: Migrate work logs (work_logs + work_records → work_logs)
    await migrate_work_logs(database)
    
    # Step 4: Clean up empty and test collections
    await cleanup_collections(database)
    
    # Step 5: Verify final state
    await verify_migration(database)
    
    print("\n🎉 マイグレーション完了!")


async def migrate_users(database):
    """Migrate farmers and workers to unified users collection."""
    print("\n👥 ユーザー統合: farmers + workers → users")
    
    # Get existing data
    farmers = await database.farmers.find({}).to_list(100)
    workers = await database.workers.find({}).to_list(100)
    
    print(f"   farmers: {len(farmers)}件, workers: {len(workers)}件")
    
    if not farmers and not workers:
        print("   ⚠️ 移行データなし")
        return
    
    users_to_create = []
    
    # Convert farmers to users
    for farmer in farmers:
        user_doc = {
            "line_user_id": farmer.get("line_user_id", ""),
            "name": farmer.get("name", ""),
            "role": "farmer",  # farmers are always farmers
            "is_active": farmer.get("is_active", True),
            "profile": farmer.get("profile", {}),
            "skills": [],  # farmers don't have skills field
            "created_at": farmer.get("created_at", datetime.utcnow()),
            "updated_at": datetime.utcnow(),
            "source": "farmers_migration"
        }
        users_to_create.append(user_doc)
    
    # Convert workers to users  
    for worker in workers:
        user_doc = {
            "line_user_id": worker.get("line_user_id", ""),
            "name": worker.get("name", ""),
            "role": worker.get("role", "worker"),
            "is_active": worker.get("is_active", True),
            "profile": {},  # workers don't have profile field
            "skills": worker.get("skills", []),
            "created_at": worker.get("created_at", datetime.utcnow()),
            "updated_at": datetime.utcnow(),
            "source": "workers_migration"
        }
        users_to_create.append(user_doc)
    
    if users_to_create:
        result = await database.users.insert_many(users_to_create)
        print(f"   ✅ {len(result.inserted_ids)}件のユーザーを統合")


async def migrate_tasks(database):
    """Migrate auto_tasks, scheduled_tasks, tasks to unified tasks collection."""
    print("\n📋 タスク統合: auto_tasks + scheduled_tasks + tasks → tasks")
    
    # Get existing data
    auto_tasks = await database.auto_tasks.find({}).to_list(100)
    scheduled_tasks = await database.scheduled_tasks.find({}).to_list(100)
    existing_tasks = await database.tasks.find({}).to_list(100)
    
    print(f"   auto_tasks: {len(auto_tasks)}件, scheduled_tasks: {len(scheduled_tasks)}件, tasks: {len(existing_tasks)}件")
    
    tasks_to_create = []
    
    # Convert auto_tasks
    for auto_task in auto_tasks:
        task_doc = {
            "task_id": f"AUTO-{auto_task.get('_id')}",
            "field_id": auto_task.get("field_id"),
            "work_type": auto_task.get("work_type", ""),
            "description": f"自動生成タスク: {auto_task.get('work_type', '')}",
            "scheduled_date": auto_task.get("scheduled_date"),
            "priority": auto_task.get("priority", "medium"),
            "status": auto_task.get("status", "pending"),
            "assigned_worker": None,
            "estimated_duration": None,
            "materials_needed": auto_task.get("materials", []),
            "notes": auto_task.get("notes", ""),
            "auto_generated": True,
            "created_at": auto_task.get("created_at", datetime.utcnow()),
            "updated_at": datetime.utcnow(),
            "source": "auto_tasks_migration"
        }
        tasks_to_create.append(task_doc)
    
    # Convert scheduled_tasks (these are more complete)
    for sched_task in scheduled_tasks:
        task_doc = {
            "task_id": sched_task.get("task_id", f"SCHED-{sched_task.get('_id')}"),
            "field_id": sched_task.get("field_id"),
            "crop_id": sched_task.get("crop_id"),
            "work_type": sched_task.get("work_type", ""),
            "description": sched_task.get("description", ""),
            "scheduled_date": sched_task.get("scheduled_date"),
            "priority": sched_task.get("priority", "medium"),
            "status": sched_task.get("status", "pending"),
            "assigned_worker": sched_task.get("assigned_worker"),
            "estimated_duration": sched_task.get("estimated_duration"),
            "materials_needed": sched_task.get("materials_needed", []),
            "notes": sched_task.get("notes", ""),
            "auto_generated": False,
            "created_at": sched_task.get("created_at", datetime.utcnow()),
            "updated_at": datetime.utcnow(),
            "source": "scheduled_tasks_migration"
        }
        tasks_to_create.append(task_doc)
    
    # Clear existing tasks collection and insert all
    if tasks_to_create:
        await database.tasks.delete_many({})  # Clear existing
        result = await database.tasks.insert_many(tasks_to_create)
        print(f"   ✅ {len(result.inserted_ids)}件のタスクを統合")


async def migrate_work_logs(database):
    """Migrate work_records to work_logs if needed."""
    print("\n📝 作業ログ統合: work_records → work_logs")
    
    work_records = await database.work_records.find({}).to_list(100)
    print(f"   work_records: {len(work_records)}件")
    
    if not work_records:
        print("   ⚠️ 移行データなし")
        return
    
    # Convert work_records to work_logs format
    logs_to_create = []
    for record in work_records:
        log_doc = {
            "log_id": f"REC-{record.get('_id')}",
            "user_id": record.get("user_id", ""),
            "work_date": record.get("work_date", datetime.utcnow()),
            "created_at": record.get("created_at", datetime.utcnow()),
            "updated_at": datetime.utcnow(),
            "original_message": record.get("description", ""),
            "extracted_data": {
                "field_id": record.get("field_id"),
                "work_type": record.get("work_type", ""),
            },
            "category": record.get("category", "その他"),
            "tags": [],
            "confidence": 1.0,  # Manual records have high confidence
            "status": "confirmed",
            "source": "work_records_migration",
            "version": 1.0
        }
        logs_to_create.append(log_doc)
    
    if logs_to_create:
        result = await database.work_logs.insert_many(logs_to_create)
        print(f"   ✅ {len(result.inserted_ids)}件の作業記録を統合")


async def cleanup_collections(database):
    """Remove empty and test collections."""
    print("\n🗑️ 不要コレクション削除")
    
    collections_to_remove = [
        "test_collection",
        "farmers",      # Migrated to users
        "workers",      # Migrated to users  
        "auto_tasks",   # Migrated to tasks
        "scheduled_tasks",  # Migrated to tasks
        "work_records", # Migrated to work_logs
    ]
    
    for collection_name in collections_to_remove:
        try:
            await database[collection_name].drop()
            print(f"   ✅ {collection_name} を削除")
        except Exception as e:
            print(f"   ⚠️ {collection_name} 削除失敗: {e}")


async def verify_migration(database):
    """Verify the final state after migration."""
    print("\n🔍 マイグレーション結果確認")
    
    collections = await database.list_collection_names()
    print(f"   最終コレクション数: {len(collections)}")
    
    for col in sorted(collections):
        count = await database[col].count_documents({})
        print(f"   📄 {col}: {count}件")


if __name__ == "__main__":
    print("⚠️ 重要: このスクリプトはデータベースを変更します。")
    confirm = input("続行しますか？ (yes/no): ")
    
    if confirm.lower() == 'yes':
        asyncio.run(migrate_collections())
    else:
        print("マイグレーションをキャンセルしました。")